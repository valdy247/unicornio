import * as THREE from "three";
import { TextGeometry } from "three/addons/geometries/TextGeometry.js";
import { FontLoader } from "three/addons/loaders/FontLoader.js";
import { advance, createPhysics, impact, boundsForObject, hasFootContact } from "./physics.mjs";

const get = (id) => document.getElementById(id);
const stage = get("composite");
const ctx = stage.getContext("2d");
const viewport = get("viewport");
const video = get("sourceVideo");
const ui = {
  videoFile: get("videoFile"), fileName: get("fileName"),
  text: get("textInput"), color: get("colorInput"), size: get("sizeInput"),
  strength: get("strengthInput"), layer: get("layerMode"),
  tracking: get("trackingInput"), skeleton: get("skeletonInput"),
  trackingStatus: get("trackingStatus"), collisionStatus: get("collisionStatus"),
  resolution: get("resolutionLabel"), fps: get("fpsLabel"),
  notice: get("viewportNotice"), playPause: get("playPause"),
  timeline: get("timeline"), timecode: get("timecode"),
  simulate: get("simulateBtn"), reset: get("resetBtn"),
  export: get("exportBtn")
};

const WORLD_W = 12;
let WORLD_H = WORLD_W * stage.height / stage.width;
let sourceUrl = null;
let textMesh = null;
let font = null;
let poseLandmarker = null;
let lastPose = null;
let lastPoseTime = 0;
let lastDetection = 0;
let lastVideoTime = -1;
let lastContactTime = -1e9;
let hasSegmentation = false;
let maskCanvas = document.createElement("canvas");
let maskCtx = maskCanvas.getContext("2d");
let subjectCanvas = document.createElement("canvas");
let subjectCtx = subjectCanvas.getContext("2d");
let lastCanvasFrame = performance.now();
let frameCounter = 0;
let dragging = false;
let exportInProgress = false;
let demoJumpTime = -1e9;
let autoPersonFront = false; // simple interaction timeline, NOT estimated physical depth

const state = { x: 0.50, y: 0.61, size: 0.88, text: "UNICORNIO", strength: 0.9 };
const physical = createPhysics();

const scene = new THREE.Scene();
const camera = new THREE.OrthographicCamera(-WORLD_W / 2, WORLD_W / 2, WORLD_H / 2, -WORLD_H / 2, 0.1, 100);
camera.position.set(0, 0, 18);
camera.lookAt(0, 0, 0);
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: false });
renderer.setPixelRatio(1);
renderer.setSize(stage.width, stage.height, false);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
scene.add(new THREE.HemisphereLight(0xffffff, 0x4c3377, 2.2));
const light = new THREE.DirectionalLight(0xffffff, 2.4);
light.position.set(-3, 5, 7);
scene.add(light);
const rim = new THREE.PointLight(0xc2a0ff, 80);
rim.position.set(2, 0, 5);
scene.add(rim);

function setStatus(element, value) {
  element.textContent = value;
}

function resetPhysics() {
  Object.assign(physical, createPhysics());
}

function setStageSize(width, height) {
  const scale = Math.min(1, 960 / width, 720 / height);
  stage.width = Math.max(160, Math.round(width * scale));
  stage.height = Math.max(120, Math.round(height * scale));
  viewport.style.aspectRatio = stage.width + " / " + stage.height;
  WORLD_H = WORLD_W * stage.height / stage.width;
  camera.top = WORLD_H / 2;
  camera.bottom = -WORLD_H / 2;
  camera.updateProjectionMatrix();
  renderer.setSize(stage.width, stage.height, false);
  subjectCanvas.width = stage.width;
  subjectCanvas.height = stage.height;
  setStatus(ui.resolution, stage.width + " × " + stage.height + (sourceUrl ? " · VIDEO" : " · DEMO"));
}

function worldX(normalized) { return (normalized - 0.5) * WORLD_W; }
function worldY(normalized) { return (0.5 - normalized) * WORLD_H; }

