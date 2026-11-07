"""Pruebas de correccion: las optimizaciones no deben modificar el resultado."""

import unittest

import cv2
import numpy as np

from zero_01 import incremental_blur, synthetic_frames


class IncrementalBlurTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(12)
        self.original = self.rng.integers(0, 255, size=(120, 180, 3), dtype=np.uint8)
        self.kernel = 15
        self.initial_blur = cv2.GaussianBlur(self.original, (self.kernel, self.kernel), 0)

    def check_matches_full_blur(self, current):
        actual, _, _ = incremental_blur(self.original, self.initial_blur, current, self.kernel)
        expected = cv2.GaussianBlur(current, (self.kernel, self.kernel), 0)
        np.testing.assert_array_equal(actual, expected)

    def test_no_changes(self):
        actual, fraction, method = incremental_blur(self.original, self.initial_blur, self.original)
        np.testing.assert_array_equal(actual, self.initial_blur)
        self.assertEqual(fraction, 0)
        self.assertEqual(method, "sin_cambios")

    def test_change_center(self):
        current = self.original.copy()
        current[40:60, 55:85] = (255, 0, 0)
        self.check_matches_full_blur(current)

    def test_change_near_edges(self):
        current = self.original.copy()
        current[0:12, 0:15] = (0, 255, 0)
        current[112:, 170:] = (0, 0, 255)
        self.check_matches_full_blur(current)

    def test_large_change_falls_back(self):
        current = np.zeros_like(self.original)
        self.check_matches_full_blur(current)

    def test_moving_object_sequence(self):
        frames = list(synthetic_frames(8, 240, 160))
        previous_frame = frames[0]
        previous_blur = cv2.GaussianBlur(previous_frame, (self.kernel, self.kernel), 0)
        for frame in frames[1:]:
            previous_blur, _, _ = incremental_blur(previous_frame, previous_blur, frame, self.kernel)
            np.testing.assert_array_equal(previous_blur, cv2.GaussianBlur(frame, (self.kernel, self.kernel), 0))
            previous_frame = frame


if __name__ == "__main__":
    unittest.main()
