#!/usr/bin/env python3
"""Merge hard-row reviewer export into canonical manual row overrides."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

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

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
EXCLUDE_VERDICTS = {
    "exclude",
    "excluded",
    "reject",
    "rejected",
    "discard",
    "drop",
    "do_not_use",
    "not_tomato",
    "non_tomato",
    "nontomato",
}


def normalize_text(value: str) -> str:
    return (value or "").strip()


def parse_int(value: str) -> int:
    try:
        return int(normalize_text(value))
    except (TypeError, ValueError):
        return 0


def parse_bool(value: str) -> bool:
    return normalize_text(value).lower() in TRUE_VALUES


def canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_text(value).lower()).strip()


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
    digits = re.sub(r"[^0-9]", "", normalize_text(value))
    if not digits:
        return ""
    number = int(digits)
    if number <= 0:
        return ""
    return str(number)


def normalize_row_index(value: str) -> str:
    parsed = parse_int(value)
    return str(parsed) if parsed > 0 else ""


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} missing CSV header")
        return list(reader)


def load_canonical_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
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


def write_canonical_rows(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def row_key(row: Dict[str, str]) -> Tuple[str, int, str]:
    return (
        normalize_text(row.get("run_date", "")),
        parse_int(row.get("row_index", "")),
        normalize_text(row.get("source_asset_id", "")),
    )


def merge_rows(
    base_rows: Sequence[Dict[str, str]],
    incoming_rows: Sequence[Dict[str, str]],
) -> Tuple[List[Dict[str, str]], int, int]:
    merged: Dict[Tuple[str, int, str], Dict[str, str]] = {}
    for row in base_rows:
        merged[row_key(row)] = dict(row)

    inserted = 0
    updated = 0
    for row in incoming_rows:
        key = row_key(row)
        if key in merged:
            updated += 1
        else:
            inserted += 1
        merged[key] = dict(row)

    ordered_keys = sorted(merged.keys(), key=lambda item: (item[0], item[1], item[2]))
    return [merged[key] for key in ordered_keys], inserted, updated


def load_series_lookup(path: Path) -> Dict[str, str]:
    rows = load_csv_rows(path)
    lookup: Dict[str, str] = {}
    for row in rows:
        variety_name = canonical_key(row.get("variety_name", ""))
        series_number = normalize_varietal_id(row.get("series_number", ""))
        if variety_name and series_number:
            lookup[variety_name] = series_number
    return lookup


def load_pot_series_lookup(path: Path) -> Dict[str, str]:
    rows = load_csv_rows(path)
    lookup: Dict[str, str] = {}
    for row in rows:
        pot_id = normalize_pot_id(row.get("pot_id", ""))
        series_number = normalize_varietal_id(row.get("series_number", ""))
        if pot_id and series_number:
            lookup[pot_id] = series_number
    return lookup


def derive_run_date(review_rows: Sequence[Dict[str, str]], run_date_arg: str) -> str:
    if normalize_text(run_date_arg):
        return normalize_text(run_date_arg)
    run_dates = sorted(
        {
            normalize_text(row.get("run_date", ""))
            for row in review_rows
            if normalize_text(row.get("run_date", ""))
        }
    )
    if not run_dates:
        raise ValueError("Could not derive run_date from incoming hard-row review CSV.")
    if len(run_dates) > 1:
        raise ValueError(
            f"Incoming hard-row review CSV contains multiple run_dates: {run_dates}. "
            "Pass --run-date explicitly."
        )
    return run_dates[0]


def build_labeled_lookup(
    labeled_rows: Sequence[Dict[str, str]],
    run_date: str,
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    lookup: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row_index, row in enumerate(labeled_rows, start=1):
        if normalize_text(row.get("capture_date", "")) != run_date:
            continue
        source_asset_id = normalize_text(row.get("source_asset_id", ""))
        if not source_asset_id:
            continue
        key = (run_date, str(row_index), source_asset_id)
        lookup[key] = row
    return lookup


def build_review_lookup(
    review_rows: Sequence[Dict[str, str]],
    run_date: str,
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    lookup: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row in review_rows:
        row_run_date = normalize_text(row.get("run_date", ""))
        if row_run_date != run_date:
            continue
        row_index = normalize_row_index(row.get("row_index", ""))
        source_asset_id = normalize_text(row.get("source_asset_id", ""))
        if not row_index or not source_asset_id:
            continue
        key = (run_date, row_index, source_asset_id)
        lookup[key] = row
    return lookup


def build_queue_lookup(
    queue_rows: Sequence[Dict[str, str]],
    run_date: str,
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    lookup: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row in queue_rows:
        row_run_date = normalize_text(row.get("run_date", ""))
        if row_run_date != run_date:
            continue
        row_index = normalize_row_index(row.get("row_index", ""))
        source_asset_id = normalize_text(row.get("source_asset_id", ""))
        if not row_index or not source_asset_id:
            continue
        key = (run_date, row_index, source_asset_id)
        lookup[key] = row
    return lookup


def ordered_phase2_keys(
    queue_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
    review_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
) -> List[Tuple[str, str, str]]:
    keys = list(queue_lookup.keys()) if queue_lookup else list(review_lookup.keys())
    keys.sort(key=lambda item: (parse_int(item[1]), item[2]))
    return keys


def infer_varietal_id(variety_name: str, series_lookup: Dict[str, str]) -> str:
    key = canonical_key(variety_name)
    if not key:
        return ""
    return normalize_varietal_id(series_lookup.get(key, ""))


def unique_note_parts(parts: Sequence[str]) -> str:
    seen = set()
    out: List[str] = []
    for part in parts:
        text = normalize_text(part)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return "; ".join(out)


def build_phase2_rows(
    keys: Sequence[Tuple[str, str, str]],
    review_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
    queue_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
    labeled_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
    series_lookup: Dict[str, str],
    pot_series_lookup: Dict[str, str],
    imported_at_utc: str,
    source_file: str,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    rows: List[Dict[str, str]] = []
    stats = {
        "phase2_rows": 0,
        "queue_fallback_rows": 0,
        "excluded_rows": 0,
        "normalized_suggested_varietal_rows": 0,
        "normalized_confirmed_varietal_rows": 0,
    }

    for key in keys:
        run_date, row_index, source_asset_id = key
        review = review_lookup.get(key, {})
        queue = queue_lookup.get(key, {})
        labeled = labeled_lookup.get(key, {})
        review_present = bool(review)

        suggested_pot_id = normalize_pot_id(
            review.get("suggested_pot_id", "")
            or queue.get("pot_id", "")
        )
        confirmed_pot_id = normalize_pot_id(review.get("confirmed_pot_id", ""))
        if not confirmed_pot_id:
            confirmed_pot_id = suggested_pot_id

        suggested_varietal_id = infer_varietal_id(
            review.get("suggested_variety_name", "") or queue.get("variety_name", ""),
            series_lookup,
        )
        if not suggested_varietal_id and suggested_pot_id:
            suggested_varietal_id = normalize_varietal_id(
                pot_series_lookup.get(suggested_pot_id, "")
            )

        confirmed_varietal_id = infer_varietal_id(
            review.get("confirmed_variety_name", ""),
            series_lookup,
        )
        review_notes = normalize_text(review.get("notes", ""))
        review_notes_lower = review_notes.lower()
        keep_confirmed_varietal = (
            "keep_confirmed_varietal=1" in review_notes_lower
            or "varietal_lock=1" in review_notes_lower
        )
        keep_suggested_varietal = "keep_suggested_varietal=1" in review_notes_lower

        normalized_suggested_varietal = False
        normalized_confirmed_varietal = False

        suggested_pot_varietal_id = normalize_varietal_id(
            pot_series_lookup.get(suggested_pot_id, "")
        )
        if suggested_pot_varietal_id:
            if not suggested_varietal_id:
                suggested_varietal_id = suggested_pot_varietal_id
            elif (
                suggested_varietal_id != suggested_pot_varietal_id
                and not keep_suggested_varietal
            ):
                suggested_varietal_id = suggested_pot_varietal_id
                normalized_suggested_varietal = True
                stats["normalized_suggested_varietal_rows"] += 1

        confirmed_pot_varietal_id = normalize_varietal_id(
            pot_series_lookup.get(confirmed_pot_id, "")
        )
        if confirmed_pot_varietal_id:
            if not confirmed_varietal_id:
                confirmed_varietal_id = confirmed_pot_varietal_id
            elif (
                confirmed_varietal_id != confirmed_pot_varietal_id
                and not keep_confirmed_varietal
            ):
                confirmed_varietal_id = confirmed_pot_varietal_id
                normalized_confirmed_varietal = True
                stats["normalized_confirmed_varietal_rows"] += 1

        if not confirmed_varietal_id:
            confirmed_varietal_id = suggested_varietal_id
        if not suggested_varietal_id:
            suggested_varietal_id = confirmed_varietal_id

        verdict = normalize_text(review.get("verdict", "")).lower()
        do_not_use = parse_bool(review.get("do_not_use", ""))
        exclude_row = do_not_use or verdict in EXCLUDE_VERDICTS

        indoor_pot = "in a pot" in review_notes.lower()

        note_parts: List[str] = []
        if review_notes:
            note_parts.append(review_notes)
        note_parts.append("phase2_start=1")
        if indoor_pot:
            note_parts.append("phase2_micro_env=indoor_artificial_light")
        else:
            note_parts.append("phase2_micro_env=outdoor_sun")
        if exclude_row:
            note_parts.append("exclude_row=1")
        if normalized_suggested_varietal:
            note_parts.append("suggested_varietal_aligned_to_pot_map=1")
        if normalized_confirmed_varietal:
            note_parts.append("confirmed_varietal_aligned_to_pot_map=1")

        if not review_present:
            note_parts.append("phase2_fallback=accepted_queue_suggestion")
            stats["queue_fallback_rows"] += 1

        notes = unique_note_parts(note_parts)
        if exclude_row:
            stats["excluded_rows"] += 1

        photo_url = normalize_text(
            review.get("photo_url", "")
            or queue.get("photo_url", "")
            or labeled.get("photo_url", "")
        )

        row = {
            "run_date": run_date,
            "row_index": row_index,
            "source_asset_id": source_asset_id,
            "photo_url": photo_url,
            "suggested_pot_id": suggested_pot_id,
            "suggested_varietal_id": suggested_varietal_id,
            "confirmed_pot_id": confirmed_pot_id,
            "confirmed_varietal_id": confirmed_varietal_id,
            "reviewed": "1",
            "notes": notes,
            "last_edited_at": normalize_text(review.get("last_edited_at", "")),
            "imported_at_utc": imported_at_utc,
            "source_file": source_file,
        }
        rows.append(row)
        stats["phase2_rows"] += 1

    return rows, stats


def build_prephase_exclusion_rows(
    run_date: str,
    labeled_lookup: Dict[Tuple[str, str, str], Dict[str, str]],
    phase2_start_row_index: int,
    imported_at_utc: str,
    source_file: str,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for key in sorted(labeled_lookup.keys(), key=lambda item: (parse_int(item[1]), item[2])):
        _, row_index_text, source_asset_id = key
        row_index = parse_int(row_index_text)
        if row_index <= 0 or row_index >= phase2_start_row_index:
            continue
        labeled = labeled_lookup[key]
        rows.append(
            {
                "run_date": run_date,
                "row_index": str(row_index),
                "source_asset_id": source_asset_id,
                "photo_url": normalize_text(labeled.get("photo_url", "")),
                "suggested_pot_id": "",
                "suggested_varietal_id": "",
                "confirmed_pot_id": "",
                "confirmed_varietal_id": "",
                "reviewed": "1",
                "notes": "exclude_row=1; phase_boundary=pre_phase2_reference",
                "last_edited_at": "",
                "imported_at_utc": imported_at_utc,
                "source_file": source_file,
            }
        )
    return rows


def analyze_phase2_pots(
    phase2_rows: Sequence[Dict[str, str]],
    expected_pots: int,
) -> Dict[str, object]:
    counted_rows = [
        row
        for row in phase2_rows
        if "exclude_row=1" not in normalize_text(row.get("notes", ""))
    ]
    pot_counter = Counter(
        normalize_pot_id(row.get("confirmed_pot_id", ""))
        for row in counted_rows
        if normalize_pot_id(row.get("confirmed_pot_id", ""))
    )
    duplicates = sorted(
        [pot_id for pot_id, count in pot_counter.items() if count > 1],
        key=lambda value: parse_int(value[:-1]),
    )
    missing = sorted(
        [f"{number}T" for number in range(1, expected_pots + 1) if f"{number}T" not in pot_counter],
        key=lambda value: parse_int(value[:-1]),
    )
    return {
        "counted_phase2_rows": len(counted_rows),
        "phase2_unique_pot_count": len(pot_counter),
        "phase2_duplicate_pots": duplicates,
        "phase2_missing_pots": missing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge hard-row reviewer export into canonical manual row overrides."
    )
    parser.add_argument(
        "--incoming",
        type=Path,
        required=True,
        help="CSV exported from tracker/hard-row-reviewer*.html",
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_6/phase_end_2026-03-22/manual_label_queue.csv"),
        help="Hard-row queue CSV used to backfill unchanged rows.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed photos CSV used for row lookup.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-to-variety map CSV.",
    )
    parser.add_argument(
        "--pot-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot-to-series override CSV.",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides.csv"),
        help="Existing canonical overrides CSV.",
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
        default=Path("data/intake/google_photos/hard_row_review_merge_summary.json"),
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Target run date (YYYY-MM-DD). Defaults to single run_date in incoming CSV.",
    )
    parser.add_argument(
        "--phase2-start-row-index",
        type=int,
        default=0,
        help="Optional explicit row_index where phase-2 rows begin for this run.",
    )
    parser.add_argument(
        "--include-prephase-exclusions",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-add exclude_row=1 overrides for rows before phase-2 start index.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected unique pot count for phase-2 batch diagnostics.",
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
    if not args.labeled_csv.exists():
        raise SystemExit(f"labeled_csv_not_found={args.labeled_csv}")
    if not args.series_map_csv.exists():
        raise SystemExit(f"series_map_csv_not_found={args.series_map_csv}")
    if not args.pot_overrides_csv.exists():
        raise SystemExit(f"pot_overrides_csv_not_found={args.pot_overrides_csv}")

    imported_at_utc = normalize_text(args.imported_at_utc)
    if not imported_at_utc:
        imported_at_utc = datetime.now(timezone.utc).isoformat()

    review_rows = load_csv_rows(args.incoming)
    run_date = derive_run_date(review_rows, args.run_date)
    series_lookup = load_series_lookup(args.series_map_csv)
    pot_series_lookup = load_pot_series_lookup(args.pot_overrides_csv)
    labeled_rows = load_csv_rows(args.labeled_csv)
    labeled_lookup = build_labeled_lookup(labeled_rows, run_date)
    review_lookup = build_review_lookup(review_rows, run_date)

    queue_lookup: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    if args.queue_csv and args.queue_csv.exists():
        queue_rows = load_csv_rows(args.queue_csv)
        queue_lookup = build_queue_lookup(queue_rows, run_date)

    phase2_keys = ordered_phase2_keys(queue_lookup, review_lookup)
    if not phase2_keys:
        raise SystemExit("No phase-2 keys found for the requested run/date.")

    phase2_rows, phase2_stats = build_phase2_rows(
        keys=phase2_keys,
        review_lookup=review_lookup,
        queue_lookup=queue_lookup,
        labeled_lookup=labeled_lookup,
        series_lookup=series_lookup,
        pot_series_lookup=pot_series_lookup,
        imported_at_utc=imported_at_utc,
        source_file=str(args.incoming),
    )

    phase2_start_row_index = (
        args.phase2_start_row_index
        if args.phase2_start_row_index > 0
        else min(parse_int(key[1]) for key in phase2_keys)
    )

    prephase_rows: List[Dict[str, str]] = []
    if args.include_prephase_exclusions:
        prephase_rows = build_prephase_exclusion_rows(
            run_date=run_date,
            labeled_lookup=labeled_lookup,
            phase2_start_row_index=phase2_start_row_index,
            imported_at_utc=imported_at_utc,
            source_file=f"{args.incoming}#prephase_exclusions",
        )

    incoming_rows = phase2_rows + prephase_rows
    base_rows = load_canonical_rows(args.base)
    merged_rows, inserted, updated = merge_rows(base_rows, incoming_rows)
    write_canonical_rows(args.output, merged_rows)

    phase2_diagnostics = analyze_phase2_pots(phase2_rows, args.expected_pots)

    summary: Dict[str, object] = {
        "incoming_file": str(args.incoming),
        "queue_csv": str(args.queue_csv) if args.queue_csv else "",
        "run_date": run_date,
        "phase2_start_row_index": phase2_start_row_index,
        "incoming_review_rows": len(review_rows),
        "incoming_rows_merged": len(incoming_rows),
        "phase2_rows_merged": phase2_stats["phase2_rows"],
        "phase2_excluded_rows": phase2_stats["excluded_rows"],
        "queue_fallback_rows": phase2_stats["queue_fallback_rows"],
        "normalized_suggested_varietal_rows": phase2_stats[
            "normalized_suggested_varietal_rows"
        ],
        "normalized_confirmed_varietal_rows": phase2_stats[
            "normalized_confirmed_varietal_rows"
        ],
        "prephase_exclusion_rows": len(prephase_rows),
        "base_rows": len(base_rows),
        "inserted": inserted,
        "updated": updated,
        "output_rows": len(merged_rows),
        "output_csv": str(args.output),
        "imported_at_utc": imported_at_utc,
    }
    summary.update(phase2_diagnostics)

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"run_date={run_date}")
    print(f"incoming_review_rows={len(review_rows)}")
    print(f"phase2_rows_merged={phase2_stats['phase2_rows']}")
    print(f"queue_fallback_rows={phase2_stats['queue_fallback_rows']}")
    print(
        "normalized_suggested_varietal_rows="
        f"{phase2_stats['normalized_suggested_varietal_rows']}"
    )
    print(
        "normalized_confirmed_varietal_rows="
        f"{phase2_stats['normalized_confirmed_varietal_rows']}"
    )
    print(f"prephase_exclusion_rows={len(prephase_rows)}")
    print(f"phase2_unique_pot_count={summary['phase2_unique_pot_count']}")
    print(f"phase2_duplicate_pots={summary['phase2_duplicate_pots']}")
    print(f"phase2_missing_pots={summary['phase2_missing_pots']}")
    print(f"inserted={inserted}")
    print(f"updated={updated}")
    print(f"output_rows={len(merged_rows)}")
    print(f"output_csv={args.output}")
    print(f"summary_json={args.summary_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
