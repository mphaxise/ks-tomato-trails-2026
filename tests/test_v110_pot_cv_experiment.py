import csv
import json
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

    def test_build_owned_canopy_mask_excludes_distant_neighbor(self):
        image = np.zeros((260, 260, 3), dtype=np.uint8)
        cv2.rectangle(image, (85, 105), (140, 160), (40, 180, 40), thickness=-1)
        cv2.rectangle(image, (175, 115), (225, 170), (40, 180, 40), thickness=-1)
        vegetation_mask = experiment.compute_vegetation_mask(image)
        primary = experiment.detect_primary_canopy(image, vegetation_mask)
        pot_polygon = np.array([[60, 120], [170, 120], [182, 228], [48, 228]], dtype=np.int32)
        pot_mask = experiment.polygon_mask((260, 260), pot_polygon)
        expanded_mask = experiment.polygon_mask((260, 260), experiment.expand_polygon(pot_polygon, image.shape))
        owned = experiment.build_owned_canopy_mask(vegetation_mask, primary, pot_mask, expanded_mask)

        self.assertGreater(np.count_nonzero(owned[:, :170]), 0)
        self.assertEqual(int(np.count_nonzero(owned[:, 180:])), 0)

    def test_compute_chlorosis_ratio_separates_green_from_yellow(self):
        mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.rectangle(mask, (20, 20), (100, 100), 255, thickness=-1)

        green_image = np.zeros((120, 120, 3), dtype=np.uint8)
        green_image[:] = (40, 170, 40)
        yellow_image = np.zeros((120, 120, 3), dtype=np.uint8)
        yellow_image[:] = (50, 145, 150)

        green_ratio = experiment.compute_chlorosis_ratio(green_image, mask)
        yellow_ratio = experiment.compute_chlorosis_ratio(yellow_image, mask)
        self.assertLess(green_ratio, 0.10)
        self.assertGreater(yellow_ratio, 0.45)

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
        self.assertLess(metrics["chlorosis_ratio"], 0.35)

    def test_build_mask_label_queue_prioritizes_clean_high_readiness_rows(self):
        queue = experiment.build_mask_label_queue(
            [
                {
                    "pot_id": "7T",
                    "variety_name": "Taxi",
                    "tracking_readiness": "moderate",
                    "focus_score": 0.62,
                    "pot_coverage": 0.024,
                    "spill_in_pot_ratio": 0.18,
                    "neighbor_spill_ratio": 0.22,
                    "chlorosis_ratio": 0.05,
                    "growth_delta": "",
                    "capture_date": "2026-03-06",
                    "source_asset_id": "A7",
                    "photo_url": "https://example.com/7.jpg",
                    "overlay_path": "assets/v1-10-pot-cv/7_overlay.jpg",
                    "crop_path": "assets/v1-10-pot-cv/7_crop.jpg",
                    "next_step_code": "ready_for_mask_labels",
                },
                {
                    "pot_id": "4T",
                    "variety_name": "Taxi",
                    "tracking_readiness": "high",
                    "focus_score": 0.74,
                    "pot_coverage": 0.028,
                    "spill_in_pot_ratio": 0.09,
                    "neighbor_spill_ratio": 0.11,
                    "chlorosis_ratio": 0.03,
                    "growth_delta": 0.17,
                    "capture_date": "2026-03-06",
                    "source_asset_id": "A4",
                    "photo_url": "https://example.com/4.jpg",
                    "overlay_path": "assets/v1-10-pot-cv/4_overlay.jpg",
                    "crop_path": "assets/v1-10-pot-cv/4_crop.jpg",
                    "next_step_code": "ready_for_mask_labels",
                },
                {
                    "pot_id": "12T",
                    "variety_name": "Taxi",
                    "tracking_readiness": "high",
                    "focus_score": 0.81,
                    "pot_coverage": 0.031,
                    "spill_in_pot_ratio": 0.04,
                    "neighbor_spill_ratio": 0.07,
                    "chlorosis_ratio": 0.02,
                    "growth_delta": 0.21,
                    "capture_date": "2026-03-06",
                    "source_asset_id": "A12",
                    "photo_url": "https://example.com/12.jpg",
                    "overlay_path": "assets/v1-10-pot-cv/12_overlay.jpg",
                    "crop_path": "assets/v1-10-pot-cv/12_crop.jpg",
                    "next_step_code": "inspect_leaf_health",
                },
            ]
        )

        self.assertEqual([row["pot_id"] for row in queue], ["4T", "7T"])
        self.assertEqual(queue[0]["priority_rank"], 1)
        self.assertIn("starter mask", queue[0]["labeling_note"].lower())

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
            self.assertTrue((output_dir / "mask_label_queue.csv").exists())
            self.assertTrue((output_dir / "algorithm_assessment.csv").exists())
            self.assertTrue((output_dir / "pot_cv_summary.json").exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(db_path.exists())
            self.assertTrue(any(assets_dir.glob("*_overlay.jpg")))
            self.assertTrue(any(assets_dir.glob("*_crop.jpg")))

            summary = json.loads((output_dir / "pot_cv_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["mask_label_queue_path"], str(output_dir / "mask_label_queue.csv"))
            self.assertEqual(summary["mask_label_seed_set_path"], str(output_dir / "mask_label_seed_set.csv"))
            self.assertEqual(summary["mask_label_seed_page"], "tracker/v1-10-mask-label-seed.html")

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
