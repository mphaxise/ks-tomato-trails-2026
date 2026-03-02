import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v17_sw3_dhash_dedup as sw3  # noqa: E402


class V17Sw3DhashDedupTests(unittest.TestCase):
    def test_parse_image_filename(self):
        parsed = sw3.parse_image_filename(Path("09_AF1QipPBKSwU3sjNcQQSkKhJlcDXrMPgsJUsYU4qxJBM.jpg"))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], 9)
        self.assertEqual(parsed[1], "AF1QipPBKSwU3sjNcQQSkKhJlcDXrMPgsJUsYU4qxJBM")

    def test_hamming_distance(self):
        self.assertEqual(sw3.hamming_distance(0b0000, 0b0000), 0)
        self.assertEqual(sw3.hamming_distance(0b1111, 0b0000), 4)
        self.assertEqual(sw3.hamming_distance(0b1010, 0b0011), 2)

    def test_cluster_hashes_threshold(self):
        rows = [
            sw3.ImageRow(1, "A1", Path("a1.jpg"), "2026-03-01", "unknown", "", "", 0b0000),
            sw3.ImageRow(2, "A2", Path("a2.jpg"), "2026-03-01", "unknown", "", "", 0b0001),
            sw3.ImageRow(3, "A3", Path("a3.jpg"), "2026-03-01", "unknown", "", "", 0b1111),
        ]
        clusters = sw3.cluster_hashes(rows, threshold=1)
        sizes = sorted(len(cluster) for cluster in clusters)
        self.assertEqual(sizes, [1, 2])

    def test_choose_recommendation_prefers_safe_high_reduction(self):
        rows = [
            {"threshold": 5, "workload_reduction_ratio": 0.10, "clusters_with_caption_truth_conflict": 0, "clusters_with_cross_date_members": 0},
            {"threshold": 8, "workload_reduction_ratio": 0.20, "clusters_with_caption_truth_conflict": 1, "clusters_with_cross_date_members": 0},
            {"threshold": 12, "workload_reduction_ratio": 0.15, "clusters_with_caption_truth_conflict": 0, "clusters_with_cross_date_members": 1},
        ]
        self.assertEqual(sw3.choose_recommendation(rows), "12")


if __name__ == "__main__":
    unittest.main()
