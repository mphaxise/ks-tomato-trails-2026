import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_single_photo_quick_labeler_page as builder  # noqa: E402


class BuildSinglePhotoQuickLabelerPageTests(unittest.TestCase):
    def test_pick_latest_image_prefers_latest_date_with_existing_file(self):
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
                writer = csv.DictWriter(handle, fieldnames=["capture_date", "source_asset_id", "photo_url"])
                writer.writeheader()
                writer.writerows(rows)

            # only the 3rd CSV row image exists (row_index=3, latest date)
            (image_dir / "03_A3.jpg").write_bytes(b"x")

            picked = builder.pick_latest_image(csv_path, image_dir)
            self.assertEqual(picked["capture_date"], "2026-03-02")
            self.assertEqual(picked["row_index"], "3")
            self.assertEqual(picked["source_asset_id"], "A3")

    def test_pick_latest_image_respects_preferred_row_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "mixed.csv"
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            rows = [
                {
                    "capture_date": "2026-03-02",
                    "row_index": "92",
                    "source_asset_id": "A2",
                    "photo_url": "u2",
                },
                {
                    "capture_date": "2026-03-02",
                    "row_index": "93",
                    "source_asset_id": "A3",
                    "photo_url": "u3",
                },
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

            picked = builder.pick_latest_image(
                csv_path, image_dir, preferred_row_index="93"
            )
            self.assertEqual(picked["source_asset_id"], "A3")
            self.assertEqual(picked["row_index"], "93")

    def test_pick_latest_image_respects_preferred_asset_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "mixed.csv"
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            rows = [
                {"capture_date": "2026-03-02", "source_asset_id": "A2", "photo_url": "u2"},
                {"capture_date": "2026-03-02", "source_asset_id": "A3", "photo_url": "u3"},
            ]
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["capture_date", "source_asset_id", "photo_url"])
                writer.writeheader()
                writer.writerows(rows)
            (image_dir / "01_A2.jpg").write_bytes(b"x")
            (image_dir / "02_A3.jpg").write_bytes(b"x")

            picked = builder.pick_latest_image(
                csv_path, image_dir, preferred_asset_id="A2"
            )
            self.assertEqual(picked["source_asset_id"], "A2")

    def test_build_page_contains_minimal_controls(self):
        html = builder.build_page(
            {
                "capture_date": "2026-03-01",
                "row_index": "92",
                "source_asset_id": "AF1QipMJ",
                "image_src": "../local/non_tomato_species/images/92_AF1QipMJ.jpg",
                "embedded_image_src": "data:image/jpeg;base64,AAAA",
                "photo_url": "https://example.com/p",
            }
        )
        self.assertIn("Quick Single Photo Labeler", html)
        self.assertIn("Download JSON (all together)", html)
        self.assertIn("id=\"canvas\"", html)
        self.assertIn("Draw Mode: OFF", html)
        self.assertIn("const EMBEDDED_IMAGE", html)
        self.assertIn("Do Not Use: OFF", html)
        self.assertIn("review_notes", html)
        self.assertIn("exclude_from_training", html)

    def test_copy_default_image_for_tracker_updates_image_src(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "src.jpg"
            src.write_bytes(b"abc")
            out_html = tmp_path / "tracker" / "single-photo-quick-labeler.html"
            out_html.parent.mkdir(parents=True, exist_ok=True)
            defaults = {
                "capture_date": "2026-03-01",
                "row_index": "92",
                "source_asset_id": "AF1QipXYZABCDEFGHI",
                "image_file_path": str(src),
                "image_src": "../local/old.jpg",
                "photo_url": "x",
            }
            updated = builder.copy_default_image_for_tracker(defaults, out_html)
            self.assertTrue(updated["image_src"].startswith("./assets/single-photo-quick-labeler/"))
            copied = Path(updated["copied_image_path"])
            self.assertTrue(copied.exists())

    def test_build_embedded_data_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.jpg"
            p.write_bytes(b"abc")
            data_url = builder.build_embedded_data_url(str(p))
            self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
