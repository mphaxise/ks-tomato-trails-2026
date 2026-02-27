import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import label_non_tomato_from_images as labeler  # noqa: E402


class LabelNonTomatoFromImagesTests(unittest.TestCase):
    def test_classify_non_tomato_collards(self):
        result = labeler.classify_from_text("Hybrid Collards FLASH F1 Brassica oleracea")
        self.assertEqual(result["classification_label"], "non_tomato")
        self.assertEqual(result["species_common_name"], "Collards")

    def test_classify_tomato_keyword(self):
        result = labeler.classify_from_text("Sunset Tomato")
        self.assertEqual(result["classification_label"], "tomato")
        self.assertEqual(result["species_scientific_name"], "Solanum lycopersicum")

    def test_classify_unknown(self):
        result = labeler.classify_from_text("label unreadable")
        self.assertEqual(result["classification_label"], "unknown")

    def test_classify_non_tomato_leek_keyword(self):
        result = labeler.classify_from_text("TADORNA OG Allium porrum")
        self.assertEqual(result["classification_label"], "non_tomato")
        self.assertEqual(result["species_common_name"], "Leek")

    def test_classify_non_tomato_red_cabbage_keyword(self):
        result = labeler.classify_from_text("Hybrid Storage Red Cabbage RUBY PERFECTION")
        self.assertEqual(result["classification_label"], "non_tomato")
        self.assertEqual(result["species_common_name"], "Red Cabbage")

    def test_manual_override_updates_output_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            overrides_csv = Path(tmp) / "overrides.csv"
            overrides_csv.write_text(
                (
                    "row_index,source_asset_id,classification_label,species_common_name,"
                    "variety_name,species_scientific_name,specific_note,weather_hypothesis,expected_harvest_window,"
                    "confidence,labeling_method,caption,notes_append\n"
                    "3,asset_3,tomato,Sasha Altai,Sasha Altai,Solanum lycopersicum,"
                    "Early cool-climate heirloom,Performs well in mild weather,~ 65-80 days,"
                    "0.99,manual_packet_label,Sasha Altai | tomato_03 | verified,"
                    "Manual packet-label verification from photo.\n"
                ),
                encoding="utf-8",
            )

            overrides = labeler.load_manual_overrides(overrides_csv)
            row = {
                "classification_label": "unknown",
                "species_common_name": "unknown",
                "variety_name": "",
                "species_scientific_name": "unknown",
                "specific_note": "",
                "weather_hypothesis": "",
                "expected_harvest_window": "",
                "confidence": "0.4",
                "labeling_method": "ocr_unresolved",
                "caption": "",
                "notes": "",
                "ocr_excerpt": "",
            }

            updated = labeler.apply_manual_override(3, "asset_3", row, overrides)
            self.assertEqual(updated["classification_label"], "tomato")
            self.assertEqual(updated["species_common_name"], "Sasha Altai")
            self.assertEqual(updated["variety_name"], "Sasha Altai")
            self.assertEqual(updated["labeling_method"], "manual_packet_label")
            self.assertIn("cool-climate", updated["specific_note"])
            self.assertIn("Manual packet-label verification", updated["notes"])


if __name__ == "__main__":
    unittest.main()
