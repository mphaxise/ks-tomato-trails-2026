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

import v110_pot_cv_experiment as experiment  # noqa: E402


def draw_test_scene(path: Path, plant_scale: int = 1) -> None:
    image = np.full((480, 360, 3), 110, dtype=np.uint8)
    cv2.rectangle(image, (60, 170), (300, 350), (190, 175, 145), thickness=-1)
    cv2.rectangle(image, (80, 165), (280, 180), (170, 158, 132), thickness=-1)
    cv2.rectangle(image, (145, 70), (200, 215), (245, 245, 240), thickness=-1)
    cv2.putText(image, "2T", (150, 155), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 3)
    cv2.rectangle(image, (262, 110), (315, 255), (245, 245, 240), thickness=-1)
    cv2.putText(image, "5", (274, 208), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 3)
    cv2.rectangle(image, (250, 165), (360, 345), (185, 170, 140), thickness=-1)

    plant_color = (45, 170, 45)
    leaf_offset = 18 * plant_scale
    cv2.rectangle(image, (174, 140), (182, 245), plant_color, thickness=-1)
    cv2.ellipse(image, (150, 150), (40 + leaf_offset, 18 + leaf_offset // 2), 10, 0, 360, plant_color, thickness=-1)
    cv2.ellipse(image, (205, 155), (36 + leaf_offset, 16 + leaf_offset // 2), -12, 0, 360, plant_color, thickness=-1)
    cv2.ellipse(image, (156, 195), (34 + leaf_offset, 14 + leaf_offset // 2), 20, 0, 360, plant_color, thickness=-1)
    cv2.ellipse(image, (210, 205), (32 + leaf_offset, 14 + leaf_offset // 2), -18, 0, 360, plant_color, thickness=-1)
    cv2.ellipse(image, (270, 235), (24, 14), 0, 0, 360, plant_color, thickness=-1)

    cv2.imwrite(str(path), image)


class V110PotCvExperimentTests(unittest.TestCase):
    def test_detect_primary_canopy_picks_center_biased_component(self):
        image = np.zeros((240, 240, 3), dtype=np.uint8)
        cv2.rectangle(image, (20, 80), (70, 125), (40, 180, 40), thickness=-1)
        cv2.rectangle(image, (90, 100), (165, 170), (40, 180, 40), thickness=-1)
        mask = experiment.compute_vegetation_mask(image)
        canopy = experiment.detect_primary_canopy(image, mask)
        self.assertIsNotNone(canopy)
        self.assertGreater(canopy["cx"], 100.0)
        self.assertGreater(canopy["confidence"], 0.3)

    def test_compute_pot_metrics_returns_focus_and_spill(self):
        image = np.full((360, 280, 3), 110, dtype=np.uint8)
        cv2.rectangle(image, (60, 120), (220, 280), (190, 175, 145), thickness=-1)
        cv2.rectangle(image, (95, 55), (135, 180), (245, 245, 240), thickness=-1)
        cv2.putText(image, "1T", (98, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 3)
        cv2.rectangle(image, (120, 115), (128, 205), (40, 180, 40), thickness=-1)
        cv2.ellipse(image, (105, 120), (30, 16), 0, 0, 360, (40, 180, 40), thickness=-1)
        cv2.ellipse(image, (145, 130), (26, 15), 0, 0, 360, (40, 180, 40), thickness=-1)
        cv2.ellipse(image, (205, 180), (22, 12), 0, 0, 360, (40, 180, 40), thickness=-1)

        metrics = experiment.compute_pot_metrics(image)
        self.assertIn(metrics["anchor_mode"], {"plant", "label", "fallback"})
        self.assertGreater(metrics["pot_coverage"], 0.01)
        self.assertGreaterEqual(metrics["neighbor_spill_ratio"], 0.0)
        self.assertLessEqual(metrics["neighbor_spill_ratio"], 1.0)
        self.assertGreater(metrics["focus_score"], 0.0)

    def test_run_pipeline_creates_outputs_assets_and_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            images_dir = tmp_path / "images"
            output_dir = tmp_path / "out"
            assets_dir = tmp_path / "tracker" / "assets" / "v1-10-pot-cv"
            images_dir.mkdir(parents=True, exist_ok=True)

            baseline_asset = "BASE_ASSET_2"
            latest_asset = "LATEST_ASSET_2"
            draw_test_scene(images_dir / f"01_{baseline_asset}.jpg", plant_scale=0)
            draw_test_scene(images_dir / f"02_{latest_asset}.jpg", plant_scale=1)

            mapping_csv = tmp_path / "mapping.csv"
            with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "captured_at",
                        "pot_id",
                        "source_asset_id",
                        "variety_name",
                        "photo_url",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-03-06",
                        "captured_at": "2026-03-06T09:16:10-08:00",
                        "pot_id": "2T",
                        "source_asset_id": latest_asset,
                        "variety_name": "Taxi",
                        "photo_url": "https://example.com/latest.jpg",
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
                        "caption": "Taxi | tomato_2 | verified",
                        "source_asset_id": baseline_asset,
                    }
                )

            db_path = tmp_path / "local" / "v1_10.db"
            report_path = tmp_path / "docs" / "report.md"

            result = experiment.run_pipeline(
                mapping_csv=mapping_csv,
                labeled_csv=labeled_csv,
                images_dir=images_dir,
                db_path=db_path,
                output_dir=output_dir,
                assets_dir=assets_dir,
                report_path=report_path,
                run_id="unit_test_v1_10",
            )

            self.assertEqual(result["pots_analyzed"], 1)
            self.assertTrue((output_dir / "pot_cv_metrics.csv").exists())
            self.assertTrue((output_dir / "pot_cv_recommendations.csv").exists())
            self.assertTrue((output_dir / "algorithm_assessment.csv").exists())
            self.assertTrue((output_dir / "pot_cv_summary.json").exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(db_path.exists())
            self.assertTrue(any(assets_dir.glob("*_overlay.jpg")))
            self.assertTrue(any(assets_dir.glob("*_crop.jpg")))

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT pot_coverage, focus_score, tracking_readiness, next_step_code "
                    "FROM pot_metrics WHERE run_id = ?",
                    ("unit_test_v1_10",),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertGreater(float(row[0]), 0.0)
            self.assertGreater(float(row[1]), 0.0)
            self.assertIn(row[2], {"high", "moderate", "low"})
            self.assertTrue(row[3])


if __name__ == "__main__":
    unittest.main()
