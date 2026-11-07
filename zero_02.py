"""ZERO-02: study when incremental image processing stops being useful.

This is a CPU-only benchmark, not a claim of a new algorithm. It compares
whole-frame Gaussian blur with ZERO-01's region-based incremental blur.
"""

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from zero_01 import incremental_blur


SCENARIOS = ("static", "camera", "global")


def synthetic_frames(scenario, count=60, width=960, height=540):
    """Deterministic scenes with fixed camera, panning, or global changes."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    rng = np.random.default_rng(2026)
    background = rng.integers(30, 210, size=(height, width, 3), dtype=np.uint8)
    # Keep synthesis outside timed operations.
    for index in range(count):
        if scenario == "camera":
            frame = np.roll(background, shift=3 * index, axis=1).copy()
        elif scenario == "global":
            frame = cv2.add(background, (index * 7) % 45).copy()
        else:
            frame = background.copy()
        x = (15 + index * 3) % max(1, width - 95)
        y = max(0, min(height - 70, height // 3))
        cv2.rectangle(frame, (x, y), (min(x + 84, width - 1), min(y + 54, height - 1)), (15, 175, 245), -1)
        yield frame


def video_frames(path, count, width, height):
    """Read a video frame-by-frame; video decoding is not included in timing."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    try:
        for _ in range(count):
            ok, frame = capture.read()
            if not ok:
                break
            yield cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    finally:
        capture.release()


def benchmark(frames, kernel=15, repeats=3):
    """Measure median wall-clock totals. Verify exact output on every frame."""
    if repeats < 1 or kernel < 3 or kernel % 2 == 0:
        raise ValueError("repeats must be >= 1 and kernel odd >= 3")
    if len(frames) < 2:
        raise ValueError("At least two frames are required")
    cv2.setNumThreads(1)
    cv2.GaussianBlur(frames[0], (kernel, kernel), 0)  # warm up
    full_times, incremental_times = [], []
    methods, fractions, max_error = {}, [], 0

    for repetition in range(repeats):
        previous_frame, previous_blur = None, None
        full_total, incremental_total = 0.0, 0.0
        round_methods, round_fractions = {}, []
        for index, frame in enumerate(frames):
            def full():
                start = perf_counter()
                output = cv2.GaussianBlur(frame, (kernel, kernel), 0)
                return output, perf_counter() - start

            def incremental():
                start = perf_counter()
                if previous_frame is None:
                    output = cv2.GaussianBlur(frame, (kernel, kernel), 0)
                    fraction, method = 1.0, "completo"
                else:
                    output, fraction, method = incremental_blur(
                        previous_frame, previous_blur, frame, kernel
                    )
                return output, perf_counter() - start, fraction, method

            # Change execution order to reduce systematic first-run advantage.
            if (index + repetition) % 2:
                updated, incremental_elapsed, fraction, method = incremental()
                reference, full_elapsed = full()
            else:
                reference, full_elapsed = full()
                updated, incremental_elapsed, fraction, method = incremental()
            error = int(np.max(cv2.absdiff(reference, updated)))
            max_error = max(max_error, error)
            if error:
                raise AssertionError(f"Frame {index}: max pixel error {error}")
            full_total += full_elapsed
            incremental_total += incremental_elapsed
            round_methods[method] = round_methods.get(method, 0) + 1
            if index > 0:
                round_fractions.append(fraction)
            previous_frame, previous_blur = frame, updated
        full_times.append(full_total * 1000)
        incremental_times.append(incremental_total * 1000)
        if repetition == 0:
            methods, fractions = round_methods, round_fractions

    median_full = statistics.median(full_times)
    median_incremental = statistics.median(incremental_times)
    return {
        "frames": len(frames),
        "resolution": f"{frames[0].shape[1]}x{frames[0].shape[0]}",
        "kernel": kernel,
        "repeats": repeats,
        "median_full_ms": round(median_full, 3),
        "median_incremental_ms": round(median_incremental, 3),
        "speedup": round(median_full / median_incremental, 3),
        "saved_time_percent": round((1 - median_incremental / median_full) * 100, 2),
        "average_changed_bbox_percent": round(statistics.mean(fractions) * 100, 2),
        "method_counts_first_repeat": methods,
        "max_pixel_error": max_error,
    }


def run(scenario="all", video=None, frames=60, width=960, height=540,
        kernel=15, repeats=3, output=Path("results/zero_02.json")):
    if frames < 2 or width < 160 or height < 120 or repeats < 1:
        raise ValueError("frames >= 2, width >= 160, height >= 120, repeats >= 1")
    if scenario == "video" and video is None:
        raise ValueError("--video is required when scenario is video")
    if scenario not in ("all", "video", *SCENARIOS):
        raise ValueError(f"Unknown scenario: {scenario}")
    targets = SCENARIOS if scenario == "all" else (scenario,)
    report = {
        "experiment": "ZERO-02",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": "CPU wall-clock only; excludes decode/resize; no energy measurement",
        "results": {},
    }
    print("=== UNICORNIO LABS | ZERO-02 ===")
    for target in targets:
        source = (video_frames(video, frames, width, height) if target == "video"
                  else synthetic_frames(target, frames, width, height))
        samples = list(source)
        result = benchmark(samples, kernel=kernel, repeats=repeats)
        report["results"][target] = result
        print(f"{target}: {result['speedup']:.2f}x | saved {result['saved_time_percent']:.1f}% | "
              f"bbox {result['average_changed_bbox_percent']:.1f}% | error {result['max_pixel_error']}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {output.resolve()}")
    return report


def main():
    parser = argparse.ArgumentParser(description="ZERO-02: incremental update limits")
    parser.add_argument("--scenario", choices=("all", "video", *SCENARIOS), default="all")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--kernel", type=int, default=15)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("results/zero_02.json"))
    args = parser.parse_args()
    try:
        run(args.scenario, args.video, args.frames, args.width, args.height,
            args.kernel, args.repeats, args.output)
    except (ValueError, AssertionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
