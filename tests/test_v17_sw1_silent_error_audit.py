import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw1_silent_error_audit as sw1  # noqa: E402


class V17Sw1SilentErrorAuditTests(unittest.TestCase):
    def test_extract_caption_truth(self):
        rows = [
            {
                "capture_date": "2026-02-25",
                "source_asset_id": "A1",
                "caption": "Taxi | tomato_15 | verified",
            },
            {
                "capture_date": "2026-02-25",
                "source_asset_id": "A2",
                "caption": "No token here",
            },
            {
                "capture_date": "2026-02-25",
                "source_asset_id": "A3",
                "caption": "Kale | non_tomato_09 | verified",
            },
        ]
        out = sw1.extract_caption_truth(rows)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["true_pot_id"], "15T")
        self.assertEqual(out[1]["true_pot_id"], "9T")

    def test_build_detail_rows_marks_silent_error(self):
        truth_rows = [
            {
                "run_date": "2026-03-01",
                "row_index": "88",
                "source_asset_id": "A1",
                "true_pot_id": "8T",
                "truth_source": "csv",
                "truth_note": "",
            }
        ]
        prediction_map = {
            ("2026-03-01", "88", "A1"): {
                "pot_id": "12T",
                "mapping_status": "ok",
                "final_status": "ready_auto_resolved",
                "resolution_source": "sequence_inference",
                "mapping_note": "pot_id_inferred_from_run_sequence",
            }
        }
        details = sw1.build_detail_rows(truth_rows, prediction_map)
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["pot_correct"], 0)
        self.assertEqual(details[0]["is_error"], 1)
        self.assertEqual(details[0]["is_silent_error"], 1)
        self.assertEqual(details[0]["error_class"], "silent_error")

    def test_build_summary_fails_when_silent_rate_high(self):
        detail_rows = [
            {"run_date": "2026-02-28", "is_error": 1, "is_silent_error": 1, "error_class": "silent_error", "resolution_source": "sequence_inference"},
            {"run_date": "2026-02-28", "is_error": 1, "is_silent_error": 1, "error_class": "silent_error", "resolution_source": "sequence_inference"},
            {"run_date": "2026-02-28", "is_error": 0, "is_silent_error": 0, "error_class": "correct", "resolution_source": "direct_detection"},
        ]
        summary = sw1.build_summary(detail_rows, ["2026-02-28"])
        self.assertEqual(summary["truth_rows"], 3)
        self.assertEqual(summary["total_errors"], 2)
        self.assertEqual(summary["silent_errors"], 2)
        self.assertEqual(summary["sw1_verdict"], "fail")


if __name__ == "__main__":
    unittest.main()
