import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_new_batch_label_suggester as suggester  # noqa: E402


class V17NewBatchLabelSuggesterTests(unittest.TestCase):
    def test_confidence_tier(self):
        self.assertEqual(suggester.confidence_tier(0.09), "high")
        self.assertEqual(suggester.confidence_tier(0.05), "medium")
        self.assertEqual(suggester.confidence_tier(0.02), "low")

    def test_confidence_value_clamped(self):
        self.assertEqual(suggester.confidence_value(0.0), 0.55)
        self.assertLessEqual(suggester.confidence_value(1.0), 0.95)

    def test_build_override_seed_rows_filters_by_margin(self):
        rows = [
            {
                "row_index": 1,
                "source_asset_id": "asset1",
                "predicted_classification_label": "tomato",
                "predicted_species_common_name": "Tomato",
                "predicted_variety_name": "Taxi",
                "predicted_species_scientific_name": "Solanum lycopersicum",
                "tomato_similarity": 0.8,
                "non_tomato_similarity": 0.6,
                "margin": 0.2,
            },
            {
                "row_index": 2,
                "source_asset_id": "asset2",
                "predicted_classification_label": "non_tomato",
                "predicted_species_common_name": "Spinach",
                "predicted_variety_name": "Spinach",
                "predicted_species_scientific_name": "Spinacia oleracea",
                "tomato_similarity": 0.7,
                "non_tomato_similarity": 0.72,
                "margin": 0.02,
            },
        ]
        seed = suggester.build_override_seed_rows(rows, min_margin=0.05)
        self.assertEqual(len(seed), 1)
        self.assertEqual(seed[0]["row_index"], 1)


if __name__ == "__main__":
    unittest.main()
