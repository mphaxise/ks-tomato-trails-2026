import csv
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v14_cv_research_pipeline as pipeline  # noqa: E402


class V14CvResearchPipelineTests(unittest.TestCase):
    def test_estimate_plant_count_does_not_exceed_components(self):
        self.assertEqual(
            pipeline.estimate_plant_count(
                canopy_components=1,
                vegetation_coverage=0.058,
                largest_component_ratio=0.07,
            ),
            1,
        )
        self.assertEqual(
            pipeline.estimate_plant_count(
                canopy_components=6,
                vegetation_coverage=0.062,
                largest_component_ratio=0.03,
            ),
            3,
        )

    def test_build_baseline_lookup_picks_earliest_tomato_row(self):
        rows = [
            {
                "classification_label": "tomato",
                "caption": "Taxi | tomato_5 | verified",
                "source_asset_id": "late_asset",
                "capture_date": "2026-02-27",
            },
            {
                "classification_label": "tomato",
                "caption": "Taxi | tomato_5 | verified",
                "source_asset_id": "early_asset",
                "capture_date": "2026-02-25",
            },
            {
                "classification_label": "non_tomato",
                "caption": "Spinach | non_tomato_2 | verified",
                "source_asset_id": "ignored_asset",
                "capture_date": "2026-02-25",
            },
        ]
        lookup = pipeline.build_baseline_lookup(rows)
        self.assertIn(5, lookup)
        self.assertEqual(lookup[5].source_asset_id, "early_asset")

    def test_compute_cv_metrics_detects_green_signal(self):
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(image, (30, 30), (160, 170), (40, 180, 40), thickness=-1)
        metrics = pipeline.compute_cv_metrics(image)
        self.assertGreater(metrics["vegetation_coverage"], 0.30)
        self.assertGreaterEqual(metrics["canopy_components"], 1)
        self.assertGreaterEqual(metrics["plant_count_estimate"], 1)

    def test_run_pipeline_creates_isolated_outputs_and_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            images_dir = tmp_path / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            baseline_image = np.zeros((180, 180, 3), dtype=np.uint8)
            cv2.rectangle(baseline_image, (70, 70), (115, 120), (40, 180, 40), thickness=-1)
            latest_image = np.zeros((180, 180, 3), dtype=np.uint8)
            cv2.rectangle(latest_image, (40, 40), (150, 155), (40, 180, 40), thickness=-1)

            baseline_asset = "BASE_ASSET_1"
            latest_asset = "LATEST_ASSET_1"
            baseline_path = images_dir / f"13_{baseline_asset}.jpg"
            latest_path = images_dir / f"27_{latest_asset}.jpg"
            cv2.imwrite(str(baseline_path), baseline_image)
            cv2.imwrite(str(latest_path), latest_image)

            mapping_csv = tmp_path / "mapping.csv"
            with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "classification_label",
                        "pot_id",
                        "source_asset_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-02-27",
                        "classification_label": "tomato",
                        "pot_id": "1T",
                        "source_asset_id": latest_asset,
                    }
                )

            labeled_csv = tmp_path / "labeled.csv"
            with labeled_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "classification_label",
                        "caption",
                        "source_asset_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-02-25",
                        "classification_label": "tomato",
                        "caption": "Taxi | tomato_1 | verified",
                        "source_asset_id": baseline_asset,
                    }
                )

            db_path = tmp_path / "local" / "cv_research.db"
            output_dir = tmp_path / "out"
            report_path = tmp_path / "docs" / "report.md"

            result = pipeline.run_pipeline(
                mapping_csv=mapping_csv,
                labeled_csv=labeled_csv,
                images_dir=images_dir,
                db_path=db_path,
                output_dir=output_dir,
                report_path=report_path,
                run_id="unit_test_run",
            )

            self.assertEqual(result["analyzed_rows"], 1)
            self.assertTrue((output_dir / "cv_experiment_results.csv").exists())
            self.assertTrue((output_dir / "research_summary.json").exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(db_path.exists())

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT growth_delta, health_score, survival_hypothesis "
                    "FROM image_metrics WHERE run_id = ?",
                    ("unit_test_run",),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertIsNotNone(row[0])
            self.assertGreater(float(row[1]), 0.0)
            self.assertIn(row[2], {"high", "moderate", "low"})

    def test_run_pipeline_only_processes_latest_capture_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            images_dir = tmp_path / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            image_old = np.zeros((140, 140, 3), dtype=np.uint8)
            cv2.rectangle(image_old, (40, 40), (95, 95), (40, 180, 40), thickness=-1)
            image_new = np.zeros((140, 140, 3), dtype=np.uint8)
            cv2.rectangle(image_new, (30, 30), (110, 110), (40, 180, 40), thickness=-1)

            old_asset = "OLD_ASSET_1"
            new_asset = "NEW_ASSET_1"
            cv2.imwrite(str(images_dir / f"20_{old_asset}.jpg"), image_old)
            cv2.imwrite(str(images_dir / f"21_{new_asset}.jpg"), image_new)

            mapping_csv = tmp_path / "mapping.csv"
            with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "classification_label",
                        "pot_id",
                        "source_asset_id",
                        "variety_name",
                        "photo_url",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-02-26",
                        "classification_label": "tomato",
                        "pot_id": "1T",
                        "source_asset_id": old_asset,
                        "variety_name": "Old Row",
                        "photo_url": "https://example.com/old.jpg",
                    }
                )
                writer.writerow(
                    {
                        "capture_date": "2026-02-27",
                        "classification_label": "tomato",
                        "pot_id": "2T",
                        "source_asset_id": new_asset,
                        "variety_name": "New Row",
                        "photo_url": "https://example.com/new.jpg",
                    }
                )

            labeled_csv = tmp_path / "labeled.csv"
            with labeled_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "classification_label",
                        "caption",
                        "source_asset_id",
                    ],
                )
                writer.writeheader()

            db_path = tmp_path / "local" / "cv_research.db"
            output_dir = tmp_path / "out"
            report_path = tmp_path / "docs" / "report.md"

            result = pipeline.run_pipeline(
                mapping_csv=mapping_csv,
                labeled_csv=labeled_csv,
                images_dir=images_dir,
                db_path=db_path,
                output_dir=output_dir,
                report_path=report_path,
                run_id="run_latest_only",
            )

            self.assertEqual(result["run_date"], "2026-02-27")
            self.assertEqual(result["total_mapping_rows"], 1)
            self.assertEqual(result["analyzed_rows"], 1)

            with (output_dir / "cv_experiment_results.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                output_rows = list(csv.DictReader(handle))
            self.assertEqual(len(output_rows), 1)
            self.assertEqual(output_rows[0]["capture_date"], "2026-02-27")
            self.assertEqual(output_rows[0]["pot_id"], "2T")


if __name__ == "__main__":
    unittest.main()
