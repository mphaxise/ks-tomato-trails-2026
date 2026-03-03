#!/usr/bin/env python3
"""Batch-resolve multiple quick seed annotation JSON files."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from v18_quick_seed_pair_resolver import (
    load_pot_series_map,
    load_series_map,
    read_json,
    resolve_seed,
    write_json,
)


def is_quick_seed_payload(payload: Dict[str, object]) -> bool:
    boxes = payload.get("boxes", [])
    source_asset_id = str(payload.get("source_asset_id", "") or "").strip()
    capture_date = str(payload.get("capture_date", "") or "").strip()
    version = str(payload.get("version", "") or "").strip()
    if not isinstance(boxes, list):
        return False
    if not source_asset_id:
        return False
    if not capture_date:
        return False
    if version and "quick-single-photo" not in version:
        return False
    return True


def discover_seed_paths(seed_dirs: List[Path], explicit_jsons: List[Path]) -> List[Path]:
    discovered: List[Path] = []
    for p in explicit_jsons:
        if p.exists() and p.is_file():
            discovered.append(p)
    for seed_dir in seed_dirs:
        if not seed_dir.exists():
            continue
        for p in sorted(seed_dir.rglob("quick_seed_*.json")):
            if p.is_file():
                discovered.append(p)
    dedup: List[Path] = []
    seen = set()
    for p in discovered:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        dedup.append(p)
    return dedup


def summarize_batch(
    seed_paths: List[Path],
    pot_series_map: Dict[str, int],
    series_map: Dict[int, str],
) -> Dict[str, object]:
    per_seed: List[Dict[str, object]] = []
    review_reason_counts: Counter[str] = Counter()
    evidence_type_counts: Counter[str] = Counter()

    total_rows = 0
    total_needs_review = 0

    for path in seed_paths:
        payload = read_json(path)
        if not is_quick_seed_payload(payload):
            continue
        resolution = resolve_seed(
            payload, pot_series_map=pot_series_map, series_map=series_map
        )
        total_rows += int(resolution.get("total_rows", 0))
        total_needs_review += int(resolution.get("needs_review_count", 0))

        this_reasons = resolution.get("review_reason_counts", {})
        if isinstance(this_reasons, dict):
            for reason, count in this_reasons.items():
                review_reason_counts[str(reason)] += int(count)

        this_evidence = resolution.get("evidence_type_counts", {})
        if isinstance(this_evidence, dict):
            for key, count in this_evidence.items():
                evidence_type_counts[str(key)] += int(count)

        per_seed.append(
            {
                "seed_json_path": str(path),
                "capture_date": resolution.get("capture_date", ""),
                "row_index": resolution.get("row_index", ""),
                "source_asset_id": resolution.get("source_asset_id", ""),
                "photo_url": resolution.get("photo_url", ""),
                "total_rows": resolution.get("total_rows", 0),
                "pot_boxes": resolution.get("pot_boxes", 0),
                "varietal_boxes": resolution.get("varietal_boxes", 0),
                "auto_resolved_count": resolution.get("auto_resolved_count", 0),
                "needs_review_count": resolution.get("needs_review_count", 0),
                "review_reason_counts": this_reasons,
                "evidence_type_counts": this_evidence,
            }
        )

    per_seed.sort(
        key=lambda row: (
            str(row.get("capture_date", "")),
            int(str(row.get("row_index", "0") or "0")),
            str(row.get("source_asset_id", "")),
        )
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_files_discovered": len(seed_paths),
        "seed_files_processed": len(per_seed),
        "total_rows": total_rows,
        "total_needs_review": total_needs_review,
        "total_auto_resolved": total_rows - total_needs_review,
        "review_reason_counts": dict(review_reason_counts),
        "evidence_type_counts": dict(evidence_type_counts),
        "per_seed": per_seed,
    }


def build_markdown(summary: Dict[str, object], output_json: Path) -> str:
    per_seed = summary.get("per_seed", [])
    if not isinstance(per_seed, list):
        per_seed = []
    review_reason_counts = summary.get("review_reason_counts", {})
    if not isinstance(review_reason_counts, dict):
        review_reason_counts = {}
    evidence_type_counts = summary.get("evidence_type_counts", {})
    if not isinstance(evidence_type_counts, dict):
        evidence_type_counts = {}

    lines = [
        "# V1.8 Quick Seed Batch Summary",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        f"Output JSON: `{output_json}`",
        "",
        "## Totals",
        "",
        f"- discovered: `{summary.get('seed_files_discovered', 0)}`",
        f"- processed: `{summary.get('seed_files_processed', 0)}`",
        f"- total rows: `{summary.get('total_rows', 0)}`",
        f"- auto resolved: `{summary.get('total_auto_resolved', 0)}`",
        f"- needs review: `{summary.get('total_needs_review', 0)}`",
        "",
        "## Review Reasons",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]

    if review_reason_counts:
        for key, value in sorted(review_reason_counts.items()):
            lines.append(f"| `{key}` | {value} |")
    else:
        lines.append("| _(none)_ | 0 |")

    lines.extend(["", "## Evidence Types", "", "| Type | Count |", "|---|---:|"])
    for key, value in sorted(evidence_type_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Per-Seed",
            "",
            "| capture_date | row_index | source_asset_id | rows | auto | review |",
            "|---|---:|---|---:|---:|---:|",
        ]
    )

    for row in per_seed:
        lines.append(
            "| `{capture_date}` | `{row_index}` | `{source_asset_id}` | {total_rows} | {auto_resolved_count} | {needs_review_count} |".format(
                capture_date=row.get("capture_date", ""),
                row_index=row.get("row_index", ""),
                source_asset_id=row.get("source_asset_id", ""),
                total_rows=row.get("total_rows", 0),
                auto_resolved_count=row.get("auto_resolved_count", 0),
                needs_review_count=row.get("needs_review_count", 0),
            )
        )

    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run quick-seed pair resolution over multiple seed JSON exports."
    )
    parser.add_argument(
        "--seed-dir",
        action="append",
        type=Path,
        default=[],
        help="Directory to recursively scan for quick_seed_*.json files.",
    )
    parser.add_argument(
        "--seed-json",
        action="append",
        type=Path,
        default=[],
        help="Explicit quick_seed JSON file path. Can be used multiple times.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
    )
    parser.add_argument(
        "--pot-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
    )
    parser.add_argument(
        "--baseline-mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_8/quick_seed_batch_summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.8-QUICK-SEED-BATCH-SUMMARY.md"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    seed_paths = discover_seed_paths(args.seed_dir, args.seed_json)
    series_map = load_series_map(args.series_map_csv)
    pot_series_map = load_pot_series_map(args.pot_overrides_csv, args.baseline_mapping_csv)

    summary = summarize_batch(seed_paths, pot_series_map=pot_series_map, series_map=series_map)
    write_json(args.output_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(summary, args.output_json), encoding="utf-8")

    print(f"discovered={summary['seed_files_discovered']}")
    print(f"processed={summary['seed_files_processed']}")
    print(f"total_rows={summary['total_rows']}")
    print(f"total_needs_review={summary['total_needs_review']}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
