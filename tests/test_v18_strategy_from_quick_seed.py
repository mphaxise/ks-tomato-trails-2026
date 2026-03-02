import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_strategy_from_quick_seed as strategy  # noqa: E402


class V18StrategyFromQuickSeedTests(unittest.TestCase):
    def test_classify_description(self):
        self.assertEqual(strategy.classify_description("this varietal no 11"), ("varietal_number", "11"))
        self.assertEqual(strategy.classify_description("this is tag for pot 21 T"), ("pot_id", "21T"))
        self.assertEqual(strategy.classify_description("this is pot 21"), ("other", ""))
        self.assertEqual(strategy.classify_description(""), ("unlabeled", ""))

    def test_summarize_counts(self):
        seed = {
            "boxes": [
                {"id": 1, "description": "varietal no 7"},
                {"id": 2, "description": "tag for pot 31 T"},
                {"id": 3, "description": "tag for pot 31 T"},
                {"id": 4, "description": ""},
            ]
        }
        s = strategy.summarize(seed)
        self.assertEqual(s["boxes_total"], 4)
        self.assertEqual(s["type_counts"]["varietal_number"], 1)
        self.assertEqual(s["type_counts"]["pot_id"], 2)
        self.assertEqual(s["pot_id_counts"]["31T"], 2)
        self.assertEqual(s["varietal_number_counts"]["7"], 1)
        self.assertTrue(s["confirmed_annotation_rules"]["varietal_no_maps_to_series_number"])
        self.assertTrue(s["confirmed_annotation_rules"]["pot_id_requires_t_suffix"])
        self.assertEqual(
            s["identity_resolution_policy"]["conflict_reason_code"], "pot_varietal_conflict"
        )

    def test_main_outputs_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_json = tmp_path / "seed.json"
            out_json = tmp_path / "summary.json"
            out_md = tmp_path / "strategy.md"
            input_json.write_text(
                json.dumps(
                    {
                        "capture_date": "2026-03-01",
                        "source_asset_id": "A1",
                        "boxes": [{"id": 1, "description": "tag for pot 18 T"}],
                    }
                ),
                encoding="utf-8",
            )
            rc = strategy.main(
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
            parsed = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertIn("identity_resolution_policy", parsed)
            md = out_md.read_text(encoding="utf-8")
            self.assertIn("## Confirmed Label Rules", md)
            self.assertIn("pot_varietal_conflict", md)
            self.assertNotIn("Immediate Next Inputs Needed From You", md)


if __name__ == "__main__":
    unittest.main()
