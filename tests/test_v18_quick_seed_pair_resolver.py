import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_quick_seed_pair_resolver as resolver  # noqa: E402


class V18QuickSeedPairResolverTests(unittest.TestCase):
    def test_normalize_pot_id(self):
        self.assertEqual(resolver.normalize_pot_id("21T"), "21T")
        self.assertEqual(resolver.normalize_pot_id("21 t"), "21T")
        self.assertEqual(resolver.normalize_pot_id("pot 21"), "")

    def test_resolve_seed_conflict_and_orphan(self):
        seed = {
            "boxes": [
                {
                    "id": 1,
                    "description": "this is pot 21 T",
                    "x_norm": 0.10,
                    "y_norm": 0.10,
                    "w_norm": 0.10,
                    "h_norm": 0.10,
                },
                {
                    "id": 2,
                    "description": "this varietal no 11",
                    "x_norm": 0.12,
                    "y_norm": 0.11,
                    "w_norm": 0.10,
                    "h_norm": 0.10,
                },
                {
                    "id": 3,
                    "description": "this is pot 32 T",
                    "x_norm": 0.70,
                    "y_norm": 0.70,
                    "w_norm": 0.10,
                    "h_norm": 0.10,
                },
                {
                    "id": 4,
                    "description": "this varietal no 7",
                    "x_norm": 0.72,
                    "y_norm": 0.71,
                    "w_norm": 0.10,
                    "h_norm": 0.10,
                },
                {
                    "id": 5,
                    "description": "this varietal no 10",
                    "x_norm": 0.90,
                    "y_norm": 0.90,
                    "w_norm": 0.05,
                    "h_norm": 0.05,
                },
            ]
        }
        series_map = {
            7: "Sunset's Red Horizon",
            9: "Sasha Altai",
            10: "Gold Dust",
            11: "Azoychka",
        }
        pot_series_map = {"21T": 9, "32T": 7}
        out = resolver.resolve_seed(seed, pot_series_map=pot_series_map, series_map=series_map)
        self.assertEqual(out["total_rows"], 3)
        self.assertEqual(out["needs_review_count"], 2)
        self.assertEqual(out["review_reason_counts"]["pot_varietal_conflict"], 1)
        self.assertEqual(out["review_reason_counts"]["orphan_varietal_without_pot"], 1)
        self.assertEqual(out["auto_resolved_count"], 1)

    def test_main_outputs_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_json = tmp_path / "seed.json"
            series_csv = tmp_path / "series.csv"
            overrides_csv = tmp_path / "overrides.csv"
            baseline_csv = tmp_path / "baseline.csv"
            out_json = tmp_path / "resolution.json"
            out_md = tmp_path / "resolution.md"

            input_json.write_text(
                json.dumps(
                    {
                        "capture_date": "2026-03-01",
                        "source_asset_id": "A1",
                        "boxes": [
                            {"id": 1, "description": "this is pot 18 T"},
                            {"id": 2, "description": "this varietal no 7"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            series_csv.write_text(
                "series_number,variety_name\n7,Sunset's Red Horizon\n",
                encoding="utf-8",
            )
            overrides_csv.write_text("pot_id,series_number\n", encoding="utf-8")
            baseline_csv.write_text(
                "pot_id,packet_number\n18T,7\n",
                encoding="utf-8",
            )

            rc = resolver.main(
                [
                    "--input-json",
                    str(input_json),
                    "--series-map-csv",
                    str(series_csv),
                    "--pot-overrides-csv",
                    str(overrides_csv),
                    "--baseline-mapping-csv",
                    str(baseline_csv),
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
            self.assertEqual(parsed["needs_review_count"], 0)


if __name__ == "__main__":
    unittest.main()
