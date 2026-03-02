import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw0_ocr_crop_diagnosis as sw0  # noqa: E402


class V17Sw0OcrCropDiagnosisTests(unittest.TestCase):
    def test_choose_sample_rows_round_robin_by_run(self):
        rows = [
            {"run_date": "2026-02-28", "row_index": "1"},
            {"run_date": "2026-02-28", "row_index": "2"},
            {"run_date": "2026-03-01", "row_index": "1"},
            {"run_date": "2026-03-01", "row_index": "2"},
        ]
        sampled = sw0.choose_sample_rows(rows, sample_size=3)
        self.assertEqual(len(sampled), 3)
        self.assertEqual(sampled[0]["run_date"], "2026-02-28")
        self.assertEqual(sampled[1]["run_date"], "2026-03-01")

    def test_classify_proxy_root_cause_crop_targeting(self):
        cls, reason = sw0.classify_proxy_root_cause(
            expected_pot_number=7,
            label_numbers=[],
            non_label_numbers=[2, 4],
            label_match_any=False,
            non_label_match_any=False,
        )
        self.assertEqual(cls, "crop_targeting_likely_wrong")
        self.assertIn("non-label", reason)

    def test_classify_proxy_root_cause_ambient_numbers(self):
        cls, reason = sw0.classify_proxy_root_cause(
            expected_pot_number=7,
            label_numbers=[2],
            non_label_numbers=[4],
            label_match_any=False,
            non_label_match_any=False,
        )
        self.assertEqual(cls, "ambient_numbers_no_pot_signal")
        self.assertIn("digits", reason)


if __name__ == "__main__":
    unittest.main()
