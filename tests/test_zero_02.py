"""Correctness and basic controls for ZERO-02."""
import tempfile
import unittest
from pathlib import Path

from zero_02 import benchmark, run, synthetic_frames


class Zero02Tests(unittest.TestCase):
    def test_static(self):
        outcome = benchmark(list(synthetic_frames("static", 5, 160, 120)), repeats=1)
        self.assertEqual(outcome["max_pixel_error"], 0)
        self.assertEqual(outcome["frames"], 5)

    def test_camera(self):
        outcome = benchmark(list(synthetic_frames("camera", 5, 160, 120)), repeats=1)
        self.assertEqual(outcome["max_pixel_error"], 0)

    def test_global(self):
        outcome = benchmark(list(synthetic_frames("global", 5, 160, 120)), repeats=1)
        self.assertEqual(outcome["max_pixel_error"], 0)

    def test_requires_video_path(self):
        with self.assertRaises(ValueError):
            run(scenario="video")

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run(scenario="static", frames=4, width=160, height=120,
                         repeats=1, output=Path(temp) / "out.json")
            self.assertIn("static", report["results"])
            self.assertTrue((Path(temp) / "out.json").exists())


if __name__ == "__main__":
    unittest.main()
