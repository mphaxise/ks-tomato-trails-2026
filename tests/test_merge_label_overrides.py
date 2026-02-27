import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_label_overrides as merger  # noqa: E402


class MergeLabelOverridesTests(unittest.TestCase):
    def write_rows(self, path: Path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=merger.OVERRIDE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_merge_updates_existing_and_inserts_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.csv"
            incoming = tmp_path / "incoming.csv"

            self.write_rows(
                base,
                [
                    {
                        "row_index": "1",
                        "source_asset_id": "asset1",
                        "classification_label": "non_tomato",
                        "species_common_name": "Lettuce",
                        "species_scientific_name": "Lactuca sativa",
                        "confidence": "0.99",
                        "labeling_method": "manual_packet_label",
                        "caption": "old",
                        "notes_append": "",
                        "ocr_excerpt": "",
                    }
                ],
            )

            self.write_rows(
                incoming,
                [
                    {
                        "row_index": "1",
                        "source_asset_id": "asset1",
                        "classification_label": "non_tomato",
                        "species_common_name": "Lettuce",
                        "species_scientific_name": "Lactuca sativa",
                        "confidence": "0.95",
                        "labeling_method": "manual_web_edit",
                        "caption": "updated",
                        "notes_append": "pot_tag=1",
                        "ocr_excerpt": "",
                    },
                    {
                        "row_index": "2",
                        "source_asset_id": "asset2",
                        "classification_label": "tomato",
                        "species_common_name": "Taxi",
                        "species_scientific_name": "Solanum lycopersicum",
                        "confidence": "0.99",
                        "labeling_method": "manual_web_edit",
                        "caption": "new",
                        "notes_append": "",
                        "ocr_excerpt": "",
                    },
                ],
            )

            merged, inserted, updated = merger.merge_rows(
                merger.load_csv_rows(base), merger.load_csv_rows(incoming)
            )

            self.assertEqual(inserted, 1)
            self.assertEqual(updated, 1)
            self.assertEqual(len(merged), 2)
            self.assertEqual(merged[0]["caption"], "updated")
            self.assertEqual(merged[1]["species_common_name"], "Taxi")


if __name__ == "__main__":
    unittest.main()
