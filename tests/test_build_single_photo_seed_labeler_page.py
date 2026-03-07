import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_single_photo_seed_labeler_page as builder  # noqa: E402


class BuildSinglePhotoSeedLabelerPageTests(unittest.TestCase):
    def test_build_page_contains_fabric_export_and_task_mode_controls(self):
        html = builder.build_page("../local/non_tomato_species/images/example.jpg")
        self.assertIn("fabric.min.js", html)
        self.assertIn("Single Photo Seed Labeler", html)
        self.assertIn("Export JSON", html)
        self.assertIn("Export CSV", html)
        self.assertIn("Draw Mode", html)
        self.assertIn("id=\"fabric-canvas\"", html)
        self.assertIn("id=\"add-level\"", html)
        self.assertIn("id=\"levels-body\"", html)
        self.assertIn("task-meta-card", html)
        self.assertIn("new URLSearchParams(window.location.search)", html)
        self.assertIn("pot_region", html)
        self.assertIn("pot_interior", html)


if __name__ == "__main__":
    unittest.main()
