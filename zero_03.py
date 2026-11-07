"""ZERO-03: adaptive early-exit before full-frame change detection.

Known technique, intended as a controlled baseline: sample a regular pixel grid;
when changes appear widespread, process the full frame immediately. Otherwise
reuse ZERO-01's exactly validated region-update algorithm.
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
from zero_02 import SCENARIOS, synthetic_frames, video_frames


def adaptive_blur(previous_frame, previous_result, current_frame, *, kernel=15,
                  sample_stride=12, global_threshold=0.20):
    """Return (blurred frame, strategy, sampled change ratio).

    The grid is a hint only. A low sampled ratio NEVER skips full-resolution
    detection, so even changes between sampled pixels cannot be missed.
    """
    if previous_frame.shape != current_frame.shape or previous_result.shape != current_frame.shape:
        raise ValueError("Frame shapes must match")
    if sample_stride < 1 or not 0 < global_threshold <= 1:
        raise ValueError("sample_stride >= 1, 0 < global_threshold <= 1 required")
    if kernel < 3 or kernel % 2 == 0:
        raise ValueError("kernel must be odd and >= 3")
    old_sample = previous_frame[::sample_stride, ::sample_stride]
    new_sample = current_frame[::sample_stride, ::sample_stride]
    ratio = float(np.count_nonzero(np.any(old_sample != new_sample, axis=2))) / old_sample.shape[0] / old_sample.shape[1]
    if ratio >= global_threshold:
        return cv2.GaussianBlur(current_frame, (kernel, kernel), 0), "early_full", ratio
    output, _, strategy = incremental_blur(previous_frame, previous_result, current_frame, kernel)
    return output, strategy, ratio


def benchmark(frames, *, repeats=3, kernel=15, stride=12, threshold=0.20):
    """Benchmark each method against identical decoded input frames."""
    if len(frames) < 2 or repeats < 1:
        raise ValueError("At least 2 frames and 1 repetition required")
    cv2.setNumThreads(1)
    cv2.GaussianBlur(frames[0], (kernel, kernel), 0)
    timings = {"full": [], "zero_02": [], "adaptive": []}
    strategy_counts = {}
    sampled_ratios = []
    max_error = 0
    for iteration in range(repeats):
        totals = {name: 0.0 for name in timings}
        old_frame, old_result = None, None
        iteration_counts = {}
        ratios = []
        for index, frame in enumerate(frames):
            def run_full():
                return cv2.GaussianBlur(frame, (kernel, kernel), 0)

            def run_legacy():
                if old_frame is None:
                    return run_full()
                return incremental_blur(old_frame, old_result, frame, kernel)[0]

            def run_adaptive():
                if old_frame is None:
                    return run_full(), "initial_full", 1.0
                return adaptive_blur(old_frame, old_result, frame,
                                     kernel=kernel, sample_stride=stride,
                                     global_threshold=threshold)

            tasks = {"full": run_full, "zero_02": run_legacy, "adaptive": run_adaptive}
            names = list(tasks)
            rotation = (index + iteration) % 3
            names = names[rotation:] + names[:rotation]
            outputs = {}
            for name in names:
                begin = perf_counter()
                value = tasks[name]()
                totals[name] += (perf_counter() - begin) * 1000
                if name == "adaptive":
                    output, strategy, ratio = value
                    iteration_counts[strategy] = iteration_counts.get(strategy, 0) + 1
                    if old_frame is not None:
                        ratios.append(ratio)
                else:
                    output = value
                outputs[name] = output
            for name in ("zero_02", "adaptive"):
                error = int(np.max(cv2.absdiff(outputs["full"], outputs[name])))
                max_error = max(max_error, error)
                if error:
                    raise AssertionError(f"Frame {index}, {name}: maximum pixel error {error}")
            old_frame, old_result = frame, outputs["full"]
        for name in timings:
            timings[name].append(totals[name])
        if iteration == 0:
            strategy_counts = iteration_counts
            sampled_ratios = ratios
    medians = {name: statistics.median(values) for name, values in timings.items()}
    return {
        "frames": len(frames),
        "resolution": f"{frames[0].shape[1]}x{frames[0].shape[0]}",
        "repeats": repeats,
        "kernel": kernel,
        "sample_stride": stride,
        "global_threshold": threshold,
        "median_total_ms": {name: round(value, 3) for name, value in medians.items()},
        "zero_02_vs_full": round(medians["full"] / medians["zero_02"], 3),
        "adaptive_vs_full": round(medians["full"] / medians["adaptive"], 3),
        "adaptive_vs_zero_02": round(medians["zero_02"] / medians["adaptive"], 3),
        "sampled_change_percent": round(statistics.mean(sampled_ratios) * 100, 2),
        "adaptive_strategy_counts_first_repeat": strategy_counts,
        "max_pixel_error": max_error,
    }


def run(*, scenario="all", video=None, frames=60, width=960, height=540,
        repeats=3, kernel=15, stride=12, threshold=0.20,
        output=Path("results/zero_03.json")):
    if frames < 2 or width < 160 or height < 120 or repeats < 1:
        raise ValueError("frames >= 2; width >= 160; height >= 120; repeats >= 1 required")
    if scenario == "video" and not video:
        raise ValueError("--video required when scenario is video")
    if scenario not in ("all", "video", *SCENARIOS):
        raise ValueError("Unknown scenario")
    report = {
        "experiment": "ZERO-03",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": "CPU wall-clock; excludes decode/resize and I/O; not a measurement of video AI generation or electrical energy.",
        "results": {},
    }
    targets = SCENARIOS if scenario == "all" else (scenario,)
    print("=== UNICORNIO LABS | ZERO-03 ===")
    for target in targets:
        source = (video_frames(video, frames, width, height) if target == "video"
                  else synthetic_frames(target, frames, width, height))
        result = benchmark(list(source), repeats=repeats, kernel=kernel, stride=stride,
                           threshold=threshold)
        report["results"][target] = result
        print(f"{target}: previous={result['zero_02_vs_full']:.2f}x | "
              f"adaptive={result['adaptive_vs_full']:.2f}x | "
              f"vs previous={result['adaptive_vs_zero_02']:.2f}x | "
              f"pixel error={result['max_pixel_error']}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {output.resolve()}")
    return report


def main():
    parser = argparse.ArgumentParser(description="ZERO-03: adaptive early-exit experiment")
    parser.add_argument("--scenario", choices=("all", "video", *SCENARIOS), default="all")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--kernel", type=int, default=15)
    parser.add_argument("--stride", type=int, default=12)
    parser.add_argument("--threshold", type=float, default=0.20)
    parser.add_argument("--output", type=Path, default=Path("results/zero_03.json"))
    args = parser.parse_args()
    try:
        run(scenario=args.scenario, video=args.video, frames=args.frames,
            width=args.width, height=args.height, repeats=args.repeats,
            kernel=args.kernel, stride=args.stride, threshold=args.threshold,
            output=args.output)
    except (ValueError, AssertionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
