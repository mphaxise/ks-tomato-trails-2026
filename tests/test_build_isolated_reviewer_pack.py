import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_isolated_reviewer_pack as reviewer_pack  # noqa: E402


class BuildIsolatedReviewerPackTests(unittest.TestCase):
    def test_resolve_latest_run_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            labeled_csv = Path(tmp) / "labeled.csv"
            with labeled_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["capture_date"])
                writer.writeheader()
                writer.writerow({"capture_date": "2026-03-04"})
                writer.writerow({"capture_date": "2026-03-06"})
                writer.writerow({"capture_date": "2026-03-05"})

            self.assertEqual(
                reviewer_pack.resolve_latest_run_date(labeled_csv),
                "2026-03-06",
            )

    def test_filter_queue_rows_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_csv = Path(tmp) / "queue.csv"
            filtered_csv = Path(tmp) / "filtered.csv"
            fieldnames = [
                "run_date",
                "matched_variant_count",
                "ensemble_numbers_detected",
            ]
            with queue_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(
                    {
                        "run_date": "2026-03-06",
                        "matched_variant_count": "0",
                        "ensemble_numbers_detected": "2,4,7",
                    }
                )
                writer.writerow(
                    {
                        "run_date": "2026-03-06",
                        "matched_variant_count": "1",
                        "ensemble_numbers_detected": "5",
                    }
                )
                writer.writerow(
                    {
                        "run_date": "2026-03-05",
                        "matched_variant_count": "0",
                        "ensemble_numbers_detected": "",
                    }
                )

            rows = reviewer_pack.filter_queue_rows(
                queue_csv=queue_csv,
                run_date="2026-03-06",
                output_csv=filtered_csv,
            )
            summary = reviewer_pack.summarize_queue_rows(rows)

            self.assertEqual(len(rows), 2)
            self.assertTrue(filtered_csv.exists())
            self.assertEqual(summary["rows_total"], 2)
            self.assertEqual(summary["signal_tier_counts"]["weak_ocr"], 1)
            self.assertEqual(summary["signal_tier_counts"]["ocr_match"], 1)

    def test_write_root_index_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            pack_dir = output_root / "reviewer_pack_2026_03_06"
            reviewer_html = pack_dir / "reviewer_page" / "index.html"
            summary_path = pack_dir / "summary.json"
            reviewer_html.parent.mkdir(parents=True, exist_ok=True)
            reviewer_html.write_text("<html></html>", encoding="utf-8")
            summary_path.write_text(
                '{"run_date":"2026-03-06","rows_total":27,"signal_tier_counts":{"weak_ocr":27},"reviewer_html":"'
                + str(reviewer_html)
                + '"}',
                encoding="utf-8",
            )

            outputs = reviewer_pack.write_root_index(output_root)
            manifest_text = outputs["manifest"].read_text(encoding="utf-8")
            index_text = outputs["index"].read_text(encoding="utf-8")

            self.assertIn("2026-03-06", manifest_text)
            self.assertIn("Isolated Reviewer Packs", index_text)
            self.assertIn("2026-03-06", index_text)
            self.assertIn("reviewer_pack_2026_03_06/reviewer_page/index.html", index_text)


if __name__ == "__main__":
    unittest.main()
