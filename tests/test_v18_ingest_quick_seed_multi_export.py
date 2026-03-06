import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_ingest_quick_seed_multi_export as ingest  # noqa: E402


class V18IngestQuickSeedMultiExportTests(unittest.TestCase):
    def test_ingest_multi_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_json = tmp_path / "multi.json"
            out_seed = tmp_path / "seed"
            out_data = tmp_path / "data"
            out_docs = tmp_path / "docs"
            manifest = tmp_path / "manifest.json"
            series_csv = tmp_path / "series.csv"
            overrides_csv = tmp_path / "overrides.csv"
            baseline_csv = tmp_path / "baseline.csv"

            input_json.write_text(
                json.dumps(
                    {
                        "version": "quick-multi-photo-v1",
                        "saved_at_utc": "2026-03-03T16:52:32.362Z",
                        "capture_date": "2026-03-01",
                        "photos": [
                            {
                                "row_index": "92",
                                "source_asset_id": "A1",
                                "photo_url": "https://example.com/1",
                                "boxes": [
                                    {"id": 1, "description": "18 T POT ID"},
                                    {"id": 2, "description": "7 VARIETAL"},
                                ],
                            },
                            {
                                "row_index": "93",
                                "source_asset_id": "A2",
                                "photo_url": "https://example.com/2",
                                "boxes": [],
                            },
                            {
                                "row_index": "94",
                                "source_asset_id": "A3",
                                "photo_url": "https://example.com/3",
                                "exclude_from_training": True,
                                "review_notes": "blurred and duplicate frame",
                                "boxes": [
                                    {"id": 1, "description": "19 T POT ID"},
                                    {"id": 2, "description": "8 VARIETAL"},
                                ],
                            },
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
            baseline_csv.write_text("pot_id,packet_number\n18T,7\n", encoding="utf-8")

            rc = ingest.main(
                [
                    "--input-json",
                    str(input_json),
                    "--output-seed-dir",
                    str(out_seed),
                    "--output-data-dir",
                    str(out_data),
                    "--output-docs-dir",
                    str(out_docs),
                    "--series-map-csv",
                    str(series_csv),
                    "--pot-overrides-csv",
                    str(overrides_csv),
                    "--baseline-mapping-csv",
                    str(baseline_csv),
                    "--manifest-json",
                    str(manifest),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(manifest.exists())
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["photos_total"], 3)
            self.assertEqual(payload["photos_processed"], 1)
            self.assertEqual(payload["photos_skipped"], 2)
            self.assertEqual(payload["photos_skipped_excluded"], 1)
            self.assertTrue(any(out_seed.glob("quick_seed_*.json")))
            self.assertTrue(any(out_data.glob("quick_seed_pair_resolution_*.json")))
            self.assertTrue(any(out_docs.glob("V1.8-QUICK-SEED-PAIR-RESOLUTION-*.md")))


if __name__ == "__main__":
    unittest.main()
