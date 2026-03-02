#!/usr/bin/env python3
"""Sprint 2 SW-3: dHash-based near-duplicate clustering for intake reduction."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image


CAPTION_ID_RE = re.compile(r"\b(?:tomato|non_tomato)[_\s-]*([0-9]{1,3})\b", re.IGNORECASE)
IMAGE_NAME_RE = re.compile(r"^(?P<row>[0-9]{1,4})_(?P<asset>AF1Qip[0-9A-Za-z_-]+)\.(jpg|jpeg|png)$", re.IGNORECASE)

HASH_FIELDS = [
    "row_index",
    "source_asset_id",
    "image_path",
    "capture_date",
    "classification_label",
    "variety_name",
    "caption_true_pot_id",
    "dhash_hex",
]

CLUSTER_FIELDS = [
    "threshold",
    "cluster_id",
    "cluster_size",
    "member_rank",
    "is_representative",
    "distance_to_representative",
    "row_index",
    "source_asset_id",
    "image_path",
    "capture_date",
    "classification_label",
    "variety_name",
    "caption_true_pot_id",
    "dhash_hex",
    "caption_truth_conflict",
    "cross_date_cluster",
]


@dataclass(frozen=True)
class ImageRow:
    row_index: int
    source_asset_id: str
    image_path: Path
    capture_date: str
    classification_label: str
    variety_name: str
    caption_true_pot_id: str
    dhash: int

    @property
    def dhash_hex(self) -> str:
        return f"{self.dhash:016x}"


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def normalize_pot_id(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]", "", (value or "").strip()).upper()
    if not cleaned:
        return ""
    matched = re.fullmatch(r"([0-9]{1,3})T?", cleaned)
    if not matched:
        return ""
    number = int(matched.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def caption_truth_pot_id(caption: str) -> str:
    matched = CAPTION_ID_RE.search(caption or "")
    if not matched:
        return ""
    return normalize_pot_id(matched.group(1))


def parse_image_filename(path: Path) -> Tuple[int, str] | None:
    matched = IMAGE_NAME_RE.fullmatch(path.name)
    if not matched:
        return None
    row_index = int(matched.group("row"))
    source_asset_id = matched.group("asset")
    return row_index, source_asset_id


def dhash(image_path: Path, hash_size: int = 8) -> int:
    with Image.open(image_path) as image:
        gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())

    result = 0
    width = hash_size + 1
    for y in range(hash_size):
        row_start = y * width
        for x in range(hash_size):
            left = pixels[row_start + x]
            right = pixels[row_start + x + 1]
            result <<= 1
            if left > right:
                result |= 1
    return result


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def build_image_rows(input_csv: Path, image_dir: Path) -> List[ImageRow]:
    labeled_rows = read_csv_rows(input_csv)
    by_key: Dict[Tuple[int, str], Dict[str, str]] = {}
    for idx, row in enumerate(labeled_rows, start=1):
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue
        by_key[(idx, source_asset_id)] = row

    image_rows: List[ImageRow] = []
    for path in sorted(image_dir.glob("*")):
        if not path.is_file():
            continue
        parsed = parse_image_filename(path)
        if parsed is None:
            continue
        row_index, source_asset_id = parsed
        meta = by_key.get((row_index, source_asset_id), {})
        caption_true = caption_truth_pot_id((meta.get("caption", "") or "").strip())
        image_rows.append(
            ImageRow(
                row_index=row_index,
                source_asset_id=source_asset_id,
                image_path=path,
                capture_date=(meta.get("capture_date", "") or "").strip(),
                classification_label=(meta.get("classification_label", "") or "").strip(),
                variety_name=(meta.get("variety_name", "") or "").strip(),
                caption_true_pot_id=caption_true,
                dhash=dhash(path),
            )
        )

    if not image_rows:
        raise ValueError(f"No images found in {image_dir} matching <row>_<source_asset_id>.* pattern.")
    return image_rows


def cluster_hashes(rows: Sequence[ImageRow], threshold: int) -> List[List[int]]:
    n = len(rows)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            if hamming_distance(rows[i].dhash, rows[j].dhash) <= threshold:
                union(i, j)

    groups: Dict[int, List[int]] = defaultdict(list)
    for idx in range(n):
        groups[find(idx)].append(idx)

    clusters = [sorted(indices, key=lambda pos: rows[pos].row_index) for indices in groups.values()]
    clusters.sort(key=lambda indices: (rows[indices[0]].row_index, rows[indices[0]].source_asset_id))
    return clusters


def cluster_conflict_flags(rows: Sequence[ImageRow], member_indices: Sequence[int]) -> Tuple[int, int]:
    caption_truths = {rows[idx].caption_true_pot_id for idx in member_indices if rows[idx].caption_true_pot_id}
    capture_dates = {rows[idx].capture_date for idx in member_indices if rows[idx].capture_date}
    truth_conflict = int(len(caption_truths) > 1)
    cross_date = int(len(capture_dates) > 1)
    return truth_conflict, cross_date


def summarize_threshold(rows: Sequence[ImageRow], threshold: int) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    clusters = cluster_hashes(rows, threshold=threshold)
    cluster_rows: List[Dict[str, object]] = []
    truth_conflict_clusters = 0
    cross_date_clusters = 0

    for cluster_id, members in enumerate(clusters, start=1):
        representative = members[0]
        truth_conflict, cross_date = cluster_conflict_flags(rows, members)
        truth_conflict_clusters += truth_conflict
        cross_date_clusters += cross_date

        for rank, idx in enumerate(members, start=1):
            member = rows[idx]
            cluster_rows.append(
                {
                    "threshold": threshold,
                    "cluster_id": cluster_id,
                    "cluster_size": len(members),
                    "member_rank": rank,
                    "is_representative": int(idx == representative),
                    "distance_to_representative": hamming_distance(
                        rows[representative].dhash, member.dhash
                    ),
                    "row_index": member.row_index,
                    "source_asset_id": member.source_asset_id,
                    "image_path": str(member.image_path),
                    "capture_date": member.capture_date,
                    "classification_label": member.classification_label,
                    "variety_name": member.variety_name,
                    "caption_true_pot_id": member.caption_true_pot_id,
                    "dhash_hex": member.dhash_hex,
                    "caption_truth_conflict": truth_conflict,
                    "cross_date_cluster": cross_date,
                }
            )

    image_count = len(rows)
    cluster_count = len(clusters)
    merged_images = image_count - cluster_count
    reduction_ratio = (float(merged_images) / float(image_count)) if image_count else 0.0

    cluster_sizes = sorted((len(members) for members in clusters), reverse=True)
    cluster_size_counter = Counter(cluster_sizes)

    summary = {
        "threshold": threshold,
        "image_count": image_count,
        "cluster_count": cluster_count,
        "merged_images": merged_images,
        "workload_reduction_ratio": round(reduction_ratio, 4),
        "workload_reduction_pct": round(reduction_ratio * 100.0, 2),
        "singletons": cluster_size_counter.get(1, 0),
        "clusters_with_caption_truth_conflict": truth_conflict_clusters,
        "clusters_with_cross_date_members": cross_date_clusters,
        "largest_cluster_size": cluster_sizes[0] if cluster_sizes else 0,
    }
    return cluster_rows, summary


def choose_recommendation(threshold_summaries: Sequence[Dict[str, object]]) -> str:
    safe = [
        row
        for row in threshold_summaries
        if int(row.get("clusters_with_caption_truth_conflict", 0) or 0) == 0
    ]
    candidate_rows = safe if safe else list(threshold_summaries)
    if not candidate_rows:
        return ""
    candidate_rows.sort(
        key=lambda row: (
            float(row.get("workload_reduction_ratio", 0.0) or 0.0),
            -int(row.get("clusters_with_cross_date_members", 0) or 0),
        ),
        reverse=True,
    )
    return str(candidate_rows[0].get("threshold", ""))


def write_markdown(
    *,
    output_md: Path,
    input_csv: Path,
    image_dir: Path,
    thresholds: Sequence[int],
    threshold_summaries: Sequence[Dict[str, object]],
    recommended_threshold: str,
) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# V1.7 SW-3 dHash Dedup Probe",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Inputs",
        "",
        f"- Labeled CSV: `{input_csv}`",
        f"- Image directory: `{image_dir}`",
        f"- Thresholds tested: `{','.join(str(value) for value in thresholds)}`",
        "",
        "## Results",
        "",
        "| Threshold | Images | Clusters | Reduction % | Caption-Truth Conflicts | Cross-Date Clusters | Largest Cluster |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in threshold_summaries:
        lines.append(
            "| {threshold} | {image_count} | {cluster_count} | {workload_reduction_pct} | "
            "{clusters_with_caption_truth_conflict} | {clusters_with_cross_date_members} | {largest_cluster_size} |".format(
                **row
            )
        )

    best_reduction = 0.0
    for row in threshold_summaries:
        value = float(row.get("workload_reduction_ratio", 0.0) or 0.0)
        if value > best_reduction:
            best_reduction = value
    verdict = "adopt_candidate" if best_reduction >= 0.2 else "low_impact_hold"

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            (
                f"- Recommended threshold: `{recommended_threshold}` "
                "(max reduction with zero caption-truth conflicts when available)."
                if recommended_threshold
                else "- No recommendation generated (no summaries)."
            ),
            "",
            "## Interpretation",
            "",
            f"- Best observed reduction ratio: `{round(best_reduction, 4)}`",
            f"- SW-3 verdict: `{verdict}`",
            "",
            "## Outputs",
            "",
            "- `data/research/v1_7/sw3_dhash_image_hashes.csv`",
            "- `data/research/v1_7/sw3_dhash_clusters_threshold_*.csv`",
            "- `data/research/v1_7/sw3_dhash_summary.csv`",
            "- `data/research/v1_7/sw3_dhash_summary.json`",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SW-3 dHash dedup probe.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled CSV used for metadata lookup.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Image directory with files named <row_index>_<source_asset_id>.jpg.",
    )
    parser.add_argument(
        "--thresholds",
        default="5,8,12",
        help="Comma-separated Hamming thresholds.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/v1_7"),
        help="Output directory for SW-3 artifacts.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.7-SW3-DHASH-DEDUP.md"),
        help="Markdown report path.",
    )
    return parser


def parse_thresholds(value: str) -> List[int]:
    out: List[int] = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        number = int(stripped)
        if number < 0:
            continue
        out.append(number)
    if not out:
        raise ValueError("At least one valid threshold is required.")
    return sorted(set(out))


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    thresholds = parse_thresholds(args.thresholds)

    rows = build_image_rows(args.input_csv, args.image_dir)
    hash_rows = [
        {
            "row_index": row.row_index,
            "source_asset_id": row.source_asset_id,
            "image_path": str(row.image_path),
            "capture_date": row.capture_date,
            "classification_label": row.classification_label,
            "variety_name": row.variety_name,
            "caption_true_pot_id": row.caption_true_pot_id,
            "dhash_hex": row.dhash_hex,
        }
        for row in rows
    ]
    write_csv(args.output_dir / "sw3_dhash_image_hashes.csv", HASH_FIELDS, hash_rows)

    summary_rows: List[Dict[str, object]] = []
    for threshold in thresholds:
        cluster_rows, summary = summarize_threshold(rows, threshold=threshold)
        write_csv(
            args.output_dir / f"sw3_dhash_clusters_threshold_{threshold}.csv",
            CLUSTER_FIELDS,
            cluster_rows,
        )
        summary_rows.append(summary)

    summary_fields = [
        "threshold",
        "image_count",
        "cluster_count",
        "merged_images",
        "workload_reduction_ratio",
        "workload_reduction_pct",
        "singletons",
        "clusters_with_caption_truth_conflict",
        "clusters_with_cross_date_members",
        "largest_cluster_size",
    ]
    write_csv(args.output_dir / "sw3_dhash_summary.csv", summary_fields, summary_rows)
    recommended_threshold = choose_recommendation(summary_rows)
    summary_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(args.input_csv),
        "image_dir": str(args.image_dir),
        "thresholds": thresholds,
        "recommended_threshold": recommended_threshold,
        "rows": summary_rows,
    }
    write_json(args.output_dir / "sw3_dhash_summary.json", summary_payload)
    write_markdown(
        output_md=args.output_md,
        input_csv=args.input_csv,
        image_dir=args.image_dir,
        thresholds=thresholds,
        threshold_summaries=summary_rows,
        recommended_threshold=recommended_threshold,
    )

    print(f"input_csv={args.input_csv}")
    print(f"image_dir={args.image_dir}")
    print(f"images={len(rows)}")
    print(f"thresholds={','.join(str(value) for value in thresholds)}")
    print(f"recommended_threshold={recommended_threshold}")
    print(f"output_dir={args.output_dir}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
