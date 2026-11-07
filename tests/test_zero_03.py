"""ZERO-03: grid sampling cannot undermine pixel-perfect correctness."""
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from zero_03 import adaptive_blur, benchmark, run
from zero_02 import synthetic_frames


class Zero03Tests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(5)
        self.previous = self.rng.integers(0, 255, size=(120, 180, 3), dtype=np.uint8)
        self.cached = cv2.GaussianBlur(self.previous, (15, 15), 0)

    def assert_exact(self, next_frame, stride=12):
        updated, _, _ = adaptive_blur(self.previous, self.cached, next_frame, sample_stride=stride)
        np.testing.assert_array_equal(updated, cv2.GaussianBlur(next_frame, (15, 15), 0))

    def test_no_change(self):
        self.assert_exact(self.previous)

    def test_single_pixel_unseen_by_grid(self):
        changed = self.previous.copy()
        changed[13, 13] = (0, 0, 0)
        self.assert_exact(changed, stride=12)

    def test_global_difference_early_exit(self):
        changed = np.zeros_like(self.previous)
        updated, method, _ = adaptive_blur(self.previous, self.cached, changed)
        self.assertEqual(method, "early_full")
        np.testing.assert_array_equal(updated, cv2.GaussianBlur(changed, (15, 15), 0))

    def test_camera_changes_exact(self):
        frames = list(synthetic_frames("camera", 5, 160, 120))
        result = benchmark(frames, repeats=1)
        self.assertEqual(result["max_pixel_error"], 0)
        self.assertGreater(result["adaptive_strategy_counts_first_repeat"].get("early_full", 0), 0)

    def test_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            result = run(scenario="static", frames=4, width=160, height=120, repeats=1, output=path)
            self.assertTrue(path.exists())
            self.assertIn("static", result["results"])


if __name__ == "__main__":
    unittest.main()
