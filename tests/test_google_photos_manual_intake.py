import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import google_photos_manual_intake as intake  # noqa: E402


class GooglePhotosManualIntakeTests(unittest.TestCase):
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
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_pipeline_happy_path(self):
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

            input_csv = tmp_path / "input.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "https://photos.google.com/share/a/item/1",
                        "caption": "Stupice | stupice_01 | TomatoFest",
                        "capture_date": "2026-02-25",
                        "captured_at": "2026-02-25T09:10:11-08:00",
                        "uploaded_at": "2026-02-25T11:00:00-08:00",
                        "timezone": "-08:00",
                        "latitude": "37.8599",
                        "longitude": "-122.4853",
                        "device_model": "iPhone",
                        "notes": "just watered",
                    },
                    {
                        "photo_url": "https://photos.google.com/share/a/item/2",
                        "caption": "glacier | glacier_01 | unknown | packet visible",
                        "capture_date": "",
                        "captured_at": "2026-02-25T09:20:00-08:00",
                        "uploaded_at": "",
                        "timezone": "-08:00",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "iPhone",
                        "notes": "",
                    },
                ],
            )

            output_csv = tmp_path / "output.csv"
            count = intake.run_pipeline(input_csv, output_csv, varieties)
            self.assertEqual(count, 2)

            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["variety_name"], "Stupice")
            self.assertEqual(rows[0]["seed_source_or_packet_name"], "TomatoFest")
            self.assertEqual(rows[0]["notes"], "just watered")
            self.assertEqual(rows[1]["variety_name"], "Glacier")
            self.assertEqual(rows[1]["capture_date"], "2026-02-25")
            self.assertEqual(rows[1]["notes"], "packet visible")

    def test_unknown_variety_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps([{"id": "stupice", "name": "Stupice"}]), encoding="utf-8"
            )
            input_csv = tmp_path / "input.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "https://photos.google.com/share/a/item/1",
                        "caption": "Unknown Variety | plant_01 | unknown",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "",
                    }
                ],
            )

            output_csv = tmp_path / "output.csv"
            with self.assertRaises(ValueError):
                intake.run_pipeline(input_csv, output_csv, varieties)

    def test_malformed_row_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps([{"id": "stupice", "name": "Stupice"}]), encoding="utf-8"
            )
            input_csv = tmp_path / "input.csv"
            input_csv.write_text(
                "photo_url,caption,capture_date,captured_at,uploaded_at,timezone,latitude,longitude,device_model,notes\n"
                "https://photos.google.com/share/a/item/1,Stupice | stupice_01 | unknown,2026-02-25,2026-02-25T09:10:00-08:00,-08:00,,,iPhone\n",
                encoding="utf-8",
            )
            output_csv = tmp_path / "output.csv"
            with self.assertRaisesRegex(ValueError, "Malformed CSV row"):
                intake.run_pipeline(input_csv, output_csv, varieties)

    def test_album_url_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            varieties = tmp_path / "varieties.json"
            varieties.write_text(
                json.dumps([{"id": "stupice", "name": "Stupice"}]), encoding="utf-8"
            )
            input_csv = tmp_path / "input.csv"
            self.write_csv(
                input_csv,
                [
                    {
                        "photo_url": "",
                        "caption": "Stupice | stupice_01 | unknown",
                        "capture_date": "2026-02-25",
                        "captured_at": "",
                        "uploaded_at": "",
                        "timezone": "",
                        "latitude": "",
                        "longitude": "",
                        "device_model": "",
                        "notes": "just watered",
                    }
                ],
            )
            output_csv = tmp_path / "output.csv"
            intake.run_pipeline(
                input_csv,
                output_csv,
                varieties,
                default_album_url="https://photos.google.com/share/album",
            )
            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["photo"], "https://photos.google.com/share/album")


if __name__ == "__main__":
    unittest.main()
