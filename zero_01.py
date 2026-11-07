"""ZERO-01: benchmark reproducible de desenfoque completo vs. incremental.

Usa solo CPU y datos sinteticos por defecto. No supone una invencion.
"""

import argparse
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np


def incremental_blur(previous_frame, previous_blur, current_frame, kernel=15, fallback_ratio=0.60):
    """Devuelve (imagen, fraccion_bbox, metodo).

    Detecta diferencias en toda la imagen (costo incluido en el benchmark).
    Solo recalcula la region que cambio, agregando un margen de kernel//2.
    """
    if previous_frame.shape != current_frame.shape:
        raise ValueError("Los fotogramas deben tener dimensiones iguales")
    if kernel < 3 or kernel % 2 == 0:
        raise ValueError("kernel debe ser impar y >= 3")

    difference = cv2.absdiff(previous_frame, current_frame)
    unchanged = cv2.inRange(difference, (0, 0, 0), (0, 0, 0))
    coordinates = cv2.findNonZero(cv2.bitwise_not(unchanged))
    if coordinates is None:
        return previous_blur.copy(), 0.0, "sin_cambios"
    x0, y0, roi_width, roi_height = cv2.boundingRect(coordinates)
    x1, y1 = x0 + roi_width, y0 + roi_height
    height, width = current_frame.shape[:2]
    fraction = ((y1 - y0) * (x1 - x0)) / (height * width)

    if fraction >= fallback_ratio:
        return cv2.GaussianBlur(current_frame, (kernel, kernel), 0), fraction, "completo"

    # Los pixeles de entrada cambiados afectan los pixeles vecinos de salida.
    # Primer halo: salida afectada. Segundo halo: contexto para calcular esa salida.
    margin = kernel // 2
    ox0, oy0 = max(x0 - margin, 0), max(y0 - margin, 0)
    ox1, oy1 = min(x1 + margin, width), min(y1 + margin, height)
    px0, py0 = max(ox0 - margin, 0), max(oy0 - margin, 0)
    px1, py1 = min(ox1 + margin, width), min(oy1 + margin, height)
    patch = cv2.GaussianBlur(current_frame[py0:py1, px0:px1], (kernel, kernel), 0)
    result = previous_blur.copy()
    result[oy0:oy1, ox0:ox1] = patch[oy0 - py0:oy1 - py0, ox0 - px0:ox1 - px0]
    return result, fraction, "regional"


def synthetic_frames(count, width, height):
    rng = np.random.default_rng(42)
    background = rng.integers(30, 220, size=(height, width, 3), dtype=np.uint8)
    for i in range(count):
        frame = background.copy()
        x = 10 + round(i * max(width - 150, 0) / max(count - 1, 1))
        y = max(0, min(height - 90, round(height * 0.35 + 12 * np.sin(i / 4))))
        cv2.rectangle(frame, (x, y), (min(x + 90, width - 1), min(y + 70, height - 1)), (30, 170, 250), -1)
        yield frame


def video_frames(path, count):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"No se pudo abrir el video: {path}")
    try:
        produced = 0
        while produced < count:
            ok, frame = capture.read()
            if not ok:
                break
            yield frame
            produced += 1
    finally:
        capture.release()


def run_benchmark(frames, kernel=15, output=Path("results")):
    cv2.setNumThreads(1)
    baseline_ms, incremental_ms, region_fractions = [], [], []
    methods = {"completo": 0, "regional": 0, "sin_cambios": 0}
    previous_frame, previous_result, last_frame, last_result = None, None, None, None
    max_error = 0
    for frame in frames:
        start = perf_counter()
        baseline = cv2.GaussianBlur(frame, (kernel, kernel), 0)
        baseline_ms.append((perf_counter() - start) * 1000)

        start = perf_counter()
        if previous_frame is None:
            updated, fraction, method = cv2.GaussianBlur(frame, (kernel, kernel), 0), 1.0, "completo"
        else:
            updated, fraction, method = incremental_blur(previous_frame, previous_result, frame, kernel)
        incremental_ms.append((perf_counter() - start) * 1000)
        error = int(np.max(cv2.absdiff(baseline, updated)))
        max_error = max(max_error, error)
        if error:
            raise AssertionError(f"Calidad desigual: error maximo de pixel = {error}")
        methods[method] += 1
        region_fractions.append(fraction)
        previous_frame, previous_result = frame, updated
        last_frame, last_result = frame, updated

    if not baseline_ms:
        raise ValueError("No hay fotogramas para evaluar")
    output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output / "ultimo_fotograma.png"), last_frame)
    cv2.imwrite(str(output / "ultimo_desenfoque.png"), last_result)
    total_full, total_inc = sum(baseline_ms), sum(incremental_ms)
    print("=== UNICORNIO LABS | ZERO-01 ===")
    print(f"Fotogramas: {len(baseline_ms)} | Kernel: {kernel}x{kernel}")
    print(f"Tiempo total completo: {total_full:.2f} ms")
    print(f"Tiempo total incremental: {total_inc:.2f} ms (incluye deteccion de cambios)")
    print(f"Factor de velocidad: {total_full / total_inc:.2f}x (menor que 1x = mas lento)")
    print(f"Area media del cambio (caja delimitadora): {np.mean(region_fractions[1:]) * 100 if len(region_fractions)>1 else 100:.2f}%")
    print(f"Metodos utilizados: {methods}")
    print(f"Error maximo de pixel frente al metodo completo: {max_error}")
    print(f"Imagenes guardadas en: {output.resolve()}")
    return {"frames": len(baseline_ms), "max_error": max_error, "speedup": total_full / total_inc}


def main():
    parser = argparse.ArgumentParser(description="ZERO-01: medicion de actualizacion regional vs. total")
    parser.add_argument("--video", type=Path, help="Archivo de video opcional. Si se omite, se usan escenas sinteticas")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--kernel", type=int, default=15)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.frames < 2 or args.width < 160 or args.height < 120 or args.kernel < 3 or args.kernel % 2 == 0:
        parser.error("frames >= 2, width >= 160, height >= 120, kernel impar >= 3")
    source = video_frames(args.video, args.frames) if args.video else synthetic_frames(args.frames, args.width, args.height)
    run_benchmark(source, kernel=args.kernel, output=args.output)


if __name__ == "__main__":
    main()
