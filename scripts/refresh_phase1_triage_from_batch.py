#!/usr/bin/env python3
"""Refresh Phase-1 triage run-B anchors from a specific same-day photo batch."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from build_tomato_pot_mapping import extract_numeric_candidates, normalize_pot_id, read_rows


def parse_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return 0


def select_batch_rows(
    labeled_rows: List[Dict[str, str]],
    run_date: str,
    row_start: int,
    row_end: int,
) -> List[Tuple[int, Dict[str, str]]]:
    out: List[Tuple[int, Dict[str, str]]] = []
    for row_index, row in enumerate(labeled_rows, start=1):
        capture_date = (row.get("capture_date", "") or "").strip()
        if capture_date != run_date:
            continue
        if row_index < row_start or row_index > row_end:
            continue
        out.append((row_index, row))
    return out


def build_pot_lookup(
    batch_rows: List[Tuple[int, Dict[str, str]]],
    expected_pots: int,
) -> Dict[str, Dict[str, str]]:
    if len(batch_rows) != expected_pots:
        raise ValueError(
            f"batch row count mismatch: got {len(batch_rows)} expected {expected_pots}"
        )

    by_pot: Dict[str, Dict[str, str]] = {}
    for position, (global_row_index, row) in enumerate(batch_rows, start=1):
        pot_id = f"{position}T"
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        photo_url = (row.get("photo_url", "") or "").strip()
        notes = (row.get("notes", "") or "").strip()
        caption = (row.get("caption", "") or "").strip()
        ocr_excerpt = (row.get("ocr_excerpt", "") or "").strip()
        numbers = extract_numeric_candidates(notes, caption, ocr_excerpt)
        ocr_confirms = "yes" if position in numbers else "no"
        by_pot[pot_id] = {
            "run_b_asset_id": source_asset_id,
            "run_b_photo_url": photo_url,
            "run_b_ocr_confirms_pot": ocr_confirms,
            "run_b_row_index": str(global_row_index),
        }
    return by_pot


def ensure_fieldnames(rows: List[Dict[str, str]], additions: List[str]) -> List[str]:
    existing = list(rows[0].keys()) if rows else []
    for field in additions:
        if field not in existing:
            existing.append(field)
    return existing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh Phase-1 triage run-B anchors from an explicit same-day batch window."
    )
    parser.add_argument(
        "--triage-csv",
        type=Path,
        default=Path("data/research/phase1_day1_vs_lastday_manual_triage.csv"),
        help="Phase-1 triage CSV to update in-place.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed-photo CSV containing run rows.",
    )
    parser.add_argument(
        "--run-b-date",
        default="2026-03-22",
        help="Run-B date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--row-start",
        type=int,
        default=458,
        help="Global row index where batch starts (inclusive).",
    )
    parser.add_argument(
        "--row-end",
        type=int,
        default=489,
        help="Global row index where batch ends (inclusive).",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count in batch.",
    )
    parser.add_argument(
        "--run-b-batch-id",
        default="phase1_end_batch_a",
        help="Batch identifier to persist in triage rows.",
    )
    parser.add_argument(
        "--run-b-batch-label",
        default="Batch 1 (pre-repot, Phase 1 end)",
        help="Batch label to persist in triage rows.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.triage_csv.exists():
        raise SystemExit(f"triage_csv_not_found={args.triage_csv}")
    if not args.labeled_csv.exists():
        raise SystemExit(f"labeled_csv_not_found={args.labeled_csv}")

    triage_rows = read_rows(args.triage_csv)
    labeled_rows = read_rows(args.labeled_csv)
    batch_rows = select_batch_rows(
        labeled_rows=labeled_rows,
        run_date=(args.run_b_date or "").strip(),
        row_start=args.row_start,
        row_end=args.row_end,
    )
    by_pot = build_pot_lookup(batch_rows, args.expected_pots)

    missing_pots: List[str] = []
    for triage_row in triage_rows:
        pot_id = normalize_pot_id((triage_row.get("pot_id", "") or "").strip())
        if not pot_id:
            continue
        mapped = by_pot.get(pot_id)
        if not mapped:
            missing_pots.append(pot_id)
            continue
        triage_row["run_b_date"] = (args.run_b_date or "").strip()
        triage_row["run_b_asset_id"] = mapped["run_b_asset_id"]
        triage_row["run_b_photo_url"] = mapped["run_b_photo_url"]
        triage_row["run_b_ocr_confirms_pot"] = mapped["run_b_ocr_confirms_pot"]
        triage_row["missing_in_run_b"] = "False"
        triage_row["run_b_batch_id"] = (args.run_b_batch_id or "").strip()
        triage_row["run_b_batch_label"] = (args.run_b_batch_label or "").strip()
        triage_row["run_b_row_index"] = mapped["run_b_row_index"]

    fieldnames = ensure_fieldnames(
        triage_rows,
        ["run_b_batch_id", "run_b_batch_label", "run_b_row_index"],
    )
    args.triage_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.triage_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(triage_rows)

    run_b_dates = sorted(
        {
            (row.get("run_b_date", "") or "").strip()
            for row in triage_rows
            if (row.get("run_b_date", "") or "").strip()
        }
    )
    batch_labels = sorted(
        {
            (row.get("run_b_batch_label", "") or "").strip()
            for row in triage_rows
            if (row.get("run_b_batch_label", "") or "").strip()
        }
    )
    print(f"triage_csv={args.triage_csv}")
    print(f"run_b_date_values={run_b_dates}")
    print(f"run_b_batch_labels={batch_labels}")
    print(f"batch_row_count={len(batch_rows)}")
    print(f"missing_pots={sorted(set(missing_pots), key=lambda value: parse_int(value[:-1]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
