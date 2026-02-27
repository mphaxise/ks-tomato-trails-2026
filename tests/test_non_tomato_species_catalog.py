import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import non_tomato_species_catalog as catalog  # noqa: E402


class NonTomatoSpeciesCatalogTests(unittest.TestCase):
    def write_csv(self, path: Path, rows):
        fieldnames = [
            "photo_url",
            "caption",
            "capture_date",
            "captured_at",
            "uploaded_at",
            "timezone",
            "latitude",
            "longitude",
            "device_model",
            "notes",
            "source_asset_id",
            "source_platform",
            "classification_label",
            "species_common_name",
            "variety_name",
            "species_scientific_name",
            "specific_note",
            "weather_hypothesis",
            "expected_harvest_window",
            "confidence",
            "labeling_method",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_catalog_filters_tomato_and_labels_non_tomato(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps(
                    [
                        {"id": "stupice", "name": "Stupice"},
                        {"id": "glacier", "name": "Glacier"},
                    ]
                ),
                encoding="utf-8",
            )
            input_csv = tmp_path / "mixed.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "https://example.com/1",
                        "caption": "Stupice | stupice_01 | TomatoFest",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "",
                        "source_asset_id": "a1",
                        "source_platform": "google_photos",
                    },
                    {
                        "photo_url": "https://example.com/2",
                        "caption": "Marigold seedling tray",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "next to tomato tray",
                        "source_asset_id": "a2",
                        "source_platform": "google_photos",
                    },
                ],
            )
            db_path = tmp_path / "non_tomato.db"
            stats = catalog.catalog_non_tomato_rows(input_csv, db_path, varieties)
            self.assertEqual(stats["processed_rows"], 2)
            self.assertEqual(stats["skipped_tomato"], 1)
            self.assertEqual(stats["inserted"], 1)

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT species_common_name, species_scientific_name, classification_label FROM non_tomato_observations"
                ).fetchone()
            self.assertEqual(row[0], "Marigold")
            self.assertEqual(row[1], "Tagetes spp.")
            self.assertEqual(row[2], "non_tomato")

    def test_unknown_species_defaults_to_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps([{"id": "stupice", "name": "Stupice"}]), encoding="utf-8"
            )
            input_csv = tmp_path / "mixed.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "https://example.com/3",
                        "caption": "mystery volunteer plant",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "",
                        "source_asset_id": "a3",
                        "source_platform": "google_photos",
                    }
                ],
            )
            db_path = tmp_path / "non_tomato.db"
            catalog.catalog_non_tomato_rows(input_csv, db_path, varieties)
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT species_common_name, confidence FROM non_tomato_observations"
                ).fetchone()
            self.assertEqual(row[0], "unknown")
            self.assertLess(float(row[1]), 0.5)

    def test_pea_keyword_maps_species(self):
        species = catalog.classify_species("Pea | non_tomato_01 | unknown", "")
        self.assertEqual(species.common_name, "Pea")
        self.assertEqual(species.scientific_name, "Pisum sativum")

    def test_leek_keyword_maps_species(self):
        species = catalog.classify_species("Leek | non_tomato_08 | Tadorna OG", "")
        self.assertEqual(species.common_name, "Leek")
        self.assertEqual(species.scientific_name, "Allium porrum")

    def test_red_cabbage_keyword_maps_species(self):
        species = catalog.classify_species(
            "Red Cabbage (Ruby Perfection F1) | non_tomato_10 | verified", ""
        )
        self.assertEqual(species.common_name, "Red Cabbage")
        self.assertEqual(species.scientific_name, "Brassica oleracea var. capitata")

    def test_catalog_preserves_curated_fields_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps([{"id": "stupice", "name": "Stupice"}]), encoding="utf-8"
            )
            input_csv = tmp_path / "curated.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "https://example.com/4",
                        "caption": "Bloomsdale Spinach | non_tomato_03 | verified",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "",
                        "source_asset_id": "a4",
                        "source_platform": "google_photos",
                        "classification_label": "non_tomato",
                        "species_common_name": "Spinach",
                        "variety_name": "Bloomsdale Spinach",
                        "species_scientific_name": "Spinacia oleracea",
                        "specific_note": "Classic heirloom spinach.",
                        "weather_hypothesis": "Thrives in cool foggy weather.",
                        "expected_harvest_window": "~ 40-50 days.",
                        "confidence": "0.99",
                        "labeling_method": "manual_web_edit",
                    }
                ],
            )
            db_path = tmp_path / "non_tomato.db"
            catalog.catalog_non_tomato_rows(input_csv, db_path, varieties)
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT species_common_name, variety_name, specific_note, weather_hypothesis, expected_harvest_window, labeling_method "
                    "FROM non_tomato_observations"
                ).fetchone()
            self.assertEqual(row[0], "Spinach")
            self.assertEqual(row[1], "Bloomsdale Spinach")
            self.assertIn("heirloom", row[2].lower())
            self.assertIn("foggy", row[3].lower())
            self.assertIn("40-50", row[4])
            self.assertEqual(row[5], "manual_web_edit")


if __name__ == "__main__":
    unittest.main()
