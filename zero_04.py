"""ZERO-04: known camera translation for cached bilateral filtering.

RESEARCH LIMITATION: the exact integer camera shift is SUPPLIED by the
synthetic test generator. This experiment does NOT estimate camera motion,
and therefore does not prove a usable real-video accelerator.
"""
import argparse
import json
import statistics
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np


def apply_filter(frame, diameter):
    return cv2.bilateralFilter(frame, diameter, 75, 75)


def reuse_with_known_shift(old, old_result, current, dx, dy, diameter=15,
                           tile=64, fallback_ratio=0.65):
    """Reuse translated output and recalculate only affected tiles exactly."""
    if old.shape != old_result.shape or old.shape != current.shape:
        raise ValueError("Frame shapes must match")
    height, width = current.shape[:2]
    if diameter < 3 or diameter % 2 != 1 or tile < 2 or not 0 < fallback_ratio <= 1:
        raise ValueError("Invalid diameter, tile or fallback_ratio")
    if abs(dx) >= width or abs(dy) >= height:
        raise ValueError("Translation exceeds frame dimensions")

    radius = diameter // 2
    shifted_input = np.roll(old, (dy, dx), axis=(0, 1))
    shifted_output = np.roll(old_result, (dy, dx), axis=(0, 1))

    dirty = np.any(shifted_input != current, axis=2).astype(np.uint8)
    if np.any(dirty):
        dirty = cv2.dilate(dirty, np.ones((diameter, diameter), np.uint8))

    # Reflective image borders do not commute with translation. Mark both
    # the destination frame's borders and the translated source borders.
    border = np.zeros((height, width), np.uint8)
    border[:radius, :] = 1
    border[-radius:, :] = 1
    border[:, :radius] = 1
    border[:, -radius:] = 1
    dirty |= border
    dirty |= np.roll(border, (dy, dx), axis=(0, 1))

    patches = []
    for y0 in range(0, height, tile):
        y1 = min(height, y0 + tile)
        for x0 in range(0, width, tile):
            x1 = min(width, x0 + tile)
            if np.any(dirty[y0:y1, x0:x1]):
                patches.append((x0, y0, x1, y1))

    number_of_tiles = ((height + tile - 1) // tile) * ((width + tile - 1) // tile)
    if len(patches) / number_of_tiles >= fallback_ratio:
        return apply_filter(current, diameter), "fallback"

    result = shifted_output.copy()
    for x0, y0, x1, y1 in patches:
        px0, px1 = max(0, x0 - radius), min(width, x1 + radius)
        py0, py1 = max(0, y0 - radius), min(height, y1 + radius)
        blurred_patch = apply_filter(current[py0:py1, px0:px1], diameter)
        result[y0:y1, x0:x1] = blurred_patch[
            y0 - py0:y1 - py0, x0 - px0:x1 - px0
        ]
    return result, "reuse"


def make_frames(scenario, count, width, height, dx=3, dy=0):
    """Synthetic frames with known camera motion (not estimated)."""
    if scenario not in ("camera", "camera_object", "global"):
        raise ValueError("Unknown scenario")
    rng = np.random.default_rng(710)
    background = rng.integers(30, 200, size=(height, width, 3), dtype=np.uint8)
    frames = []
    for index in range(count):
        if scenario == "global":
            frame = cv2.add(background, (index * 9) % 40)
            shift = (0, 0)
        else:
            frame = np.roll(background, (dy * index, dx * index), axis=(0, 1)).copy()
            shift = (dx, dy)
            if scenario == "camera_object":
                x = min(width - 30, 10 + index * 2)
                cv2.rectangle(frame, (x, height // 2), (x + 23, height // 2 + 23),
                              (10, 240, 100), -1)
        frames.append((frame, *shift))
    return frames


def benchmark(frames, diameter=15, tile=64, repeats=3):
    if repeats < 1 or len(frames) < 2:
        raise ValueError("At least 2 frames, 1 repetition")
    cv2.setNumThreads(1)
    apply_filter(frames[0][0], diameter)  # warmup
    timing = {"full": [], "oracle": []}
    max_pixel_error = 0
    strategy_counts = {}
    for repeat in range(repeats):
        prev, prev_result = None, None
        times = {"full": 0.0, "oracle": 0.0}
        counts = {}
        for idx, (frame, dx, dy) in enumerate(frames):
            def full():
                return apply_filter(frame, diameter)
            def oracle():
                if prev is None:
                    return full(), "initial"
                return reuse_with_known_shift(prev, prev_result, frame, dx, dy,
                                              diameter=diameter, tile=tile)
            methods = {"full": full, "oracle": oracle}
            order = ("full", "oracle") if (idx + repeat) % 2 == 0 else ("oracle", "full")
            results = {}
            for name in order:
                start = perf_counter()
                value = methods[name]()
                times[name] += (perf_counter() - start) * 1000
                if name == "oracle":
                    result, strategy = value
                    counts[strategy] = counts.get(strategy, 0) + 1
                else:
                    result = value
                results[name] = result
            error = int(np.max(cv2.absdiff(results["full"], results["oracle"])))
            max_pixel_error = max(max_pixel_error, error)
            if error:
                raise AssertionError(f"Pixel mismatch at frame {idx}: {error}")
            prev, prev_result = frame, results["oracle"]
        for name in timing:
            timing[name].append(times[name])
        if repeat == 0:
            strategy_counts = counts
    full_ms = statistics.median(timing["full"])
    oracle_ms = statistics.median(timing["oracle"])
    return {
        "frames": len(frames), "resolution": f"{frames[0][0].shape[1]}x{frames[0][0].shape[0]}",
        "diameter": diameter, "repeats": repeats,
        "full_ms": round(full_ms, 3), "oracle_ms": round(oracle_ms, 3),
        "speedup": round(full_ms / oracle_ms, 3), "max_pixel_error": max_pixel_error,
        "modes": strategy_counts, "known_shift_not_estimated": True
    }


def main():
    parser = argparse.ArgumentParser(description="ZERO-04: upper bound for known camera motion")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--diameter", type=int, default=15)
    parser.add_argument("--tile", type=int, default=64)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--shift-x", type=int, default=3)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("results/zero_04.json"))
    args = parser.parse_args()
    if args.frames < 2 or args.width < 160 or args.height < 120:
        parser.error("frames >= 2, width >= 160, height >= 120 required")
    output = {"experiment": "ZERO-04", "warning": "Translation supplied by synthetic generator, NOT estimated.", "results": {}}
    print("=== UNICORNIO LABS | ZERO-04 (known motion, bilateral filter) ===")
    for name in ("camera", "camera_object", "global"):
        frames = make_frames(name, args.frames, args.width, args.height, args.shift_x, args.shift_y)
        result = benchmark(frames, args.diameter, args.tile, args.repeats)
        output["results"][name] = result
        print(f"{name}: {result['speedup']:.2f}x | pixel error={result['max_pixel_error']} | modes={result['modes']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
