import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_experiment_trails_label_editor_page as editor_builder  # noqa: E402
import build_experiment_trails_page as view_builder  # noqa: E402


SAMPLE_ROWS = [
    {
        "capture_date": "2026-02-27",
        "classification_label": "tomato",
        "source_asset_id": "asset_1",
        "photo_url": "https://example.com/1.jpg",
        "species_common_name": "Tomato",
        "variety_name": "Taxi",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": "",
        "weather_hypothesis": "",
        "expected_harvest_window": "",
        "confidence": "0.9",
        "labeling_method": "manual",
        "caption": "Taxi",
    }
]


class BuildExperimentTrailsPagesTests(unittest.TestCase):
    def test_view_page_uses_constrained_lightbox_layout(self):
        page = view_builder.build_page(SAMPLE_ROWS, Path("sample.csv"))
        self.assertIn("height: min(94vh, 940px);", page)
        self.assertIn("grid-template-rows: minmax(0, 1fr) auto;", page)
        self.assertIn("max-height: min(50vh, 420px);", page)

    def test_label_editor_uses_stable_saved_row_mapping(self):
        page = editor_builder.build_page(SAMPLE_ROWS, Path("sample.csv"))
        self.assertIn("height: min(94vh, 940px);", page)
        self.assertIn("rows_by_asset", page)
        self.assertIn("rows_by_index", page)
        self.assertIn("assetId ? rowsByAsset[assetId] : null", page)


if __name__ == "__main__":
    unittest.main()
