#!/usr/bin/env python3
"""Merge exported manual two-run tagger CSV into a canonical overrides CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

CANONICAL_FIELDS = [
    "run_date",
    "row_index",
    "source_asset_id",
    "photo_url",
    "suggested_pot_id",
    "suggested_varietal_id",
    "confirmed_pot_id",
    "confirmed_varietal_id",
    "reviewed",
    "notes",
    "last_edited_at",
    "imported_at_utc",
    "source_file",
]


def normalize_text(value: str) -> str:
    return (value or "").strip()


def parse_int(value: str) -> int:
    try:
        return int(normalize_text(value))
    except (TypeError, ValueError):
        return 0


def normalize_pot_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", normalize_text(value)).upper()
    if not cleaned:
        return ""
    matched = re.fullmatch(r"([0-9]{1,3})T?", cleaned)
    if not matched:
        return ""
    number = int(matched.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def normalize_varietal_id(value: str) -> str:
    cleaned = re.sub(r"[^0-9]", "", normalize_text(value))
    if not cleaned:
        return ""
    number = int(cleaned)
    if number <= 0:
        return ""
    return str(number)


def normalize_reviewed(value: str) -> str:
    text = normalize_text(value).lower()
    if text in {"1", "true", "yes", "y"}:
        return "1"
    return "0"


def normalize_row(raw: Dict[str, str], source_file: str, imported_at_utc: str) -> Dict[str, str]:
    return {
        "run_date": normalize_text(raw.get("run_date", "")),
        "row_index": str(parse_int(raw.get("row_index", ""))),
        "source_asset_id": normalize_text(raw.get("source_asset_id", "")),
        "photo_url": normalize_text(raw.get("photo_url", "")),
        "suggested_pot_id": normalize_pot_id(raw.get("suggested_pot_id", "")),
        "suggested_varietal_id": normalize_varietal_id(raw.get("suggested_varietal_id", "")),
        "confirmed_pot_id": normalize_pot_id(raw.get("confirmed_pot_id", "")),
        "confirmed_varietal_id": normalize_varietal_id(raw.get("confirmed_varietal_id", "")),
        "reviewed": normalize_reviewed(raw.get("reviewed", "")),
        "notes": normalize_text(raw.get("notes", "")),
        "last_edited_at": normalize_text(raw.get("last_edited_at", "")),
        "imported_at_utc": imported_at_utc,
        "source_file": source_file,
    }


def load_export_rows(path: Path, imported_at_utc: str) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} missing CSV header")
        return [normalize_row(raw, str(path), imported_at_utc) for raw in reader]


def load_canonical_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        rows: List[Dict[str, str]] = []
        for raw in reader:
            row: Dict[str, str] = {}
            for field in CANONICAL_FIELDS:
                row[field] = normalize_text(raw.get(field, ""))
            rows.append(row)
        return rows


def row_key(row: Dict[str, str]) -> Tuple[str, int, str]:
    return (
        normalize_text(row.get("run_date", "")),
        parse_int(row.get("row_index", "")),
        normalize_text(row.get("source_asset_id", "")),
    )


def merge_rows(base_rows: List[Dict[str, str]], incoming_rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], int, int]:
    merged: Dict[Tuple[str, int, str], Dict[str, str]] = {}
    for row in base_rows:
        merged[row_key(row)] = row

    inserted = 0
    updated = 0
    for row in incoming_rows:
        key = row_key(row)
        if key in merged:
            updated += 1
        else:
            inserted += 1
        merged[key] = row

    ordered_keys = sorted(merged.keys(), key=lambda key: (key[0], key[1], key[2]))
    ordered_rows = [merged[key] for key in ordered_keys]
    return ordered_rows, inserted, updated


def write_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: List[Dict[str, str]]) -> Dict[str, object]:
    reviewed_count = sum(1 for row in rows if normalize_reviewed(row.get("reviewed", "")) == "1")
    changed_rows = [
        row
        for row in rows
        if normalize_pot_id(row.get("confirmed_pot_id", "")) != normalize_pot_id(row.get("suggested_pot_id", ""))
        or normalize_varietal_id(row.get("confirmed_varietal_id", ""))
        != normalize_varietal_id(row.get("suggested_varietal_id", ""))
    ]

    run_counts = Counter(normalize_text(row.get("run_date", "")) for row in rows)
    changed_run_counts = Counter(normalize_text(row.get("run_date", "")) for row in changed_rows)

    pot_to_varietals: Dict[str, set[str]] = defaultdict(set)
    for row in rows:
        pot_id = normalize_pot_id(row.get("confirmed_pot_id", ""))
        varietal_id = normalize_varietal_id(row.get("confirmed_varietal_id", ""))
        if pot_id and varietal_id:
            pot_to_varietals[pot_id].add(varietal_id)

    inconsistent_pots = {
        pot_id: sorted(varietals)
        for pot_id, varietals in pot_to_varietals.items()
        if len(varietals) > 1
    }

    return {
        "total_rows": len(rows),
        "reviewed_rows": reviewed_count,
        "changed_rows": len(changed_rows),
        "run_counts": dict(sorted(run_counts.items())),
        "changed_run_counts": dict(sorted(changed_run_counts.items())),
        "inconsistent_pot_varietal_assignments": inconsistent_pots,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge exported manual two-run tag CSV into canonical overrides CSV."
    )
    parser.add_argument(
        "--incoming",
        type=Path,
        required=True,
        help="CSV exported by tracker/manual-two-run-tagger.html",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides.csv"),
        help="Existing canonical manual tag overrides CSV (if present).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides.csv"),
        help="Output canonical overrides CSV path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides_summary.json"),
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--imported-at-utc",
        default="",
        help="Override import timestamp in UTC ISO format.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.incoming.exists():
        raise SystemExit(f"incoming_not_found={args.incoming}")

    imported_at_utc = normalize_text(args.imported_at_utc)
    if not imported_at_utc:
        imported_at_utc = datetime.now(timezone.utc).isoformat()

    base_rows = load_canonical_rows(args.base)
    incoming_rows = load_export_rows(args.incoming, imported_at_utc)

    merged_rows, inserted, updated = merge_rows(base_rows, incoming_rows)
    write_rows(args.output, merged_rows)

    summary = summarize(incoming_rows)
    summary.update(
        {
            "incoming_rows": len(incoming_rows),
            "base_rows": len(base_rows),
            "inserted": inserted,
            "updated": updated,
            "output_rows": len(merged_rows),
            "incoming_file": str(args.incoming),
            "output_csv": str(args.output),
            "imported_at_utc": imported_at_utc,
        }
    )

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"incoming_rows={len(incoming_rows)}")
    print(f"base_rows={len(base_rows)}")
    print(f"inserted={inserted}")
    print(f"updated={updated}")
    print(f"output_rows={len(merged_rows)}")
    print(f"changed_rows={summary['changed_rows']}")
    print(f"inconsistent_pots={len(summary['inconsistent_pot_varietal_assignments'])}")
    print(f"output_csv={args.output}")
    print(f"summary_json={args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
