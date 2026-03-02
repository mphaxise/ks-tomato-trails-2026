import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw1_build_ground_truth_template as sw1_template  # noqa: E402


class V17Sw1BuildGroundTruthTemplateTests(unittest.TestCase):
    def test_round_robin_sample_balances_run_dates(self):
        rows = [
            {"run_date": "2026-02-28", "row_index": "1"},
            {"run_date": "2026-02-28", "row_index": "2"},
            {"run_date": "2026-03-01", "row_index": "1"},
            {"run_date": "2026-03-01", "row_index": "2"},
        ]
        sampled = sw1_template.round_robin_sample(rows, sample_size=3)
        self.assertEqual(len(sampled), 3)
        self.assertEqual(sampled[0]["run_date"], "2026-02-28")
        self.assertEqual(sampled[1]["run_date"], "2026-03-01")
        self.assertEqual(sampled[2]["run_date"], "2026-02-28")

    def test_to_template_rows_carries_prediction_fields(self):
        rows = [
            {
                "run_date": "2026-02-28",
                "row_index": "59",
                "source_asset_id": "A1",
                "photo_url": "https://example.com/a1.jpg",
                "pot_id": "1T",
                "pot_number": "1",
                "matched_variant_count": "0",
                "ensemble_numbers_detected": "2,3,4",
                "label_crop_path": "label.jpg",
                "center_crop_path": "center.jpg",
                "full_crop_path": "full.jpg",
            }
        ]
        out = sw1_template.to_template_rows(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["predicted_pot_id"], "1T")
        self.assertEqual(out[0]["ocr_numbers_detected"], "2,3,4")
        self.assertEqual(out[0]["true_pot_id"], "")


if __name__ == "__main__":
    unittest.main()
