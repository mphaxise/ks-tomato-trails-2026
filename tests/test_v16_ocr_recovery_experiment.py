import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v16_ocr_recovery_experiment as exp  # noqa: E402


class V16OcrRecoveryExperimentTests(unittest.TestCase):
    def test_parse_numeric_tokens_limits_range_and_uniques(self):
        values = exp.parse_numeric_tokens("pot 3T maybe 3 41 0 12")
        self.assertEqual(values, [3, 12])

    def test_pot_number_from_pot_id(self):
        self.assertEqual(exp.pot_number_from_pot_id("7T"), 7)
        self.assertEqual(exp.pot_number_from_pot_id(""), 0)
        self.assertEqual(exp.pot_number_from_pot_id("XT"), 0)

    def test_choose_expected_for_run(self):
        rows = [
            {"capture_date": "2026-03-01"},
            {"capture_date": "2026-03-01"},
            {"capture_date": "2026-02-28"},
        ]
        self.assertEqual(exp.choose_expected_for_run(rows, "2026-03-01", 32), 2)
        self.assertEqual(exp.choose_expected_for_run(rows, "2026-02-28", 1), 1)


if __name__ == "__main__":
    unittest.main()
