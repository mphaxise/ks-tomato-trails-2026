import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v110_seed_annotation_status_page as builder  # noqa: E402


class BuildV110SeedAnnotationStatusPageTests(unittest.TestCase):
    def test_build_page_outputs_expected_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_csv = tmp_path / "manifest.csv"
            summary_json = tmp_path / "summary.json"
            output_html = tmp_path / "out.html"

            with manifest_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "task_key",
                        "pot_id",
                        "variety_name",
                        "seed_rank",
                        "queue_priority_rank",
                        "source_asset_id",
                        "annotation_status",
                        "export_count",
                        "latest_export_json_path",
                        "latest_saved_at_utc",
                        "reviewer",
                        "box_count",
                        "labels_present",
                        "image_src",
                        "crop_path",
                        "overlay_path",
                        "annotate_url",
                        "reference_url",
                        "next_action",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "task_key": "v110_seed_1_9t_asset_aaa111",
                        "pot_id": "9T",
                        "variety_name": "Iles Yellow Latvian",
                        "seed_rank": "1",
                        "queue_priority_rank": "1",
                        "source_asset_id": "ASSET_AAA111",
                        "annotation_status": "pending",
                        "export_count": "0",
                        "latest_export_json_path": "",
                        "latest_saved_at_utc": "",
                        "reviewer": "",
                        "box_count": "0",
                        "labels_present": "",
                        "image_src": "./assets/v1-10-pot-cv/9t_crop.jpg",
                        "crop_path": "./assets/v1-10-pot-cv/9t_crop.jpg",
                        "overlay_path": "./assets/v1-10-pot-cv/9t_overlay.jpg",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_1_9t_asset_aaa111",
                        "reference_url": "https://example.com/9.jpg",
                        "next_action": "Open the seed pack and start the first annotation pass for this crop.",
                    }
                )
                writer.writerow(
                    {
                        "task_key": "v110_seed_2_28t_asset_bbb222",
                        "pot_id": "28T",
                        "variety_name": "Nikolayev Yellow Cherry",
                        "seed_rank": "2",
                        "queue_priority_rank": "2",
                        "source_asset_id": "ASSET_BBB222",
                        "annotation_status": "completed",
                        "export_count": "1",
                        "latest_export_json_path": "data/research/v1_10/labeler_exports/seed_28t.json",
                        "latest_saved_at_utc": "2026-03-07T05:00:00+00:00",
                        "reviewer": "pk",
                        "box_count": "3",
                        "labels_present": "plant_region|pot_region",
                        "image_src": "./assets/v1-10-pot-cv/28t_crop.jpg",
                        "crop_path": "./assets/v1-10-pot-cv/28t_crop.jpg",
                        "overlay_path": "./assets/v1-10-pot-cv/28t_overlay.jpg",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_2_28t_asset_bbb222",
                        "reference_url": "https://example.com/28.jpg",
                        "next_action": "Review the latest export and decide whether this task is ready for polygon mask follow-up.",
                    }
                )

            summary_json.write_text(
                json.dumps(
                    {
                        "generated_at_utc": "2026-03-07T06:12:00+00:00",
                        "expected_tasks": 2,
                        "completed_tasks": 1,
                        "started_empty_tasks": 0,
                        "pending_tasks": 1,
                        "unassigned_export_files": [],
                    }
                ),
                encoding="utf-8",
            )

            html = builder.build_page(
                manifest_rows=builder.read_csv_rows(manifest_csv),
                summary=builder.read_json_optional(summary_json),
                source_manifest_csv=manifest_csv,
                source_summary_json=summary_json,
            )
            output_html.write_text(html, encoding="utf-8")

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn("Seed Annotation Status", rendered)
            self.assertIn("Pending (1)", rendered)
            self.assertIn("Completed (1)", rendered)
            self.assertIn("Annotate Crop", rendered)
            self.assertIn("./assets/v1-10-pot-cv/9t_crop.jpg", rendered)
            self.assertIn("python3 scripts/build_v110_seed_annotation_status_page.py", rendered)


if __name__ == "__main__":
    unittest.main()
