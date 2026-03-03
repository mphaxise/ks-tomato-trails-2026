import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v18_ground_truth_accuracy_audit as audit  # noqa: E402


class V18GroundTruthAccuracyAuditTests(unittest.TestCase):
    def test_build_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            imported = tmp_path / "imported_seeds"
            imported.mkdir(parents=True, exist_ok=True)
            pair_dir = tmp_path / "pair"
            pair_dir.mkdir(parents=True, exist_ok=True)
            mapping_csv = tmp_path / "mapping.csv"

            seed = {
                "version": "quick-single-photo-v1",
                "capture_date": "2026-03-01",
                "row_index": "92",
                "source_asset_id": "A1",
                "boxes": [
                    {"id": 1, "description": "18 T POT ID"},
                    {"id": 2, "description": "7 VARIETAL"},
                ],
            }
            (imported / "quick_seed_2026-03-01_92_A1.json").write_text(
                json.dumps(seed), encoding="utf-8"
            )

            pair = {
                "capture_date": "2026-03-01",
                "row_index": "92",
                "source_asset_id": "A1",
                "total_rows": 1,
                "auto_resolved_count": 1,
                "needs_review_count": 0,
                "review_reason_counts": {},
                "rows": [
                    {
                        "pot_id": "18T",
                        "varietal_number": 7,
                        "expected_series_number": 7,
                        "review_reason": "",
                    }
                ],
            }
            (pair_dir / "quick_seed_pair_resolution_2026-03-01_92.json").write_text(
                json.dumps(pair), encoding="utf-8"
            )

            with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "capture_date",
                        "row_index",
                        "source_asset_id",
                        "pot_id",
                        "packet_number",
                        "variety_name",
                        "resolution_source",
                        "mapping_note",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "capture_date": "2026-03-01",
                        "row_index": "92",
                        "source_asset_id": "A1",
                        "pot_id": "18T",
                        "packet_number": "7",
                        "variety_name": "Sunset's Red Horizon",
                        "resolution_source": "manual_override",
                        "mapping_note": "",
                    }
                )

            out = audit.build_audit(
                imported_seed_dir=imported,
                mapping_csv=mapping_csv,
                pair_resolution_glob=str(pair_dir / "quick_seed_pair_resolution_*.json"),
            )
            self.assertEqual(out["seed_rows_total"], 1)
            self.assertEqual(out["joined_rows_total"], 1)
            self.assertEqual(out["metrics"]["pot_presence_match_rate"], 1.0)
            self.assertEqual(out["metrics"]["series_presence_match_rate"], 1.0)
            self.assertEqual(out["metrics"]["pair_exact_match_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
