import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v16_random_intake_research as research  # noqa: E402


class V16RandomIntakeResearchTests(unittest.TestCase):
    def test_classify_run_mode_baseline(self):
        mode = research.classify_run_mode(
            {
                "total_rows": 26,
                "caption_rate": 1.0,
                "non_unknown_label_rate": 1.0,
                "full_resolution_rate": 1.0,
                "sequential_inferred_rate": 0.2,
            }
        )
        self.assertEqual(mode, "baseline_labeled_single_pot")

    def test_classify_run_mode_watering_day_sequence(self):
        mode = research.classify_run_mode(
            {
                "total_rows": 32,
                "caption_rate": 0.0,
                "non_unknown_label_rate": 0.0,
                "full_resolution_rate": 0.0,
                "sequential_inferred_rate": 1.0,
            }
        )
        self.assertEqual(mode, "watering_day_unlabeled_sequence")

    def test_build_recommended_routine_returns_stages(self):
        stages = research.build_recommended_routine(
            latest_mode="watering_day_unlabeled_sequence"
        )
        self.assertGreaterEqual(len(stages), 7)
        self.assertEqual(stages[0]["name"], "Batch Partitioning")
        self.assertEqual(stages[-1]["name"], "Persist And Learn")


if __name__ == "__main__":
    unittest.main()
