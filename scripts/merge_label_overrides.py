#!/usr/bin/env python3
"""Merge web-exported label correction CSV into the canonical overrides CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

OVERRIDE_FIELDS = [
    "row_index",
    "source_asset_id",
    "classification_label",
    "species_common_name",
    "variety_name",
    "species_scientific_name",
    "specific_note",
    "weather_hypothesis",
    "expected_harvest_window",
    "confidence",
    "labeling_method",
    "caption",
    "notes_append",
    "ocr_excerpt",
]


def normalize_row(raw: Dict[str, str]) -> Dict[str, str]:
    return {field: (raw.get(field, "") or "").strip() for field in OVERRIDE_FIELDS}


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(raw) for raw in reader]


def row_key(row: Dict[str, str]) -> Tuple[int, str]:
    row_index_text = (row.get("row_index") or "").strip()
    try:
        row_index = int(row_index_text)
    except ValueError:
        row_index = 0
    source_asset_id = (row.get("source_asset_id") or "").strip()
    return row_index, source_asset_id


def merge_rows(
    base_rows: List[Dict[str, str]], incoming_rows: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], int, int]:
    merged: Dict[Tuple[int, str], Dict[str, str]] = {}
    for row in base_rows:
        merged[row_key(row)] = row

    inserted = 0
    updated = 0
    for row in incoming_rows:
        key = row_key(row)
        if key in merged:
            merged[key] = row
            updated += 1
        else:
            merged[key] = row
            inserted += 1

    ordered = [
        merged[key]
        for key in sorted(
            merged.keys(), key=lambda item: (item[0], item[1])
        )
    ]
    return ordered, inserted, updated


def write_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OVERRIDE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge a web-exported label overrides CSV into manual_label_overrides_v1.csv"
    )
    parser.add_argument(
        "--incoming",
        required=True,
        type=Path,
        help="Incoming corrections CSV exported from the label editor page",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("data/intake/google_photos/manual_label_overrides_v1.csv"),
        help="Canonical overrides CSV to update",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/intake/google_photos/manual_label_overrides_v1.csv"),
        help="Output merged CSV path",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.incoming.exists():
        raise SystemExit(f"incoming_not_found={args.incoming}")

    base_rows = load_csv_rows(args.base)
    incoming_rows = load_csv_rows(args.incoming)

    merged_rows, inserted, updated = merge_rows(base_rows, incoming_rows)
    write_rows(args.output, merged_rows)

    print(f"base_rows={len(base_rows)}")
    print(f"incoming_rows={len(incoming_rows)}")
    print(f"inserted={inserted}")
    print(f"updated={updated}")
    print(f"merged_rows={len(merged_rows)}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