function makeText() {
  if (!font) return;
  if (textMesh) {
    scene.remove(textMesh);
    textMesh.geometry.dispose();
    for (const material of textMesh.material) material.dispose();
  }
  const geometry = new TextGeometry(state.text || "ORBIT", {
    font, size: 0.95, depth: 0.24,
    curveSegments: 6, bevelEnabled: true,
    bevelThickness: 0.035, bevelSize: 0.025, bevelSegments: 2
  });
  geometry.computeBoundingBox();
  geometry.center();
  geometry.computeBoundingBox();
  const span = geometry.boundingBox.max.x - geometry.boundingBox.min.x;
  // Keep long words inside the viewport.
  const fitScale = Math.min(1, 9.7 / Math.max(span, 0.1));
  const front = new THREE.MeshStandardMaterial({
    color: new THREE.Color(ui.color.value), metalness: 0.3, roughness: 0.33
  });
  const side = new THREE.MeshStandardMaterial({
    color: new THREE.Color(ui.color.value).multiplyScalar(0.45),
    metalness: 0.23, roughness: 0.53
  });
  textMesh = new THREE.Mesh(geometry, [front, side]);
  textMesh.userData.fitScale = fitScale;
  scene.add(textMesh);
  updateTextTransform();
}

function updateTextTransform() {
  if (!textMesh) return;
  textMesh.scale.setScalar(state.size * textMesh.userData.fitScale);
  textMesh.position.set(worldX(state.x), worldY(state.y) + physical.drop, 0);
  textMesh.rotation.set(-0.04, -0.12, physical.tilt);
}

function getTextBounds() {
  if (!textMesh) return boundsForObject(state.x, state.y, 0.5, 0.15);
  const box = textMesh.geometry.boundingBox;
  const scale = textMesh.scale.x;
  const width = (box.max.x - box.min.x) * scale / WORLD_W;
  const height = (box.max.y - box.min.y) * scale / WORLD_H;
  return boundsForObject(state.x, state.y - physical.drop / WORLD_H, width, height);
}

function drawDemo(timestamp) {
  const width = stage.width, height = stage.height;
  const bg = ctx.createLinearGradient(0, 0, width, height);
  bg.addColorStop(0, "#353753");
  bg.addColorStop(0.55, "#252737");
  bg.addColorStop(1, "#141825");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);
  const horizon = height * 0.70;
  ctx.fillStyle = "#292c3b";
  ctx.fillRect(0, horizon, width, height - horizon);
  ctx.strokeStyle = "#a3a0bc20";
  for (let x = 0; x < width; x += 48) {
    ctx.beginPath(); ctx.moveTo(x, horizon); ctx.lineTo((x - width / 2) * 1.45 + width / 2, height); ctx.stroke();
  }
  for (let i = 1; i < 6; i++) {
    const y = horizon + Math.pow(i / 6, 1.3) * (height - horizon);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
  }
  const elapsed = (timestamp - demoJumpTime) / 1000;
  const jump = elapsed >= 0 && elapsed < 1.05 ? Math.sin(Math.PI * elapsed / 1.05) * height * 0.23 : 0;
  const x = width * 0.49, y = height * 0.75 - jump;
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = "#151c31";
  ctx.lineWidth = Math.max(11, width * 0.025);
  ctx.beginPath(); ctx.moveTo(x - 8, y - 55); ctx.lineTo(x - 26, y - 4); ctx.moveTo(x + 8, y - 55); ctx.lineTo(x + 25, y - 4); ctx.stroke();
  ctx.strokeStyle = "#e2b59e";
  ctx.lineWidth = Math.max(9, width * 0.017);
  ctx.beginPath(); ctx.moveTo(x - 14, y - 104); ctx.lineTo(x - 45, y - 79); ctx.moveTo(x + 14, y - 104); ctx.lineTo(x + 44, y - 78); ctx.stroke();
  ctx.fillStyle = "#dce2f2";
  ctx.beginPath(); ctx.roundRect(x - 22, y - 130, 44, 76, 16); ctx.fill();
  ctx.fillStyle = "#e3b699";
  ctx.beginPath(); ctx.arc(x, y - 146, 18, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#201b28";
  ctx.beginPath(); ctx.arc(x, y - 155, 17, Math.PI, 2 * Math.PI); ctx.fill();
  ctx.restore();
  ctx.textAlign = "left"; ctx.font = "600 12px system-ui"; ctx.fillStyle = "#ffffff88";
  ctx.fillText("DEMO · AÑADE TU PROPIO VIDEO", 18, 24);
}

