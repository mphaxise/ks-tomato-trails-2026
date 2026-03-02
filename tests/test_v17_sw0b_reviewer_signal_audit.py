import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw0b_reviewer_signal_audit as sw0b  # noqa: E402


class V17Sw0bReviewerSignalAuditTests(unittest.TestCase):
    def test_parse_pot_number(self):
        self.assertEqual(sw0b.parse_pot_number("12T"), 12)
        self.assertEqual(sw0b.parse_pot_number("x"), 0)

    def test_classify_type_iii_when_no_matches(self):
        tier, reason = sw0b.classify_signal_tier(
            matched_variant_count=0,
            suggested_pot_id="9T",
            ensemble_numbers_detected="9,12",
        )
        self.assertEqual(tier, "TYPE_III")
        self.assertIn("placeholder", reason)

    def test_classify_type_i_when_suggested_number_detected(self):
        tier, _ = sw0b.classify_signal_tier(
            matched_variant_count=1,
            suggested_pot_id="9T",
            ensemble_numbers_detected="2,9,12",
        )
        self.assertEqual(tier, "TYPE_I")

    def test_classify_type_ii_when_ocr_does_not_support_suggestion(self):
        tier, _ = sw0b.classify_signal_tier(
            matched_variant_count=2,
            suggested_pot_id="9T",
            ensemble_numbers_detected="2,12",
        )
        self.assertEqual(tier, "TYPE_II")


if __name__ == "__main__":
    unittest.main()
