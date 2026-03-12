import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v111_seed_annotation_ingest as ingest  # noqa: E402


class V111SeedAnnotationIngestTests(unittest.TestCase):
    def test_main_builds_training_ready_and_blocked_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            status_manifest = tmp_path / "status_manifest.csv"
            export_dir = tmp_path / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            ready_image = image_dir / "9t_crop.jpg"
            ready_image.write_bytes(b"jpg")
            missing_label_image = image_dir / "28t_crop.jpg"
            missing_label_image.write_bytes(b"jpg")

            ready_export = export_dir / "9t.json"
            ready_export.write_text(
                json.dumps(
                    {
                        "image_width": 1000,
                        "image_height": 800,
                        "reviewer": "pk",
                        "boxes": [
                            {
                                "id": 1,
                                "label": "pot_region",
                                "x": 50,
                                "y": 40,
                                "w": 500,
                                "h": 560,
                            },
                            {
                                "id": 2,
                                "label": "pot_interior",
                                "x": 80,
                                "y": 90,
                                "w": 420,
                                "h": 470,
                            },
                            {
                                "id": 3,
                                "label": "plant_region",
                                "x_norm": 0.21,
                                "y_norm": 0.18,
                                "w_norm": 0.18,
                                "h_norm": 0.22,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            missing_label_export = export_dir / "28t.json"
            missing_label_export.write_text(
                json.dumps(
                    {
                        "image_width": 1000,
                        "image_height": 800,
                        "reviewer": "pk",
                        "boxes": [
                            {"id": 1, "label": "pot_region", "x_norm": 0.10, "y_norm": 0.10, "w_norm": 0.40, "h_norm": 0.50},
                            {"id": 2, "label": "plant_region", "x_norm": 0.20, "y_norm": 0.18, "w_norm": 0.16, "h_norm": 0.21},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with status_manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "task_key",
                        "pot_id",
                        "variety_name",
                        "seed_rank",
                        "queue_priority_rank",
                        "annotation_status",
                        "latest_export_json_path",
                        "reviewer",
                        "crop_path",
                        "overlay_path",
                        "annotate_url",
                        "reference_url",
                        "expected_pot_id",
                        "effective_pot_id",
                        "pot_id_verdict",
                        "pot_id_mismatch",
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
                        "latest_export_json_path": str(ready_export),
                        "reviewer": "pk",
                        "crop_path": str(ready_image),
                        "overlay_path": "",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_1_9t_asset_aaa111",
                        "reference_url": "https://example.com/9.jpg",
                        "expected_pot_id": "9T",
                        "effective_pot_id": "9T",
                        "pot_id_verdict": "accept_prefilled",
                        "pot_id_mismatch": "",
                    }
                )
                writer.writerow(
                    {
                        "task_key": "v110_seed_2_28t_asset_bbb222",
                        "pot_id": "28T",
                        "variety_name": "Nikolayev Yellow Cherry",
                        "seed_rank": "2",
                        "queue_priority_rank": "2",
                        "annotation_status": "completed",
                        "latest_export_json_path": str(missing_label_export),
                        "reviewer": "pk",
                        "crop_path": str(missing_label_image),
                        "overlay_path": "",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_2_28t_asset_bbb222",
                        "reference_url": "https://example.com/28.jpg",
                        "expected_pot_id": "28T",
                        "effective_pot_id": "28T",
                        "pot_id_verdict": "accept_prefilled",
                        "pot_id_mismatch": "",
                    }
                )
                writer.writerow(
                    {
                        "task_key": "v110_seed_3_5t_asset_ccc333",
                        "pot_id": "5T",
                        "variety_name": "San Francisco Fog",
                        "seed_rank": "3",
                        "queue_priority_rank": "4",
                        "annotation_status": "pending",
                        "latest_export_json_path": "",
                        "reviewer": "",
                        "crop_path": str(image_dir / "5t_crop.jpg"),
                        "overlay_path": "",
                        "annotate_url": "./single-photo-seed-labeler.html?task_key=v110_seed_3_5t_asset_ccc333",
                        "reference_url": "https://example.com/5.jpg",
                        "expected_pot_id": "5T",
                        "effective_pot_id": "5T",
                        "pot_id_verdict": "",
                        "pot_id_mismatch": "",
                    }
                )

            output_task_csv = tmp_path / "task_ingest.csv"
            output_box_csv = tmp_path / "box_rows.csv"
            output_summary_json = tmp_path / "summary.json"
            output_md = tmp_path / "summary.md"
            output_yolo_dir = tmp_path / "yolo_labels"

            rc = ingest.main(
                [
                    "--status-manifest-csv",
                    str(status_manifest),
                    "--output-task-csv",
                    str(output_task_csv),
                    "--output-box-csv",
                    str(output_box_csv),
                    "--output-summary-json",
                    str(output_summary_json),
                    "--output-md",
                    str(output_md),
                    "--output-yolo-dir",
                    str(output_yolo_dir),
                ]
            )
            self.assertEqual(rc, 0)

            with output_task_csv.open("r", encoding="utf-8", newline="") as handle:
                task_rows = list(csv.DictReader(handle))
            self.assertEqual(len(task_rows), 3)
            by_pot = {row["pot_id"]: row for row in task_rows}
            self.assertEqual(by_pot["9T"]["ingest_status"], "ready_for_training")
            self.assertEqual(by_pot["9T"]["ready_for_training"], "yes")
            self.assertTrue(by_pot["9T"]["yolo_label_path"].endswith("v110_seed_1_9t_asset_aaa111.txt"))
            self.assertEqual(by_pot["9T"]["yolo_box_count"], "3")
            self.assertEqual(by_pot["28T"]["ingest_status"], "missing_required_labels")
            self.assertEqual(by_pot["28T"]["required_labels_missing"], "pot_interior")
            self.assertEqual(by_pot["5T"]["ingest_status"], "pending_annotation")

            with output_box_csv.open("r", encoding="utf-8", newline="") as handle:
                box_rows = list(csv.DictReader(handle))
            self.assertEqual(len(box_rows), 5)
            self.assertTrue(any(row["label"] == "pot_interior" for row in box_rows))

            summary = json.loads(output_summary_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["total_tasks"], 3)
            self.assertEqual(summary["ready_for_training_tasks"], 1)
            self.assertEqual(summary["missing_required_label_tasks"], 1)
            self.assertEqual(summary["pending_annotation_tasks"], 1)
            self.assertEqual(summary["total_boxes_ingested"], 5)
            self.assertEqual(summary["required_label_task_counts"]["pot_region"], 2)
            self.assertIn("Finish the first clean indoor seed annotations", summary["recommended_next_step"])

            yolo_file = output_yolo_dir / "v110_seed_1_9t_asset_aaa111.txt"
            self.assertTrue(yolo_file.exists())
            yolo_lines = yolo_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(yolo_lines), 3)
            self.assertTrue(yolo_lines[0].startswith("0 "))

            rendered_md = output_md.read_text(encoding="utf-8")
            self.assertIn("V1.11 Seed Annotation Ingest", rendered_md)
            self.assertIn("PlantCV", rendered_md)
            self.assertIn("AgML", rendered_md)


if __name__ == "__main__":
    unittest.main()