function updateMask(result) {
  const mask = result.segmentationMasks?.[0];
  if (!mask) {
    hasSegmentation = false;
    return;
  }
  try {
    const { width, height } = mask;
    if (maskCanvas.width !== width || maskCanvas.height !== height) {
      maskCanvas.width = width;
      maskCanvas.height = height;
    }
    const probabilities = mask.getAsFloat32Array();
    const img = maskCtx.createImageData(width, height);
    for (let i = 0; i < probabilities.length; i++) {
      const alpha = Math.max(0, Math.min(255, Math.round((probabilities[i] - 0.25) * 510)));
      const index = i * 4;
      img.data[index] = 255;
      img.data[index + 1] = 255;
      img.data[index + 2] = 255;
      img.data[index + 3] = alpha;
    }
    maskCtx.putImageData(img, 0, 0);
    hasSegmentation = true;
  } catch (error) {
    hasSegmentation = false;
    console.warn("Mask unavailable", error);
  }
}

function drawSubject() {
  if (!hasSegmentation || !sourceUrl) return;
  if (ui.layer.value === "back" || (ui.layer.value === "auto" && !autoPersonFront)) return;
  const w = stage.width, h = stage.height;
  subjectCtx.clearRect(0, 0, w, h);
  subjectCtx.globalCompositeOperation = "source-over";
  subjectCtx.drawImage(video, 0, 0, w, h);
  subjectCtx.globalCompositeOperation = "destination-in";
  subjectCtx.drawImage(maskCanvas, 0, 0, w, h);
  subjectCtx.globalCompositeOperation = "source-over";
  ctx.drawImage(subjectCanvas, 0, 0);
}

function drawSkeleton(landmarks) {
  if (!ui.skeleton.checked || !landmarks) return;
  ctx.save();
  ctx.lineWidth = Math.max(2, stage.width / 500);
  ctx.strokeStyle = "#d3ff86";
  const pairs = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23],
    [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28], [27, 31], [28, 32]];
  for (const [i, j] of pairs) {
    const a = landmarks[i], b = landmarks[j];
    if (!a || !b) continue;
    ctx.beginPath();
    ctx.moveTo(a.x * stage.width, a.y * stage.height);
    ctx.lineTo(b.x * stage.width, b.y * stage.height);
    ctx.stroke();
  }
  ctx.fillStyle = "#d3ff86";
  for (const i of [15, 16, 27, 28, 31, 32]) {
    const p = landmarks[i];
    if (p) { ctx.beginPath(); ctx.arc(p.x * stage.width, p.y * stage.height, 4, 0, Math.PI * 2); ctx.fill(); }
  }
  ctx.restore();
}

function processPose(timestamp) {
  if (!sourceUrl || !poseLandmarker || video.paused || video.readyState < 2) return;
  if (timestamp - lastDetection < 90 || video.currentTime === lastVideoTime) return;
  lastDetection = timestamp;
  lastVideoTime = video.currentTime;
  try {
    const result = poseLandmarker.detectForVideo(video, timestamp);
    updateMask(result);
    const current = result.landmarks?.[0] || null;
    if (current) {
      setStatus(ui.trackingStatus, hasSegmentation ? "Cuerpo y silueta detectados" : "Puntos del cuerpo detectados");
      if (ui.tracking.checked && lastPose && timestamp - lastContactTime > 450) {
        if (hasFootContact(current, lastPose, getTextBounds(), (timestamp - lastPoseTime) / 1000)) {
          impact(physical, state.strength);
          lastContactTime = timestamp;
          autoPersonFront = true;
          setStatus(ui.collisionStatus, "Contacto estimado · el texto queda detrás ⚡");
        }
      }
    } else {
      setStatus(ui.trackingStatus, "No vemos un cuerpo completo");
    }
    lastPose = current;
    lastPoseTime = timestamp;
    result.segmentationMasks?.forEach(mask => mask.close?.());
  } catch (error) {
    console.error("Pose inference failed", error);
    setStatus(ui.trackingStatus, "Error de seguimiento: usa simulación manual");
    poseLandmarker = null;
    hasSegmentation = false;
  }
}

