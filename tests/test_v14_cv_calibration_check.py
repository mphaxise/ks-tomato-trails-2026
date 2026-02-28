import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v14_cv_calibration_check as calibration  # noqa: E402


class V14CalibrationCheckTests(unittest.TestCase):
    def test_run_check_computes_expected_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            predicted_csv = tmp_path / "predicted.csv"
            manual_csv = tmp_path / "manual.csv"
            json_out = tmp_path / "summary.json"
            markdown_out = tmp_path / "summary.md"

            with predicted_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["pot_id", "survival_hypothesis", "action_code"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pot_id": "1T",
                        "survival_hypothesis": "low",
                        "action_code": "increase_light",
                    }
                )
                writer.writerow(
                    {
                        "pot_id": "2T",
                        "survival_hypothesis": "moderate",
                        "action_code": "maintain_current_care",
                    }
                )

            with manual_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["pot_id", "expected_survival", "expected_action"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pot_id": "1T",
                        "expected_survival": "low",
                        "expected_action": "increase_light",
                    }
                )
                writer.writerow(
                    {
                        "pot_id": "2T",
                        "expected_survival": "high",
                        "expected_action": "maintain_current_care",
                    }
                )

            result = calibration.run_check(
                predicted_csv=predicted_csv,
                manual_csv=manual_csv,
                json_out=json_out,
                markdown_out=markdown_out,
            )
            self.assertEqual(result["manual_rows"], 2)
            self.assertAlmostEqual(float(result["survival_accuracy"]), 0.5, places=6)
            self.assertAlmostEqual(float(result["action_accuracy"]), 1.0, places=6)
            self.assertAlmostEqual(float(result["joint_accuracy"]), 0.5, places=6)
            self.assertTrue(json_out.exists())
            self.assertTrue(markdown_out.exists())

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["manual_rows"], 2)


if __name__ == "__main__":
    unittest.main()
