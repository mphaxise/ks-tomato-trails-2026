import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_new_batch_reviewer_page as builder  # noqa: E402


class BuildNewBatchReviewerPageTests(unittest.TestCase):
    def test_build_page_contains_export_and_filters(self):
        rows = [
            {
                "row_index": "124",
                "capture_date": "2026-03-01",
                "source_asset_id": "asset1",
                "photo_url": "https://example.com/photo.jpg",
                "predicted_classification_label": "non_tomato",
                "predicted_variety_name": "Spinach",
                "tomato_similarity": "0.5",
                "non_tomato_similarity": "0.7",
                "margin": "0.2",
                "confidence_tier": "high",
            }
        ]
        page = builder.build_page(Path("queue.csv"), rows)
        self.assertIn("New Batch Reviewer", page)
        self.assertIn("Export Overrides CSV", page)
        self.assertIn("id=\"date-filter\"", page)
        self.assertIn("id=\"pred-filter\"", page)


if __name__ == "__main__":
    unittest.main()
