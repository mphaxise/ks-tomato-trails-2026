import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_multi_photo_quick_labeler_page as builder  # noqa: E402


class BuildMultiPhotoQuickLabelerPageTests(unittest.TestCase):
    def test_pick_latest_images_returns_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "mixed.csv"
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            rows = [
                {"capture_date": "2026-03-01", "source_asset_id": "A1", "photo_url": "u1"},
                {"capture_date": "2026-03-02", "source_asset_id": "A2", "photo_url": "u2"},
                {"capture_date": "2026-03-02", "source_asset_id": "A3", "photo_url": "u3"},
            ]
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["capture_date", "source_asset_id", "photo_url"]
                )
                writer.writeheader()
                writer.writerows(rows)

            (image_dir / "02_A2.jpg").write_bytes(b"x")
            (image_dir / "03_A3.jpg").write_bytes(b"x")

            selected = builder.pick_latest_images(csv_path, image_dir)
            self.assertEqual(len(selected), 2)
            self.assertEqual(selected[0]["source_asset_id"], "A2")
            self.assertEqual(selected[1]["source_asset_id"], "A3")
            self.assertEqual(selected[0]["capture_date"], "2026-03-02")

    def test_pick_latest_images_honors_max(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "mixed.csv"
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            rows = [
                {"capture_date": "2026-03-02", "row_index": "92", "source_asset_id": "A2", "photo_url": "u2"},
                {"capture_date": "2026-03-02", "row_index": "93", "source_asset_id": "A3", "photo_url": "u3"},
                {"capture_date": "2026-03-02", "row_index": "94", "source_asset_id": "A4", "photo_url": "u4"},
            ]
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["capture_date", "row_index", "source_asset_id", "photo_url"],
                )
                writer.writeheader()
                writer.writerows(rows)

            (image_dir / "01_A2.jpg").write_bytes(b"x")
            (image_dir / "02_A3.jpg").write_bytes(b"x")
            (image_dir / "03_A4.jpg").write_bytes(b"x")

            selected = builder.pick_latest_images(csv_path, image_dir, max_images=2)
            self.assertEqual(len(selected), 2)
            self.assertEqual(selected[0]["row_index"], "92")
            self.assertEqual(selected[1]["row_index"], "93")

    def test_build_page_contains_global_controls(self):
        html = builder.build_page(
            [
                {
                    "capture_date": "2026-03-01",
                    "row_index": "92",
                    "source_asset_id": "A1",
                    "image_src": "../local/non_tomato_species/images/92_A1.jpg",
                    "photo_url": "https://example.com/1",
                },
                {
                    "capture_date": "2026-03-01",
                    "row_index": "93",
                    "source_asset_id": "A2",
                    "image_src": "../local/non_tomato_species/images/93_A2.jpg",
                    "photo_url": "https://example.com/2",
                },
            ]
        )
        self.assertIn("Quick Multi Photo Labeler", html)
        self.assertIn("Save All Local", html)
        self.assertIn("Download JSON (all photos)", html)
        self.assertIn("const PHOTOS =", html)


if __name__ == "__main__":
    unittest.main()
