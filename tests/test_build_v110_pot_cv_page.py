import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v110_pot_cv_page as builder  # noqa: E402


class BuildV110PotCvPageTests(unittest.TestCase):
    def test_build_page_outputs_expected_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_csv = tmp_path / "metrics.csv"
            algorithm_csv = tmp_path / "algo.csv"
            summary_json = tmp_path / "summary.json"
            output_html = tmp_path / "out.html"

            with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "pot_id",
                        "pot_number",
                        "variety_name",
                        "capture_date",
                        "source_asset_id",
                        "photo_url",
                        "image_path",
                        "overlay_path",
                        "crop_path",
                        "baseline_source_asset_id",
                        "baseline_capture_date",
                        "anchor_mode",
                        "anchor_confidence",
                        "label_confidence",
                        "focus_score",
                        "center_offset_ratio",
                        "pot_coverage",
                        "neighbor_spill_ratio",
                        "spill_in_pot_ratio",
                        "plant_count_estimate",
                        "canopy_components",
                        "chlorosis_ratio",
                        "growth_delta",
                        "health_score",
                        "tracking_readiness",
                        "next_step_code",
                        "next_step_text",
                        "data_quality_flag",
                        "blur_score",
                        "brightness_mean",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pot_id": "2T",
                        "pot_number": "2",
                        "variety_name": "Taxi",
                        "capture_date": "2026-03-06",
                        "source_asset_id": "A1",
                        "photo_url": "https://example.com/original.jpg",
                        "image_path": "local/non_tomato_species/images/a1.jpg",
                        "overlay_path": "assets/v1-10-pot-cv/2t_a1_overlay.jpg",
                        "crop_path": "assets/v1-10-pot-cv/2t_a1_crop.jpg",
                        "baseline_source_asset_id": "B1",
                        "baseline_capture_date": "2026-02-25",
                        "anchor_mode": "plant",
                        "anchor_confidence": "0.81",
                        "label_confidence": "0.54",
                        "focus_score": "0.77",
                        "center_offset_ratio": "0.14",
                        "pot_coverage": "0.065",
                        "neighbor_spill_ratio": "0.11",
                        "spill_in_pot_ratio": "0.08",
                        "plant_count_estimate": "2",
                        "canopy_components": "2",
                        "chlorosis_ratio": "0.04",
                        "growth_delta": "0.22",
                        "health_score": "81.4",
                        "tracking_readiness": "high",
                        "next_step_code": "ready_for_mask_labels",
                        "next_step_text": "Looks good for mask labeling.",
                        "data_quality_flag": "ok",
                        "blur_score": "220",
                        "brightness_mean": "124",
                    }
                )

            with algorithm_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "algorithm_key",
                        "metric_key",
                        "status",
                        "availability_ratio",
                        "variation_coeff",
                        "signal_summary",
                        "why_helpful",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "algorithm_key": "pot_polygon_focus_crop",
                        "metric_key": "focus_score",
                        "status": "helpful",
                        "availability_ratio": "1.0",
                        "variation_coeff": "0.23",
                        "signal_summary": "Focus crop.",
                        "why_helpful": "Suppresses neighbor spill.",
                    }
                )

            summary_json.write_text(
                json.dumps(
                    {
                        "run_id": "v1_10_test",
                        "run_date": "2026-03-06",
                        "pots_analyzed": 1,
                        "ready_for_mask_labels_count": 1,
                        "mask_label_queue_path": "data/research/v1_10/mask_label_queue.csv",
                        "average_focus_score": 0.77,
                        "average_spill_in_pot_ratio": 0.08,
                        "average_neighbor_spill_ratio": 0.11,
                        "growth_delta_availability_ratio": 1.0,
                        "tracking_readiness_counts": {"high": 1, "moderate": 0, "low": 0},
                        "next_step_counts": {"ready_for_mask_labels": 1},
                    }
                ),
                encoding="utf-8",
            )

            html = builder.build_page(
                metrics_rows=builder.read_csv_rows(metrics_csv),
                algorithm_rows=builder.read_csv_rows(algorithm_csv),
                summary=builder.read_json_optional(summary_json),
                source_metrics_csv=metrics_csv,
                source_algorithm_csv=algorithm_csv,
                source_summary_json=summary_json,
            )
            output_html.write_text(html, encoding="utf-8")

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn("Pot-Anchored Indoor CV Viewer", rendered)
            self.assertIn("ready_for_mask_labels", rendered)
            self.assertIn("./assets/v1-10-pot-cv/2t_a1_overlay.jpg", rendered)
            self.assertIn("Suppresses neighbor spill.", rendered)
            self.assertIn("data/research/v1_10/mask_label_queue.csv", rendered)


if __name__ == "__main__":
    unittest.main()
