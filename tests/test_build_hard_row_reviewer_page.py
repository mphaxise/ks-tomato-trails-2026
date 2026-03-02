import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_hard_row_reviewer_page as reviewer_builder  # noqa: E402


class BuildHardRowReviewerPageTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(reviewer_builder.slugify("2026-03-01"), "2026_03_01")
        self.assertEqual(reviewer_builder.slugify("AB cd"), "ab_cd")

    def test_build_summary(self):
        rows = [
            {"run_date": "2026-02-28", "matched_variant_count": "0", "signal_tier": "TYPE_III"},
            {"run_date": "2026-02-28", "matched_variant_count": "1", "signal_tier": "TYPE_I"},
            {"run_date": "2026-03-01", "matched_variant_count": "0", "signal_tier": "TYPE_III"},
        ]
        summary = reviewer_builder.build_summary(rows)
        self.assertEqual(summary["total_rows"], 3)
        self.assertEqual(summary["run_counts"]["2026-02-28"], 2)
        self.assertEqual(summary["variant_match_counts"]["0"], 2)
        self.assertEqual(summary["signal_tier_counts"]["TYPE_III"], 2)

    def test_classify_signal_tier_prefers_no_match_variants(self):
        tier, label, rank = reviewer_builder.classify_signal_tier(
            matched_variant_count=0,
            suggested_pot_id="8T",
            ensemble_numbers_detected="8,12",
        )
        self.assertEqual((tier, label, rank), ("TYPE_III", "No signal - sequential guess", 3))

    def test_classify_signal_tier_ocr_match(self):
        tier, label, rank = reviewer_builder.classify_signal_tier(
            matched_variant_count=2,
            suggested_pot_id="8T",
            ensemble_numbers_detected="2,8,12",
        )
        self.assertEqual((tier, label, rank), ("TYPE_I", "OCR match", 1))

    def test_classify_signal_tier_weak_ocr(self):
        tier, label, rank = reviewer_builder.classify_signal_tier(
            matched_variant_count=1,
            suggested_pot_id="8T",
            ensemble_numbers_detected="2,12",
        )
        self.assertEqual((tier, label, rank), ("TYPE_II", "Weak OCR", 2))

    def test_build_page_contains_controls(self):
        rows = [
            {
                "run_date": "2026-03-01",
                "row_index": "92",
                "source_asset_id": "asset1",
                "suggested_pot_id": "1T",
                "suggested_variety_name": "Taxi",
                "photo_url": "https://example.com/photo.jpg",
                "matched_variant_count": "0",
                "ensemble_numbers_detected": "2,4",
                "full_crop_url": "https://example.com/full.jpg",
                "center_crop_url": "https://example.com/center.jpg",
                "label_crop_url": "https://example.com/label.jpg",
                "signal_tier": "TYPE_III",
                "signal_label": "No signal - sequential guess",
                "signal_rank": "3",
                "label_ocr_boxes": [],
            }
        ]
        page = reviewer_builder.build_page(Path("queue.csv"), rows, reviewer_builder.build_summary(rows))
        self.assertIn("Hard Row Reviewer (OCR Recovery Queue)", page)
        self.assertIn("Export Reviewed CSV", page)
        self.assertIn("data-field='confirmed_pot_id'", page)
        self.assertIn("data-open-lightbox='true'", page)
        self.assertIn("No basis - cannot verify from this photo", page)
        self.assertIn("No signal - sequential guess", page)
        self.assertIn("id=\"signal-filter\"", page)


if __name__ == "__main__":
    unittest.main()
