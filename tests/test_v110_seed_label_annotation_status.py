import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v110_seed_label_annotation_status as status  # noqa: E402


class V110SeedLabelAnnotationStatusTests(unittest.TestCase):
    def test_main_builds_manifest_with_completed_and_pending_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            seed_csv = tmp_path / "mask_label_seed_set.csv"
            exports_dir = tmp_path / "exports"
            output_csv = tmp_path / "manifest.csv"
            output_json = tmp_path / "summary.json"
            output_md = tmp_path / "status.md"
            exports_dir.mkdir(parents=True, exist_ok=True)

            with seed_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "seed_rank",
                        "queue_priority_rank",
                        "pot_id",
                        "variety_name",
                        "source_asset_id",
                        "photo_url",
                        "overlay_path",
                        "crop_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "seed_rank": "1",
                        "queue_priority_rank": "1",
                        "pot_id": "9T",
                        "variety_name": "Iles Yellow Latvian",
                        "source_asset_id": "ASSET_AAA111",
                        "photo_url": "https://example.com/9.jpg",
                        "overlay_path": "assets/v1-10-pot-cv/9t_overlay.jpg",
                        "crop_path": "assets/v1-10-pot-cv/9t_crop.jpg",
                    }
                )
                writer.writerow(
                    {
                        "seed_rank": "2",
                        "queue_priority_rank": "2",
                        "pot_id": "28T",
                        "variety_name": "Nikolayev Yellow Cherry",
                        "source_asset_id": "ASSET_BBB222",
                        "photo_url": "https://example.com/28.jpg",
                        "overlay_path": "assets/v1-10-pot-cv/28t_overlay.jpg",
                        "crop_path": "assets/v1-10-pot-cv/28t_crop.jpg",
                    }
                )

            export_payload = {
                "version": "single-photo-seed-fabric-v1",
                "saved_at_utc": "2026-03-07T05:00:00+00:00",
                "task_key": "v110_seed_1_9t_asset_aaa111",
                "task_metadata": {
                    "pot_id": "9T",
                    "variety": "Iles Yellow Latvian",
                    "seed_rank": "1",
                    "queue_rank": "1",
                    "source_asset_id": "ASSET_AAA111",
                    "reference_url": "https://example.com/9.jpg",
                },
                "pot_identity": {
                    "expected_pot_id": "9T",
                    "verdict": "reject_prefilled",
                    "corrected_pot_id": "28T",
                    "effective_pot_id": "28T",
                    "note": "Tag position matches 28T, not 9T.",
                },
                "image_src": "./assets/v1-10-pot-cv/9t_crop.jpg",
                "reviewer": "pk",
                "boxes": [
                    {"id": 1, "label": "pot_region"},
                    {"id": 2, "label": "plant_region"},
                ],
            }
            (exports_dir / "seed_9t.json").write_text(json.dumps(export_payload), encoding="utf-8")
            (exports_dir / "unassigned.json").write_text(json.dumps({"hello": "world"}), encoding="utf-8")

            rc = status.main(
                [
                    "--seed-csv",
                    str(seed_csv),
                    "--exports-dir",
                    str(exports_dir),
                    "--output-csv",
                    str(output_csv),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output_csv.exists())
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())

            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            by_pot = {row["pot_id"]: row for row in rows}
            self.assertEqual(by_pot["9T"]["annotation_status"], "completed")
            self.assertEqual(by_pot["9T"]["reviewer"], "pk")
            self.assertEqual(by_pot["9T"]["box_count"], "2")
            self.assertEqual(by_pot["9T"]["crop_path"], "./assets/v1-10-pot-cv/9t_crop.jpg")
            self.assertIn("single-photo-seed-labeler.html?", by_pot["9T"]["annotate_url"])
            self.assertEqual(by_pot["9T"]["pot_id_verdict"], "reject_prefilled")
            self.assertEqual(by_pot["9T"]["corrected_pot_id"], "28T")
            self.assertEqual(by_pot["9T"]["effective_pot_id"], "28T")
            self.assertEqual(by_pot["9T"]["pot_id_mismatch"], "yes")
            self.assertIn("Resolve the pot-ID mismatch", by_pot["9T"]["next_action"])
            self.assertEqual(by_pot["28T"]["annotation_status"], "pending")
            self.assertEqual(by_pot["28T"]["image_src"], "./assets/v1-10-pot-cv/28t_crop.jpg")

            summary = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["expected_tasks"], 2)
            self.assertEqual(summary["completed_tasks"], 1)
            self.assertEqual(summary["pending_tasks"], 1)
            self.assertEqual(summary["pot_id_mismatch_tasks"], 1)
            self.assertEqual(summary["pot_id_mismatches"][0]["corrected_pot_id"], "28T")
            self.assertEqual(len(summary["unassigned_export_files"]), 1)
            self.assertIn("pot_region", summary["labels_present_counts"])
            self.assertIn("Seed Annotation Status", output_md.read_text(encoding="utf-8"))
            self.assertIn("tracker/v1-10-seed-annotation-status.html", output_md.read_text(encoding="utf-8"))
            self.assertIn("Pot-ID Mismatches", output_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
