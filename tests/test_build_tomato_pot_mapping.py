import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_tomato_pot_mapping as mapper  # noqa: E402


class BuildTomatoPotMappingTests(unittest.TestCase):
    def test_canonicalize_variety_aliases(self):
        self.assertEqual(
            mapper.canonicalize_variety_name("Bes Yellow Latvian"),
            "Iles Yellow Latvian",
        )
        self.assertEqual(
            mapper.canonicalize_variety_name("Walmea Wild Cherry"),
            "Waimea Wild Cherry",
        )

    def test_extract_pot_id_and_packet_number(self):
        pot_id = mapper.extract_pot_id(
            "notes",
            "manual check; pot_tag=07t; packet_tag=3",
            "caption",
            "",
        )
        packet = mapper.extract_packet_number(
            "notes",
            "manual check; pot_tag=07t; packet_tag=3",
            "",
            "",
        )
        self.assertEqual(pot_id, "7T")
        self.assertEqual(packet, "3")

    def test_build_mapping_success(self):
        rows = [
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:00:00-08:00",
                "source_asset_id": "asset_1",
                "photo_url": "https://example.com/1.jpg",
                "classification_label": "tomato",
                "notes": "pot_tag=1T; packet_tag=1",
                "caption": "Taxi | tomato_01 | verified",
                "variety_name": "Taxi",
                "species_common_name": "Taxi",
                "labeling_method": "manual_packet_label",
                "confidence": "0.99",
                "ocr_excerpt": "",
            },
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:01:00-08:00",
                "source_asset_id": "asset_2",
                "photo_url": "https://example.com/2.jpg",
                "classification_label": "tomato",
                "notes": "pot_tag=2T; packet_tag=2",
                "caption": "Heinz 9129 | tomato_02 | verified",
                "variety_name": "Heinz 9129",
                "species_common_name": "Heinz 9129",
                "labeling_method": "manual_packet_label",
                "confidence": "0.99",
                "ocr_excerpt": "",
            },
        ]

        mapping_rows, report = mapper.build_mapping(rows, "2026-02-27", expected_pots=2)
        self.assertEqual(len(mapping_rows), 2)
        self.assertEqual(report["unique_pot_count"], 2)
        self.assertEqual(report["errors"], [])
        self.assertEqual(mapping_rows[0]["pot_id"], "1T")
        self.assertEqual(mapping_rows[1]["pot_id"], "2T")
        self.assertEqual(mapping_rows[0]["day_since_potting"], "3")
        self.assertEqual(mapping_rows[0]["experiment_day"], "3")

    def test_build_mapping_detects_duplicate_and_missing_pot(self):
        rows = [
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:00:00-08:00",
                "source_asset_id": "asset_1",
                "photo_url": "https://example.com/1.jpg",
                "classification_label": "tomato",
                "notes": "pot_tag=1T",
                "caption": "Taxi | tomato_01 | verified",
                "variety_name": "Taxi",
                "species_common_name": "Taxi",
                "labeling_method": "manual_packet_label",
                "confidence": "0.99",
                "ocr_excerpt": "",
            },
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:01:00-08:00",
                "source_asset_id": "asset_2",
                "photo_url": "https://example.com/2.jpg",
                "classification_label": "tomato",
                "notes": "pot_tag=1T",
                "caption": "Heinz 9129 | tomato_02 | verified",
                "variety_name": "Heinz 9129",
                "species_common_name": "Heinz 9129",
                "labeling_method": "manual_packet_label",
                "confidence": "0.99",
                "ocr_excerpt": "",
            },
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:02:00-08:00",
                "source_asset_id": "asset_3",
                "photo_url": "https://example.com/3.jpg",
                "classification_label": "tomato",
                "notes": "",
                "caption": "Azoychka | verified",
                "variety_name": "Azoychka",
                "species_common_name": "Azoychka",
                "labeling_method": "manual_packet_label",
                "confidence": "0.99",
                "ocr_excerpt": "",
            },
        ]

        mapping_rows, report = mapper.build_mapping(
            rows,
            "2026-02-27",
            expected_pots=3,
            assume_sequential_pot_ids=False,
            tomato_only_run=True,
        )
        self.assertEqual(len(mapping_rows), 3)
        self.assertTrue(any("missing pot_id" in err for err in report["errors"]))
        self.assertTrue(any("duplicate rows" in err for err in report["errors"]))
        self.assertTrue(
            any("unique_pot_count" in err for err in report["errors"]),
            report["errors"],
        )

    def test_build_historical_variety_lookup_from_prior_run(self):
        rows = [
            {
                "capture_date": "2026-02-25",
                "classification_label": "tomato",
                "caption": "Taxi | tomato_13 | verified",
                "variety_name": "Taxi",
                "species_common_name": "Taxi",
            },
            {
                "capture_date": "2026-02-27",
                "classification_label": "unknown",
                "caption": "",
                "variety_name": "",
                "species_common_name": "",
            },
        ]
        lookup = mapper.build_historical_variety_lookup(rows, "2026-02-27")
        self.assertEqual(lookup.get(13), "Taxi")

    def test_load_series_variety_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "series_map.csv"
            path.write_text(
                "series_number,variety_name\n"
                "1,San Francisco Fog\n"
                "3,Iles Yellow Latvian\n",
                encoding="utf-8",
            )
            mapping = mapper.load_series_variety_map(path)
            self.assertEqual(mapping[1], "San Francisco Fog")
            self.assertEqual(mapping[3], "Iles Yellow Latvian")

    def test_load_pot_series_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pot_overrides.csv"
            path.write_text(
                "pot_id,series_number\n"
                "4T,1\n"
                "27t,4\n",
                encoding="utf-8",
            )
            mapping = mapper.load_pot_series_overrides(path)
            self.assertEqual(mapping["4T"], 1)
            self.assertEqual(mapping["27T"], 4)

    def test_build_mapping_applies_manual_pot_series_override(self):
        rows = [
            {
                "capture_date": "2026-02-27",
                "captured_at": "2026-02-27T16:02:00-08:00",
                "source_asset_id": "asset_30",
                "photo_url": "https://example.com/30.jpg",
                "classification_label": "unknown",
                "notes": "",
                "caption": "",
                "variety_name": "",
                "species_common_name": "unknown",
                "labeling_method": "ocr_unresolved",
                "confidence": "0.4",
                "ocr_excerpt": "",
            },
        ]
        mapping_rows, report = mapper.build_mapping(
            rows,
            "2026-02-27",
            expected_pots=1,
            assume_sequential_pot_ids=True,
            tomato_only_run=True,
            series_variety_map={1: "San Francisco Fog"},
            pot_series_overrides={"1T": 1},
        )
        self.assertEqual(report["errors"], [])
        self.assertEqual(mapping_rows[0]["pot_id"], "1T")
        self.assertEqual(mapping_rows[0]["packet_number"], "1")
        self.assertEqual(mapping_rows[0]["variety_name"], "San Francisco Fog")
        self.assertIn(
            "series_from_manual_pot_override",
            mapping_rows[0]["mapping_note"],
        )


if __name__ == "__main__":
    unittest.main()
