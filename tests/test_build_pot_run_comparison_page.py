import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_pot_run_comparison_page as comp_builder  # noqa: E402


class BuildPotRunComparisonPageTests(unittest.TestCase):
    def test_compare_status_flags_continuity_lock(self):
        row_a = {
            "variety_name": "Taxi",
            "resolution_source": "baseline_continuity",
            "mapping_note": "series_from_baseline_pot_mapping",
        }
        row_b = {
            "variety_name": "Taxi",
            "resolution_source": "manual_override",
            "mapping_note": "series_from_manual_pot_override",
        }
        text, css = comp_builder.compare_status(row_a, row_b)
        self.assertEqual(css, "risk")
        self.assertIn("Continuity lock", text)

    def test_compare_status_flags_drift(self):
        row_a = {"variety_name": "Taxi", "resolution_source": "baseline_continuity"}
        row_b = {"variety_name": "Azoychka", "resolution_source": "baseline_continuity"}
        text, css = comp_builder.compare_status(row_a, row_b)
        self.assertEqual(css, "drift")
        self.assertIn("Variety mismatch", text)

    def test_build_page_contains_filter_buttons(self):
        page = comp_builder.build_page(
            run_a="2026-02-28",
            run_b="2026-03-01",
            report_a={"selected_rows": 32, "unique_pot_count": 32, "ocr_confirmed_rows": 1},
            report_b={"selected_rows": 32, "unique_pot_count": 32, "ocr_confirmed_rows": 2},
            by_pot_a={"1T": {"pot_id": "1T", "photo_url": "https://example.com/a.jpg", "variety_name": "Taxi", "resolution_source": "baseline_continuity", "mapping_note": ""}},
            by_pot_b={"1T": {"pot_id": "1T", "photo_url": "https://example.com/b.jpg", "variety_name": "Taxi", "resolution_source": "manual_override", "mapping_note": ""}},
            expected_pots=1,
            input_csv=Path("sample.csv"),
        )
        self.assertIn("Pot Comparison View: 2026-02-28 vs 2026-03-01", page)
        self.assertIn("Continuity Lock Risk", page)
        self.assertIn("Variety Drift", page)


if __name__ == "__main__":
    unittest.main()
