import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_tomato_trails_page as builder  # noqa: E402


class BuildTomatoTrailsPageTests(unittest.TestCase):
    def test_build_tomato_run_rows_excludes_non_tomato_rows(self):
        rows = [
            {
                "capture_date": "2026-02-27",
                "classification_label": "tomato",
                "source_asset_id": "asset_tomato",
                "variety_name": "Taxi",
                "species_scientific_name": "",
            },
            {
                "capture_date": "2026-02-27",
                "classification_label": "non_tomato",
                "source_asset_id": "asset_non_tomato",
                "variety_name": "Spinach",
                "species_scientific_name": "",
            },
        ]

        result = builder.build_tomato_run_rows(
            rows=rows,
            run_date="2026-02-27",
            mapping_by_asset={},
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_asset_id"], "asset_tomato")
        self.assertEqual(result[0]["classification_label"], "tomato")

    def test_build_tomato_run_rows_excludes_unknown_without_mapping(self):
        rows = [
            {
                "capture_date": "2026-02-27",
                "classification_label": "unknown",
                "source_asset_id": "asset_unknown",
                "variety_name": "",
                "species_scientific_name": "",
            }
        ]
        result = builder.build_tomato_run_rows(
            rows=rows,
            run_date="2026-02-27",
            mapping_by_asset={},
        )
        self.assertEqual(result, [])

    def test_main_rewrites_page_title_for_tomato_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_csv = tmp_path / "input.csv"
            mapping_csv = tmp_path / "mapping.csv"
            output_html = tmp_path / "tomato.html"

            with input_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "classification_label",
                        "source_asset_id",
                        "photo_url",
                        "species_common_name",
                        "variety_name",
                        "species_scientific_name",
                        "specific_note",
                        "weather_hypothesis",
                        "expected_harvest_window",
                        "confidence",
                        "labeling_method",
                        "caption",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-02-27",
                        "classification_label": "tomato",
                        "source_asset_id": "asset_1",
                        "photo_url": "https://example.com/1.jpg",
                        "species_common_name": "Tomato",
                        "variety_name": "Taxi",
                        "species_scientific_name": "",
                        "specific_note": "",
                        "weather_hypothesis": "",
                        "expected_harvest_window": "",
                        "confidence": "0.9",
                        "labeling_method": "manual",
                        "caption": "Taxi",
                    }
                )

            with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["source_asset_id", "pot_id", "packet_number", "variety_name"],
                )
                writer.writeheader()

            exit_code = builder.main(
                [
                    "--input-csv",
                    str(input_csv),
                    "--mapping-csv",
                    str(mapping_csv),
                    "--run-date",
                    "2026-02-27",
                    "--output-html",
                    str(output_html),
                ]
            )
            self.assertEqual(exit_code, 0)

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn(
                "<title>K's Tomato Trails 2026: Tomato Pots View-Only (2026-02-27)</title>",
                rendered,
            )

    def test_build_tomato_run_rows_uses_mapping_review_status_fields(self):
        rows = [
            {
                "capture_date": "2026-02-28",
                "classification_label": "unknown",
                "source_asset_id": "asset_1",
                "variety_name": "",
                "species_scientific_name": "",
                "specific_note": "",
            }
        ]
        mapping = {
            "asset_1": {
                "source_asset_id": "asset_1",
                "pot_id": "1T",
                "packet_number": "4",
                "variety_name": "Taxi",
                "final_status": "ready_auto_resolved",
                "review_stage": "none",
                "resolution_source": "baseline_continuity",
                "review_status_label": "Ready (Auto-Resolved)",
                "context_id": "container_round_1",
                "mapping_status": "ok",
                "mapping_note": "series_from_baseline_pot_mapping",
            }
        }
        result = builder.build_tomato_run_rows(
            rows=rows,
            run_date="2026-02-28",
            mapping_by_asset=mapping,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["classification_label"], "tomato")
        self.assertEqual(result[0]["review_status_label"], "Ready (Auto-Resolved)")
        self.assertEqual(result[0]["resolution_source"], "baseline_continuity")
        self.assertIn("Status: Ready (Auto-Resolved)", result[0]["specific_note"])


if __name__ == "__main__":
    unittest.main()
