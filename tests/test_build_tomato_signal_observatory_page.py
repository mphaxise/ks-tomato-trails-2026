import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_tomato_signal_observatory_page as builder  # noqa: E402


class BuildTomatoSignalObservatoryPageTests(unittest.TestCase):
    def test_map_warning_rows_groups_warnings_by_pot(self):
        warning_map = builder.map_warning_rows(
            [
                "row 425: pot 1T override series=7 replaces detected series=2",
                "row 430: pot 6T override series=1 replaces detected series=23",
                "row 999: unrelated warning with no pot id",
            ]
        )

        self.assertEqual(len(warning_map["1T"]), 1)
        self.assertEqual(len(warning_map["6T"]), 1)
        self.assertNotIn("999T", warning_map)

    def test_build_page_contains_observatory_sections(self):
        page = builder.build_page(
            latest_run="2026-03-11",
            previous_run="2026-03-07",
            run_summaries=[
                {
                    "run_date": "2026-03-07",
                    "short_date": "Mar 7",
                    "photo_rows": 45,
                    "mapped_pots": 32,
                    "ocr_confirmed_rows": 2,
                    "continuity_rows": 32,
                    "warning_count": 37,
                    "batch_mode": "mixed",
                },
                {
                    "run_date": "2026-03-11",
                    "short_date": "Mar 11",
                    "photo_rows": 32,
                    "mapped_pots": 32,
                    "ocr_confirmed_rows": 0,
                    "continuity_rows": 32,
                    "warning_count": 20,
                    "batch_mode": "census",
                },
            ],
            cards=[
                {
                    "pot_id": "1T",
                    "pot_number": 1,
                    "variety_name": "Sunset's Red Horizon",
                    "status_class": "risk",
                    "status_label": "continuity lock",
                    "status_text": "Continuity lock: same assignment both days without OCR confirmation",
                    "previous_run": "2026-03-07",
                    "latest_run": "2026-03-11",
                    "previous_photo_url": "https://example.com/prev.jpg",
                    "latest_photo_url": "https://example.com/latest.jpg",
                    "previous_resolution": "manual override",
                    "latest_resolution": "manual override",
                    "previous_ocr": False,
                    "latest_ocr": False,
                    "latest_warning_count": 1,
                    "latest_warnings": ["row 425: pot 1T override series=7 replaces detected series=2"],
                    "latest_mapping_note": "series_from_manual_pot_override",
                    "source_asset_id": "asset-1",
                },
                {
                    "pot_id": "4T",
                    "pot_number": 4,
                    "variety_name": "San Francisco Fog",
                    "status_class": "info",
                    "status_label": "partial OCR",
                    "status_text": "Partially OCR confirmed",
                    "previous_run": "2026-03-07",
                    "latest_run": "2026-03-11",
                    "previous_photo_url": "https://example.com/prev-4.jpg",
                    "latest_photo_url": "https://example.com/latest-4.jpg",
                    "previous_resolution": "manual override",
                    "latest_resolution": "manual override",
                    "previous_ocr": True,
                    "latest_ocr": False,
                    "latest_warning_count": 0,
                    "latest_warnings": [],
                    "latest_mapping_note": "ocr_confirms_pot_number",
                    "source_asset_id": "asset-4",
                },
            ],
            source_csv=Path("sample.csv"),
            latest_report={"expected_pots": 32},
        )

        self.assertIn("Tomato Signal Observatory", page)
        self.assertIn("Batch Rhythm", page)
        self.assertIn("Compare Deck", page)
        self.assertIn("Continuity Lock", page)
        self.assertIn("Sunset's Red Horizon", page)
        self.assertIn("2026-03-11", page)


if __name__ == "__main__":
    unittest.main()
