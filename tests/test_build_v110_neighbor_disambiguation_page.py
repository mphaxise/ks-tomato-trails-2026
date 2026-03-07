import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v110_neighbor_disambiguation_page as builder  # noqa: E402


class BuildV110NeighborDisambiguationPageTests(unittest.TestCase):
    def test_build_queue_rows_orders_by_severity(self):
        rows = [
            {
                "pot_id": "23T",
                "variety_name": "Heinz 9129",
                "tracking_readiness": "moderate",
                "anchor_mode": "plant",
                "focus_score": "0.62",
                "pot_coverage": "0.021",
                "neighbor_spill_ratio": "0.279",
                "spill_in_pot_ratio": "0.373",
                "next_step_code": "needs_neighbor_disambiguation",
            },
            {
                "pot_id": "8T",
                "variety_name": "Iles Yellow Latvian",
                "tracking_readiness": "low",
                "anchor_mode": "plant",
                "focus_score": "0.36",
                "pot_coverage": "0.020",
                "neighbor_spill_ratio": "0.784",
                "spill_in_pot_ratio": "0.756",
                "next_step_code": "needs_neighbor_disambiguation",
            },
            {
                "pot_id": "9T",
                "variety_name": "Iles Yellow Latvian",
                "tracking_readiness": "high",
                "anchor_mode": "plant",
                "focus_score": "0.80",
                "pot_coverage": "0.056",
                "neighbor_spill_ratio": "0.000",
                "spill_in_pot_ratio": "0.000",
                "next_step_code": "ready_for_mask_labels",
            },
        ]

        queue = builder.build_queue_rows(rows)
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["pot_id"], "8T")
        self.assertEqual(queue[0]["queue_priority_rank"], "1")
        self.assertIn("disambiguation_note", queue[0])
        self.assertNotIn("9T", [row["pot_id"] for row in queue])

    def test_build_page_outputs_expected_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_csv = tmp_path / "metrics.csv"
            summary_json = tmp_path / "summary.json"
            queue_csv = tmp_path / "queue.csv"
            output_html = tmp_path / "out.html"

            with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "pot_id",
                        "variety_name",
                        "tracking_readiness",
                        "anchor_mode",
                        "focus_score",
                        "pot_coverage",
                        "neighbor_spill_ratio",
                        "spill_in_pot_ratio",
                        "chlorosis_ratio",
                        "growth_delta",
                        "capture_date",
                        "source_asset_id",
                        "photo_url",
                        "overlay_path",
                        "crop_path",
                        "next_step_code",
                        "next_step_text",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pot_id": "8T",
                        "variety_name": "Iles Yellow Latvian",
                        "tracking_readiness": "low",
                        "anchor_mode": "plant",
                        "focus_score": "0.36",
                        "pot_coverage": "0.020",
                        "neighbor_spill_ratio": "0.784",
                        "spill_in_pot_ratio": "0.756",
                        "chlorosis_ratio": "0.03",
                        "growth_delta": "",
                        "capture_date": "2026-03-06",
                        "source_asset_id": "A8",
                        "photo_url": "https://example.com/photo.jpg",
                        "overlay_path": "assets/v1-10-pot-cv/8t_overlay.jpg",
                        "crop_path": "assets/v1-10-pot-cv/8t_crop.jpg",
                        "next_step_code": "needs_neighbor_disambiguation",
                        "next_step_text": "Confirm pot walls before attempting any canopy mask.",
                    }
                )

            summary_json.write_text(
                json.dumps({"run_date": "2026-03-06", "created_at": "2026-03-07T04:15:42Z"}),
                encoding="utf-8",
            )

            queue_rows = builder.build_queue_rows(builder.read_csv_rows(metrics_csv))
            builder.write_csv_rows(queue_csv, builder.QUEUE_FIELDNAMES, queue_rows)

            html = builder.build_page(
                queue_rows=queue_rows,
                summary=builder.read_json_optional(summary_json),
                source_metrics_csv=metrics_csv,
                source_queue_csv=queue_csv,
            )
            output_html.write_text(html, encoding="utf-8")

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn("Neighbor Disambiguation Queue", rendered)
            self.assertIn("Queue 1", rendered)
            self.assertIn("Iles Yellow Latvian", rendered)
            self.assertIn("./assets/v1-10-pot-cv/8t_overlay.jpg", rendered)
            self.assertIn("./single-photo-seed-labeler.html?", rendered)
            self.assertIn("Annotate Crop", rendered)
            self.assertIn("Metrics source", rendered)
            self.assertIn("python3 scripts/build_v110_neighbor_disambiguation_page.py", rendered)


if __name__ == "__main__":
    unittest.main()