async function initializePose() {
  try {
    setStatus(ui.trackingStatus, "Descargando modelo de pose…");
    const visionModule = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/+esm");
    const { FilesetResolver, PoseLandmarker } = visionModule;
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm"
    );
    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        delegate: "CPU"
      },
      runningMode: "VIDEO", numPoses: 1, outputSegmentationMasks: true,
      minPoseDetectionConfidence: 0.4, minPosePresenceConfidence: 0.4, minTrackingConfidence: 0.4
    });
    setStatus(ui.trackingStatus, "Modelo listo · carga un video");
  } catch (error) {
    console.warn("MediaPipe unavailable", error);
    setStatus(ui.trackingStatus, "Sin seguimiento automático · modo manual disponible");
    setStatus(ui.notice, "Modo manual disponible: Simular salto");
  }
}

function timeLabel(seconds) {
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  return String(Math.floor(value / 60)).padStart(2, "0") + ":" + String(value % 60).padStart(2, "0");
}

function updateTime() {
  if (!sourceUrl || !Number.isFinite(video.duration)) return;
  ui.timeline.value = String(Math.floor(video.currentTime / video.duration * 1000) || 0);
  ui.timecode.textContent = timeLabel(video.currentTime) + " / " + timeLabel(video.duration);
  ui.playPause.textContent = video.paused ? "▶" : "❚❚";
}

function tick(timestamp) {
  requestAnimationFrame(tick);
  const delta = Math.min(0.05, (timestamp - lastCanvasFrame) / 1000);
  lastCanvasFrame = timestamp;
  if (sourceUrl && video.readyState >= 2) {
    processPose(timestamp);
    ctx.drawImage(video, 0, 0, stage.width, stage.height);
  } else {
    drawDemo(timestamp);
  }
  advance(physical, delta);
  updateTextTransform();
  renderer.render(scene, camera);
  ctx.drawImage(renderer.domElement, 0, 0, stage.width, stage.height);
  drawSubject();
  drawSkeleton(lastPose);
  if (sourceUrl) updateTime();
  frameCounter += 1;
  if (frameCounter % 35 === 0) setStatus(ui.fps, "● VISTA EN VIVO");
}

function loadVideo(file) {
  if (!file || !file.type.startsWith("video/")) {
    alert("Selecciona un archivo de video compatible.");
    return;
  }
  if (sourceUrl) URL.revokeObjectURL(sourceUrl);
  sourceUrl = URL.createObjectURL(file);
  video.pause();
  video.src = sourceUrl;
  video.load();
  setStatus(ui.fileName, file.name);
  setStatus(ui.notice, "Arrastra el texto y prueba un salto");
  resetPhysics();
  lastPose = null;
  hasSegmentation = false;
  autoPersonFront = false;
  video.onloadedmetadata = async () => {
    setStageSize(video.videoWidth, video.videoHeight);
    video.currentTime = 0;
    try { await video.play(); } catch { setStatus(ui.notice, "Pulsa ▶ para reproducir el video"); }
  };
  video.onerror = () => {
    setStatus(ui.notice, "Tu navegador no pudo abrir este formato de video");
  };
}

async function exportPreview() {
  if (exportInProgress) return;
  if (!stage.captureStream || !window.MediaRecorder) {
    alert("Este navegador no permite exportar la vista previa. Prueba Chrome o Edge.");
    return;
  }
  const type = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"]
    .find(mime => MediaRecorder.isTypeSupported(mime));
  if (!type) {
    alert("No se encontró un formato WebM compatible.");
    return;
  }
  exportInProgress = true;
  ui.export.disabled = true;
  setStatus(ui.export, "Grabando 8 s…");
  const stream = stage.captureStream(24);
  const recorder = new MediaRecorder(stream, { mimeType: type });
  const chunks = [];
  let timeout;
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    clearTimeout(timeout);
    if (recorder.state !== "inactive") recorder.stop();
  };
  recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
  recorder.onstop = () => {
    stream.getTracks().forEach(track => track.stop());
    const blob = new Blob(chunks, { type: "video/webm" });
    if (blob.size) {
      const link = document.createElement("a");
      const linkUrl = URL.createObjectURL(blob);
      link.href = linkUrl;
      link.download = "unicornio-orbit-preview.webm";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(linkUrl), 1000);
    }
    exportInProgress = false;
    ui.export.disabled = false;
    setStatus(ui.export, "↓ Exportar prueba en WebM");
  };
  recorder.onerror = error => {
    console.error("Recording error", error);
    finish();
  };
  try {
    if (sourceUrl) {
      video.pause();
      video.currentTime = 0;
      lastVideoTime = -1;
      await video.play();
      video.addEventListener("ended", finish, { once: true });
    }
    recorder.start(250);
    timeout = setTimeout(finish, 8000);
    if (!sourceUrl) {
      demoJumpTime = performance.now();
      impact(physical, state.strength);
    }
  } catch (error) {
    console.error(error);
    exportInProgress = false;
    ui.export.disabled = false;
    setStatus(ui.export, "↓ Exportar prueba en WebM");
    stream.getTracks().forEach(track => track.stop());
    alert("No se pudo iniciar la grabación; revisa el formato del video.");
  }
}

