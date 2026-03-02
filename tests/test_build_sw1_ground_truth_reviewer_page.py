import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_sw1_ground_truth_reviewer_page as builder  # noqa: E402


class BuildSw1GroundTruthReviewerPageTests(unittest.TestCase):
    def test_build_page_contains_expected_controls(self):
        rows = [
            {
                "run_date": "2026-02-28",
                "row_index": "59",
                "source_asset_id": "AF1QipPdG_T6UaPw",
                "photo_url": "https://example.com/photo.jpg",
                "predicted_pot_id": "1T",
                "predicted_pot_number": "1",
                "ocr_match_variants": "0",
                "ocr_numbers_detected": "2,3,4",
                "label_crop_path": "label.jpg",
                "center_crop_path": "center.jpg",
                "full_crop_path": "full.jpg",
                "label_crop_url": "./assets/label.jpg",
                "center_crop_url": "./assets/center.jpg",
                "full_crop_url": "./assets/full.jpg",
                "true_pot_id": "",
                "true_variety_name": "",
                "truth_source": "",
                "truth_note": "",
                "reviewer": "",
                "reviewed_at": "",
            }
        ]
        html = builder.build_page(Path("template.csv"), rows)
        self.assertIn("SW-1 Weak-Run Ground Truth Reviewer", html)
        self.assertIn("Export Reviewed Ground Truth CSV", html)
        self.assertIn("id=\"run-filter\"", html)
        self.assertIn("id=\"status-filter\"", html)
        self.assertIn("predicted_pot_id", html)


if __name__ == "__main__":
    unittest.main()
