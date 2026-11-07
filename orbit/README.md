# ORBIT-01 · Texto 3D que reacciona al movimiento

**Estado:** prototipo funcional de investigación (primera versión, sujeto a validación en equipos de usuarios). No es todavía ORBIT 3 ni reconstruye la escena física en 3D.

Una pequeña app web para experimentar con:

- **Video local:** selecciona un video de tu computadora; el archivo no se sube a nuestro servidor.
- **Texto 3D real:** geometría extruida de Three.js con iluminación; cambia texto, color y tamaño, y arrástralo en pantalla.
- **Seguimiento de persona:** MediaPipe Pose Landmarker (modelo ligero), detección de pies y máscara corporal para que la silueta se dibuje delante de las letras.
- **Reacción al impacto:** un modelo de resortes visuales hace que las letras bajen, giren y reboten al estimar contacto con un pie descendente. El modo «Salto automático (experimental)» muestra texto delante antes del contacto y persona delante después, simulando un cambio de profundidad.
- **Prueba manual:** botón «Simular salto / impacto» cuando no tienes un video o el seguimiento no se puede cargar.
- **Exportación experimental:** descarga los primeros ocho segundos del lienzo como **WebM sin audio**.

## Arranque rápido en Windows

Abre PowerShell dentro de la carpeta donde clonaste `valdy247/unicornio`:

```powershell
git pull
python -m http.server 8000
```

Abre **http://localhost:8000/orbit/** en Chrome o Edge.

Si el puerto 8000 está ocupado, usa `python -m http.server 8080` y abre `http://localhost:8080/orbit/`.

No uses `file:///...` porque los módulos y archivos WebAssembly necesitan servirse por HTTP. Para detener el servidor, pulsa **Ctrl+C**.

### Probar en 60 segundos

1. Abre la página y pulsa **«Simular salto / impacto»**. Verás que el texto cae y rebota en la escena de demostración.
2. Graba un video corto con **la cámara fija**, de cuerpo completo, en el que saltes cerca del lugar donde quieres colocar las letras.
3. Sube el archivo en **Seleccionar video**. Por ahora recomendamos MP4 H.264 para mayor compatibilidad con Chrome y Edge.
4. Arrastra las letras para situarlas cerca de tus pies. El modo **Salto automático (experimental)** cambia la capa visual después de un contacto. Si quieres mantener la silueta delante en todo momento, selecciona **Persona delante**.
5. Reproduce el video. Si el detector observa que un pie desciende cerca del borde superior del texto, activa una reacción. Si no la detecta, pulsa el botón de simulación para probar el efecto.
6. Usa **Exportar prueba en WebM** para descargar un clip de hasta ocho segundos, sin audio.

## Requisitos y privacidad

- PC con Intel UHD y 16 GB de RAM: puede ejecutar esta versión en navegador, pero la velocidad de detección depende del modelo de procesador.
- Chrome o Microsoft Edge modernos con WebGL y MediaRecorder.
- Internet la primera vez y mientras sea necesario para las dependencias de CDN: Three.js, MediaPipe y el modelo de pose, que se descargan de servicios públicos externos.
- El archivo de video permanece en el navegador; Orbit no implementa un backend de subida. Las bibliotecas externas pueden realizar sus propias solicitudes técnicas o telemetría según sus políticas.

## Limitaciones importantes

- **No recupera la geometría real ni la profundidad del mundo desde una sola cámara.** El texto 3D se coloca visualmente sobre el plano del video.
- **La oclusión es básica:** se usa una máscara de persona completa cuando seleccionas «Persona delante» o se activa el cambio de capa en «Salto automático». Esta transición es programada según el contacto estimado y **no prueba** que conocemos la profundidad real. Para que el texto pase auténticamente delante de unas partes y detrás de otras, se necesita estimación más fina de profundidad.
- **El contacto es una heurística 2D** basada en posiciones y velocidad de los pies detectados. No hay simulación de fuerza física, colisiones espaciales precisas ni garantía de detectar todos los saltos.
- El movimiento de cámara real **no** está resuelto: las letras se anclan a una posición de pantalla, no a un punto estable de una escena 3D.
- El formato de exportación es WebM sin audio; no es todavía un editor listo para publicar en redes sociales sin trabajo adicional.
- El render y la detección dependen de librerías conocidas. **Esto no es una invención tecnológica inédita.**

## Estructura

- `index.html` y `styles.css`: interfaz.
- `main.js`: video local, escena Three.js, detección MediaPipe, composición, exportación.
- `physics.mjs`: dinámica de muelles y estimación aproximada de contacto, sin dependencias externas.
- `tests/physics.test.mjs`: pruebas del módulo de física.

### Pruebas del módulo físico

Si tienes Node.js 20 o superior:

```powershell
node --test orbit/tests/physics.test.mjs
```

## Nuestra siguiente investigación

**ORBIT-02:** estimación de movimiento de cámara y anclaje del texto a un punto de la escena, primero con cámara lenta y escenario controlado.

**ORBIT-03:** profundidad relativa, oclusión coherente y contacto estimado de pies/manos. Analizar cómo separar la trayectoria humana de la ubicación del objeto.

**ORBIT-04:** interacciones físicas visuales (saltar, empujar, rodear), con corrección manual disponible y métricas de calidad y costo.

**Meta a largo plazo:** interacción automática y creíble entre personas grabadas y elementos virtuales, ejecutable a un costo accesible. Necesitamos medir calidad y latencia frente a soluciones existentes antes de reclamar originalidad.
