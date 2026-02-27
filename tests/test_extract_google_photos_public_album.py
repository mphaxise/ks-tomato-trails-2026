import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import extract_google_photos_public_album as extractor  # noqa: E402


class ExtractGooglePhotosPublicAlbumTests(unittest.TestCase):
    def test_parse_ds1_payload_and_map_rows(self):
        ds_payload = [
            None,
            [
                [
                    "asset_1",
                    [
                        "https://lh3.googleusercontent.com/photo1",
                        3072,
                        4080,
                        None,
                        None,
                        None,
                        None,
                        None,
                        [4080, 3072, 1, None, ["Google", "Pixel 8 Pro"]],
                        [4010027],
                        2,
                        [[1, 1]],
                    ],
                    1772060629626,
                    "media_key_1",
                    -28800000,
                    1772062927824,
                    ["owner_1"],
                    [[2]],
                    2,
                    {},
                ],
                [
                    "asset_2",
                    [
                        "https://lh3.googleusercontent.com/photo2",
                        3072,
                        4080,
                        None,
                        None,
                        None,
                        None,
                        None,
                        [4080, 3072, 1, None, ["Google", "Pixel 8 Pro"]],
                        [4010027],
                        2,
                        [[1, 1]],
                    ],
                    1772060639626,
                    "media_key_2",
                    -28800000,
                    1772062937824,
                    ["owner_1"],
                    [[2]],
                    2,
                    {},
                ],
            ],
            "",
            [
                "album_id_1",
                "K's Tomato Trails 2026 - Intake",
                [1772060629000, 1772061108000],
                "https://video-download.example",
                [],
                [],
                [],
                "album_id_1",
                1,
                [],
                [],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "",
                "auth_key_1",
                2,
                26,
                None,
                None,
                None,
                [19974],
                0,
                None,
                [],
                None,
                [],
                1,
                "https://photos.app.goo.gl/example",
                None,
                5,
                {},
            ],
            None,
            0,
        ]
        html = (
            "<html><head></head><body>"
            "AF_initDataCallback({key: 'ds:1', hash: '1', data:"
            + json.dumps(ds_payload)
            + ", sideChannel: {}});"
            "</body></html>"
        )

        payload = extractor.parse_ds1_payload(html)
        parsed = extractor.parse_album_rows(
            payload, "https://photos.app.goo.gl/example"
        )

        self.assertEqual(parsed["album_id"], "album_id_1")
        self.assertEqual(parsed["album_short_url"], "https://photos.app.goo.gl/example")
        self.assertEqual(len(parsed["manifest_rows"]), 2)
        self.assertEqual(len(parsed["mixed_rows"]), 2)
        self.assertEqual(parsed["manifest_rows"][0]["source_asset_id"], "asset_1")
        self.assertEqual(parsed["mixed_rows"][0]["source_platform"], "google_photos")

    def test_write_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            extractor.write_csv(
                path,
                ["a", "b"],
                [{"a": "1", "b": "2"}],
            )
            data = path.read_text(encoding="utf-8")
            self.assertIn("a,b", data)
            self.assertIn("1,2", data)


if __name__ == "__main__":
    unittest.main()