function normalizedPointer(event) {
  const rect = stage.getBoundingClientRect();
  return { x: (event.clientX - rect.left) / rect.width, y: (event.clientY - rect.top) / rect.height };
}

stage.addEventListener("pointerdown", event => {
  const point = normalizedPointer(event);
  const bounds = getTextBounds();
  if (point.x >= bounds.left - 0.04 && point.x <= bounds.right + 0.04
    && point.y >= bounds.top - 0.07 && point.y <= bounds.bottom + 0.07) {
    dragging = true;
    stage.setPointerCapture(event.pointerId);
  }
});
stage.addEventListener("pointermove", event => {
  if (!dragging) return;
  const point = normalizedPointer(event);
  state.x = Math.max(0.1, Math.min(0.9, point.x));
  state.y = Math.max(0.1, Math.min(0.9, point.y));
});
stage.addEventListener("pointerup", () => { dragging = false; });
stage.addEventListener("pointercancel", () => { dragging = false; });
viewport.addEventListener("dragover", event => { event.preventDefault(); viewport.classList.add("drag-over"); });
viewport.addEventListener("dragleave", () => viewport.classList.remove("drag-over"));
viewport.addEventListener("drop", event => {
  event.preventDefault();
  viewport.classList.remove("drag-over");
  loadVideo(event.dataTransfer?.files?.[0]);
});
ui.videoFile.addEventListener("change", () => loadVideo(ui.videoFile.files?.[0]));
ui.text.addEventListener("input", () => { state.text = ui.text.value.toUpperCase(); makeText(); });
ui.color.addEventListener("input", makeText);
ui.size.addEventListener("input", () => { state.size = Number(ui.size.value) / 100; });
ui.strength.addEventListener("input", () => { state.strength = Number(ui.strength.value) / 100; });
ui.simulate.addEventListener("click", () => {
  demoJumpTime = performance.now();
  impact(physical, state.strength);
  autoPersonFront = true;
  setStatus(ui.collisionStatus, "Impacto simulado · texto detrás ⚡");
});
ui.reset.addEventListener("click", () => {
  resetPhysics();
  autoPersonFront = false;
  state.x = 0.5;
  state.y = 0.61;
  if (sourceUrl) { video.currentTime = 0; lastVideoTime = -1; }
  lastPose = null;
  hasSegmentation = false;
  setStatus(ui.collisionStatus, "En espera de contacto");
});
ui.playPause.addEventListener("click", () => {
  if (!sourceUrl) { demoJumpTime = performance.now(); impact(physical, state.strength); autoPersonFront = true; return; }
  if (video.paused) video.play().catch(console.warn);
  else video.pause();
});
ui.timeline.addEventListener("input", () => {
  if (sourceUrl && Number.isFinite(video.duration)) {
    video.currentTime = video.duration * Number(ui.timeline.value) / 1000;
    lastVideoTime = -1;
    lastPose = null;
    hasSegmentation = false;
    autoPersonFront = false;
  }
});
ui.export.addEventListener("click", exportPreview);

setStageSize(960, 540);
requestAnimationFrame(tick);
(async () => {
  try {
    font = await new FontLoader().loadAsync(
      "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/fonts/helvetiker_bold.typeface.json"
    );
    makeText();
    setStatus(ui.notice, "Prueba «Simular salto» o sube tu video");
  } catch (error) {
    console.error("3D font unavailable", error);
    setStatus(ui.notice, "No se pudo descargar la fuente 3D. Revisa tu conexión.");
  }
})();
initializePose();
