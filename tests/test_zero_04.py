"""ZERO-04 correctness tests; camera displacement is known, not estimated."""
import unittest

import cv2
import numpy as np

from zero_04 import apply_filter, benchmark, make_frames, reuse_with_known_shift


class MotionReuseTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(71)
        self.old = rng.integers(10, 220, size=(180, 320, 3), dtype=np.uint8)
        self.old_filtered = apply_filter(self.old, 15)

    def check_equal(self, current, dx=0, dy=0):
        actual, _ = reuse_with_known_shift(
            self.old, self.old_filtered, current, dx, dy, diameter=15
        )
        reference = apply_filter(current, 15)
        np.testing.assert_array_equal(actual, reference)

    def test_translation_only(self):
        self.check_equal(np.roll(self.old, (0, 3), axis=(0, 1)), dx=3)

    def test_translation_and_local_edit(self):
        frame = np.roll(self.old, (2, 3), axis=(0, 1))
        frame[60:80, 85:120] = (255, 0, 50)
        self.check_equal(frame, dx=3, dy=2)

    def test_global_change(self):
        self.check_equal(np.zeros_like(self.old))

    def test_translation_near_border(self):
        frame = np.roll(self.old, (-2, -4), axis=(0, 1))
        frame[0:7, :9] = (50, 25, 200)
        self.check_equal(frame, dx=-4, dy=-2)

    def test_benchmark_synthetic(self):
        result = benchmark(make_frames("camera_object", 5, 320, 180), repeats=1)
        self.assertEqual(result["max_pixel_error"], 0)
        self.assertTrue(result["known_shift_not_estimated"])


if __name__ == "__main__":
    unittest.main()
