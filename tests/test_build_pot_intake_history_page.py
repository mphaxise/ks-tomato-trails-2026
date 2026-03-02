import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_pot_intake_history_page as history_builder  # noqa: E402


class BuildPotIntakeHistoryPageTests(unittest.TestCase):
    def test_normalize_pot_id(self):
        self.assertEqual(history_builder.normalize_pot_id("1"), "1T")
        self.assertEqual(history_builder.normalize_pot_id("01T"), "1T")
        self.assertEqual(history_builder.normalize_pot_id(" pot-12 "), "12T")
        self.assertEqual(history_builder.normalize_pot_id("x"), "")

    def test_organize_by_pot_and_date(self):
        rows = [
            {"pot_id": "1T", "run_date": "2026-02-27", "variety_name": "Taxi"},
            {"pot_id": "1T", "run_date": "2026-03-01", "variety_name": "Taxi"},
            {"pot_id": "2T", "run_date": "2026-03-01", "variety_name": "Azoychka"},
        ]
        by_pot = history_builder.organize_by_pot_and_date(rows, expected_pots=2)
        self.assertIn("1T", by_pot)
        self.assertIn("2026-02-27", by_pot["1T"])
        self.assertEqual(by_pot["2T"]["2026-03-01"]["variety_name"], "Azoychka")

    def test_build_page_includes_pot_timeline(self):
        run_dates = ["2026-02-27", "2026-03-01"]
        reports = {
            "2026-02-27": {
                "selected_rows": 32,
                "unique_pot_count": 32,
                "ocr_confirmed_rows": 11,
                "final_status_counts": {"ready_auto_resolved": 32},
            },
            "2026-03-01": {
                "selected_rows": 32,
                "unique_pot_count": 32,
                "ocr_confirmed_rows": 2,
                "final_status_counts": {"ready_auto_resolved": 32},
            },
        }
        by_pot_date = {
            "1T": {
                "2026-02-27": {
                    "run_date": "2026-02-27",
                    "photo_url": "https://example.com/a.jpg",
                    "variety_name": "Taxi",
                    "source_asset_id": "asset_a",
                    "final_status": "ready_auto_resolved",
                    "resolution_source": "baseline_continuity",
                    "review_status_label": "Ready (Auto-Resolved)",
                },
                "2026-03-01": {
                    "run_date": "2026-03-01",
                    "photo_url": "https://example.com/b.jpg",
                    "variety_name": "Taxi",
                    "source_asset_id": "asset_b",
                    "final_status": "ready_auto_resolved",
                    "resolution_source": "manual_override",
                    "review_status_label": "Ready (Auto-Resolved)",
                },
            },
            "2T": {},
        }

        page = history_builder.build_page(
            input_csv=Path("sample.csv"),
            run_dates=run_dates,
            reports=reports,
            by_pot_date=by_pot_date,
        )
        self.assertIn("Pot Intake History Across Photo Runs", page)
        self.assertIn("id='pot-1T'", page)
        self.assertIn("id='pot-2T'", page)
        self.assertIn("2026-02-27", page)
        self.assertIn("No mapped photo for this intake", page)


if __name__ == "__main__":
    unittest.main()
