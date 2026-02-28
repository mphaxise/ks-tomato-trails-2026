import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_v14_cv_research_page as builder  # noqa: E402


class BuildV14CvResearchPageTests(unittest.TestCase):
    def test_build_page_outputs_expected_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_csv = tmp_path / "metrics.csv"
            algo_csv = tmp_path / "algo.csv"
            summary_json = tmp_path / "summary.json"
            calibration_json = tmp_path / "calibration.json"
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
                        "baseline_source_asset_id",
                        "baseline_capture_date",
                        "plant_count_estimate",
                        "canopy_components",
                        "vegetation_coverage",
                        "chlorosis_ratio",
                        "growth_delta",
                        "health_score",
                        "survival_hypothesis",
                        "action_code",
                        "action_recommendation",
                        "data_quality_flag",
                        "blur_score",
                        "brightness_mean",
                        "edge_density",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pot_id": "1T",
                        "pot_number": "1",
                        "variety_name": "Taxi",
                        "capture_date": "2026-02-27",
                        "source_asset_id": "A1",
                        "photo_url": "https://example.com/1.jpg",
                        "image_path": "local/non_tomato_species/images/01.jpg",
                        "baseline_source_asset_id": "B1",
                        "baseline_capture_date": "2026-02-25",
                        "plant_count_estimate": "2",
                        "canopy_components": "3",
                        "vegetation_coverage": "0.05",
                        "chlorosis_ratio": "0.1",
                        "growth_delta": "0.2",
                        "health_score": "72.5",
                        "survival_hypothesis": "moderate",
                        "action_code": "maintain_current_care",
                        "action_recommendation": "Keep monitoring weekly.",
                        "data_quality_flag": "ok",
                        "blur_score": "250",
                        "brightness_mean": "120",
                        "edge_density": "0.02",
                    }
                )

            with algo_csv.open("w", encoding="utf-8", newline="") as handle:
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
                        "algorithm_key": "vegetation_segmentation_exg_hsv",
                        "metric_key": "vegetation_coverage",
                        "status": "helpful",
                        "availability_ratio": "1.0",
                        "variation_coeff": "0.55",
                        "signal_summary": "Coverage proxy.",
                        "why_helpful": "Tracks growth.",
                    }
                )

            summary_json.write_text(
                json.dumps(
                    {
                        "run_id": "v1_4_test",
                        "run_date": "2026-02-27",
                        "survival_counts": {"high": 0, "moderate": 1, "low": 0},
                        "action_counts": {"maintain_current_care": 1},
                    }
                ),
                encoding="utf-8",
            )
            calibration_json.write_text(
                json.dumps(
                    {
                        "manual_rows": 5,
                        "survival_accuracy": 0.8,
                        "action_accuracy": 0.6,
                        "joint_accuracy": 0.6,
                        "mismatches": [],
                    }
                ),
                encoding="utf-8",
            )

            metrics_rows = builder.read_csv_rows(metrics_csv)
            algo_rows = builder.read_csv_rows(algo_csv)
            page = builder.build_page(
                metrics_rows=metrics_rows,
                algorithm_rows=algo_rows,
                summary=builder.read_json_optional(summary_json),
                calibration=builder.read_json_optional(calibration_json),
                source_metrics_csv=metrics_csv,
                source_algorithm_csv=algo_csv,
            )
            output_html.write_text(page, encoding="utf-8")

            rendered = output_html.read_text(encoding="utf-8")
            self.assertIn("Computer Vision Research Output", rendered)
            self.assertIn("Taxi", rendered)
            self.assertIn("maintain_current_care", rendered)
            self.assertIn("Survival Accuracy", rendered)
            self.assertIn("vegetation_segmentation_exg_hsv", rendered)
            self.assertIn("Flip for metric meaning", rendered)
            self.assertIn("Coverage:</strong> green canopy area", rendered)


if __name__ == "__main__":
    unittest.main()
