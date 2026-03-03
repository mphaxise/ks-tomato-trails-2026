import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_batch_quick_seed_resolution as batch  # noqa: E402


class V18BatchQuickSeedResolutionTests(unittest.TestCase):
    def test_is_quick_seed_payload(self):
        valid = {
            "version": "quick-single-photo-v1",
            "capture_date": "2026-03-01",
            "source_asset_id": "A1",
            "boxes": [],
        }
        invalid = {"capture_date": "2026-03-01", "boxes": []}
        self.assertTrue(batch.is_quick_seed_payload(valid))
        self.assertFalse(batch.is_quick_seed_payload(invalid))

    def test_discover_and_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            seed_dir = tmp_path / "seeds"
            seed_dir.mkdir(parents=True, exist_ok=True)

            valid_seed = seed_dir / "quick_seed_2026-03-01_92_x.json"
            invalid_seed = seed_dir / "quick_seed_pair_resolution.json"

            valid_seed.write_text(
                json.dumps(
                    {
                        "version": "quick-single-photo-v1",
                        "capture_date": "2026-03-01",
                        "row_index": "92",
                        "source_asset_id": "A1",
                        "boxes": [
                            {"id": 1, "description": "this is pot 18 T"},
                            {"id": 2, "description": "this varietal no 7"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            invalid_seed.write_text(
                json.dumps({"generated_at_utc": "x", "rows": []}), encoding="utf-8"
            )

            series_csv = tmp_path / "series.csv"
            overrides_csv = tmp_path / "overrides.csv"
            baseline_csv = tmp_path / "baseline.csv"
            out_json = tmp_path / "batch.json"
            out_md = tmp_path / "batch.md"

            series_csv.write_text(
                "series_number,variety_name\n7,Sunset's Red Horizon\n", encoding="utf-8"
            )
            overrides_csv.write_text("pot_id,series_number\n", encoding="utf-8")
            baseline_csv.write_text("pot_id,packet_number\n18T,7\n", encoding="utf-8")

            rc = batch.main(
                [
                    "--seed-dir",
                    str(seed_dir),
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
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["seed_files_discovered"], 2)
            self.assertEqual(payload["seed_files_processed"], 1)
            self.assertEqual(payload["total_rows"], 1)
            self.assertEqual(payload["total_needs_review"], 0)


if __name__ == "__main__":
    unittest.main()
