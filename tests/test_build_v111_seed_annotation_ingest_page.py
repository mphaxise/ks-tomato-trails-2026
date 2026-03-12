import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v111_seed_annotation_ingest_page as builder  # noqa: E402


class BuildV111SeedAnnotationIngestPageTests(unittest.TestCase):
    def test_build_page_outputs_training_ready_and_pending_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_csv = tmp_path / "task_manifest.csv"
            summary_json = tmp_path / "summary.json"

            with task_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "task_key",
                        "pot_id",
                        "variety_name",
                        "seed_rank",
                        "queue_priority_rank",
                        "annotation_status",
                        "ingest_status",
                        "reviewer",
                        "image_page_path",
                        "crop_path",
                        "overlay_path",
                        "annotate_url",
                        "reference_url",
                        "box_count",
                        "labels_present",
                        "required_labels_missing",
                        "yolo_label_path",
                        "yolo_box_count",
                        "ready_for_training",
                        "expected_pot_id",
                        "effective_pot_id",
                        "next_step",
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
                        "annotation_status": "completed",
                        "ingest_status": "ready_for_training",
                        "reviewer": "pk",
                        "image_page_path": "./assets/v1-10-pot-cv/9t_crop.jpg",
                        "crop_path": "./assets/v1-10-pot-cv/9t_crop.jpg",
                        "overlay_path": "./assets/v1-10-pot-cv/9t_overlay.jpg",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_1_9t_asset_aaa111",
                        "reference_url": "https://example.com/9.jpg",
                        "box_count": "3",
                        "labels_present": "plant_region|pot_interior|pot_region",
                        "required_labels_missing": "",
                        "yolo_label_path": "data/research/v1_11/yolo_labels/v110_seed_1_9t_asset_aaa111.txt",
                        "yolo_box_count": "3",
                        "ready_for_training": "yes",
                        "expected_pot_id": "9T",
                        "effective_pot_id": "9T",
                        "next_step": "Use this task in the first indoor pot/plant detector baseline.",
                    }
                )
                writer.writerow(
                    {
                        "task_key": "v110_seed_2_28t_asset_bbb222",
                        "pot_id": "28T",
                        "variety_name": "Nikolayev Yellow Cherry",
                        "seed_rank": "2",
                        "queue_priority_rank": "2",
                        "annotation_status": "pending",
                        "ingest_status": "pending_annotation",
                        "reviewer": "",
                        "image_page_path": "./assets/v1-10-pot-cv/28t_crop.jpg",
                        "crop_path": "./assets/v1-10-pot-cv/28t_crop.jpg",
                        "overlay_path": "./assets/v1-10-pot-cv/28t_overlay.jpg",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_2_28t_asset_bbb222",
                        "reference_url": "https://example.com/28.jpg",
                        "box_count": "0",
                        "labels_present": "",
                        "required_labels_missing": "pot_region|pot_interior|plant_region",
                        "yolo_label_path": "",
                        "yolo_box_count": "0",
                        "ready_for_training": "",
                        "expected_pot_id": "28T",
                        "effective_pot_id": "28T",
                        "next_step": "Open the task in the seed labeler and complete the first annotation pass.",
                    }
                )

            summary_json.write_text(
                json.dumps(
                    {
                        "generated_at_utc": "2026-03-07T18:20:00+00:00",
                        "total_tasks": 2,
                        "completed_annotation_tasks": 1,
                        "ready_for_training_tasks": 1,
                        "pending_annotation_tasks": 1,
                        "missing_required_label_tasks": 0,
                        "pot_id_mismatch_tasks": 0,
                        "total_boxes_ingested": 3,
                        "required_label_task_counts": {
                            "pot_region": 1,
                            "pot_interior": 1,
                            "plant_region": 1,
                        },
                        "recommended_next_step": "Benchmark the first indoor detector baseline.",
                    }
                ),
                encoding="utf-8",
            )

            html = builder.build_page(
                task_rows=builder.read_csv_rows(task_csv),
                summary=builder.read_json_optional(summary_json),
                source_task_csv=task_csv,
                source_summary_json=summary_json,
            )

            self.assertIn("V1.11 Seed Annotation Ingest", html)
            self.assertIn("Ready For Training (1)", html)
            self.assertIn("Pending Annotation (1)", html)
            self.assertIn("v110_seed_1_9t_asset_aaa111.txt", html)
            self.assertIn("python3 scripts/v111_seed_annotation_ingest.py", html)
            self.assertIn("python3 scripts/build_v111_seed_annotation_ingest_page.py", html)


if __name__ == "__main__":
    unittest.main()
