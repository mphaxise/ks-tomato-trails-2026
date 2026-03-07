import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v110_mask_seed_page as builder  # noqa: E402


class BuildV110MaskSeedPageTests(unittest.TestCase):
    def test_select_seed_rows_orders_by_priority(self):
        rows = [
            {
                "priority_rank": "3",
                "pot_id": "7T",
                "variety_name": "Sasha Altai",
                "tracking_readiness": "moderate",
                "focus_score": "0.62",
                "pot_coverage": "0.03",
                "neighbor_spill_ratio": "0.10",
                "spill_in_pot_ratio": "0.19",
            },
            {
                "priority_rank": "1",
                "pot_id": "9T",
                "variety_name": "Iles Yellow Latvian",
                "tracking_readiness": "high",
                "focus_score": "0.80",
                "pot_coverage": "0.05",
                "neighbor_spill_ratio": "0.00",
                "spill_in_pot_ratio": "0.00",
            },
            {
                "priority_rank": "8",
                "pot_id": "21T",
                "variety_name": "Sasha Altai",
                "tracking_readiness": "moderate",
                "focus_score": "0.51",
                "pot_coverage": "0.04",
                "neighbor_spill_ratio": "0.54",
                "spill_in_pot_ratio": "0.54",
            },
        ]

        selected = builder.select_seed_rows(rows, max_seeds=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["pot_id"], "9T")
        self.assertEqual(selected[0]["seed_rank"], "1")
        self.assertEqual(selected[0]["queue_priority_rank"], "1")
        self.assertIn("seed_note", selected[0])

    def test_build_page_outputs_expected_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            queue_csv = tmp_path / "queue.csv"
            summary_json = tmp_path / "summary.json"
            seed_csv = tmp_path / "seed.csv"
            output_html = tmp_path / "out.html"

            with queue_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "priority_rank",
                        "pot_id",
                        "variety_name",
                        "tracking_readiness",
                        "focus_score",
                        "pot_coverage",
                        "neighbor_spill_ratio",
                        "spill_in_pot_ratio",
                        "chlorosis_ratio",
                        "growth_delta",
                        "capture_date",
                        "labeling_note",
                        "overlay_path",
                        "crop_path",
                        "photo_url",
                        "source_asset_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "priority_rank": "1",
                        "pot_id": "9T",
                        "variety_name": "Iles Yellow Latvian",
                        "tracking_readiness": "high",
                        "focus_score": "0.80",
                        "pot_coverage": "0.05",
                        "neighbor_spill_ratio": "0.00",
                        "spill_in_pot_ratio": "0.00",
                        "chlorosis_ratio": "0.03",
                        "growth_delta": "",
                        "capture_date": "2026-03-06",
                        "labeling_note": "Best starter mask candidate.",
                        "overlay_path": "assets/v1-10-pot-cv/9t_overlay.jpg",
                        "crop_path": "assets/v1-10-pot-cv/9t_crop.jpg",
                        "photo_url": "https://example.com/photo.jpg",
                        "source_asset_id": "A9",
                    }
                )

            summary_json.write_text(
                json.dumps({"run_date": "2026-03-06", "created_at": "2026-03-07T04:15:42Z"}),
                encoding="utf-8",
            )

            seed_rows = builder.select_seed_rows(builder.read_csv_rows(queue_csv))
            builder.write_csv_rows(
                seed_csv,
                [
                    "seed_rank",
                    "queue_priority_rank",
                    "seed_priority_score",
                    "pot_id",
                    "variety_name",
                    "tracking_readiness",
                    "focus_score",
                    "pot_coverage",
                    "neighbor_spill_ratio",
                    "spill_in_pot_ratio",
                    "chlorosis_ratio",
                    "growth_delta",
                    "capture_date",
                    "labeling_note",
                    "seed_note",
                    "overlay_path",
                    "crop_path",
                    "photo_url",
                    "source_asset_id",
                ],
                seed_rows,
            )

            html = builder.build_page(
                seed_rows=seed_rows,
                summary=builder.read_json_optional(summary_json),
                source_queue_csv=queue_csv,
                source_seed_csv=seed_csv,
            )
            output_html.write_text(html, encoding="utf-8")

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn("Mask Label Seed Pack", rendered)
            self.assertIn("Seed 1", rendered)
            self.assertIn("Iles Yellow Latvian", rendered)
            self.assertIn("./assets/v1-10-pot-cv/9t_overlay.jpg", rendered)
            self.assertIn("Queue source", rendered)
            self.assertIn("python3 scripts/build_v110_mask_seed_page.py", rendered)


if __name__ == "__main__":
    unittest.main()
