import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw0_crop_target_sweep as sweep  # noqa: E402


class V17Sw0CropTargetSweepTests(unittest.TestCase):
    def test_parse_int(self):
        self.assertEqual(sweep.parse_int("12"), 12)
        self.assertEqual(sweep.parse_int("x", default=7), 7)

    def test_candidates_include_baseline(self):
        names = {c.name for c in sweep.CANDIDATES}
        self.assertIn("baseline", names)
        self.assertGreaterEqual(len(names), 4)

    def test_build_markdown_contains_table(self):
        text = sweep.build_markdown(
            [
                {
                    "candidate": "baseline",
                    "x0": 0.28,
                    "x1": 0.72,
                    "y0": 0.45,
                    "y1": 0.98,
                    "match_rate_pct": 10.0,
                    "digits_rate_pct": 50.0,
                    "rows_with_match": 5,
                    "total_rows": 50,
                }
            ],
            Path("queue.csv"),
        )
        self.assertIn("V1.7 SW-0 Crop-Target Sweep", text)
        self.assertIn("`baseline`", text)
        self.assertIn("Match %", text)


if __name__ == "__main__":
    unittest.main()
