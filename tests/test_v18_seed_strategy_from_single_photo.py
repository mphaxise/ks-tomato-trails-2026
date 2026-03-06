import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_seed_strategy_from_single_photo as strat  # noqa: E402


class V18SeedStrategyFromSinglePhotoTests(unittest.TestCase):
    def test_summarize_infers_level_priority(self):
        seed = {
            "image_src": "img.jpg",
            "reviewer": "pk",
            "global_description": "test",
            "levels": [
                {"key": "L1", "description": "pot stake number label"},
                {"key": "L2", "description": "plant canopy"},
            ],
            "boxes": [
                {"level_key": "L1", "label": "pot_label"},
                {"level_key": "L1", "label": "pot_label"},
                {"level_key": "L2", "label": "plant_region"},
            ],
        }
        summary = strat.summarize(seed)
        self.assertEqual(summary["levels_count"], 2)
        self.assertEqual(summary["boxes_count"], 3)
        level_rows = {row["level_key"]: row for row in summary["level_rows"]}
        self.assertEqual(level_rows["L1"]["priority_class"], "identity_signal")
        self.assertEqual(level_rows["L2"]["priority_class"], "growth_signal")

    def test_main_writes_outputs(self):
        seed = {
            "image_src": "img.jpg",
            "reviewer": "pk",
            "global_description": "test",
            "levels": [{"key": "L1", "description": "background number"}],
            "boxes": [{"level_key": "L1", "label": "background_number"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_json = tmp_path / "seed.json"
            out_json = tmp_path / "summary.json"
            out_md = tmp_path / "strategy.md"
            input_json.write_text(json.dumps(seed), encoding="utf-8")
            rc = strat.main(
                [
                    "--input-json",
                    str(input_json),
                    "--output-json",
                    str(out_json),
                    "--output-md",
                    str(out_md),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())
            self.assertIn("Seed Pipeline Strategy", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
