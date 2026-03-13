#!/usr/bin/env python3
"""Validate Phase 1 seedling lock-in boundaries and mapping consistency."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from build_tomato_pot_mapping import (
    build_mapping,
    load_baseline_variety_map,
    load_phase_timeline,
    load_pot_series_overrides,
    load_row_overrides,
    load_series_variety_map,
    parse_missing_pot_ids,
    read_rows,
    row_override_excludes_row,
)

REQUIRED_PHASE_ID = "phase_1_seedling"
REQUIRED_START_DATE = "2026-02-27"
REQUIRED_END_DATE = "2026-03-11"
REQUIRED_START_LABEL = "Day 1 of Phase 1"
REQUIRED_END_LABEL = "Last Day of Phase 1"


def parse_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return 0


def normalize_reviewed(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def find_phase_row(phase_rows: List[Dict[str, str]]) -> Dict[str, str]:
    for row in phase_rows:
        if (row.get("phase_id", "") or "").strip() == REQUIRED_PHASE_ID:
            return row
    return {}


def collect_anchor_rows(
    overrides_path: Path,
    start_date: str,
    end_date: str,
) -> Dict[str, object]:
    with overrides_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    by_run: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        run_date = (row.get("run_date", "") or "").strip()
        if run_date:
            by_run[run_date].append(row)

    def run_summary(run_date: str) -> Dict[str, object]:
        run_rows = by_run.get(run_date, [])
        reviewed_rows = [row for row in run_rows if normalize_reviewed(row.get("reviewed", ""))]
        unique_pots = {
            (row.get("confirmed_pot_id", "") or "").strip()
            for row in reviewed_rows
            if (row.get("confirmed_pot_id", "") or "").strip()
        }
        return {
            "rows": len(run_rows),
            "reviewed_rows": len(reviewed_rows),
            "unique_pots": sorted(unique_pots),
            "unique_pot_count": len(unique_pots),
        }

    start_summary = run_summary(start_date)
    end_summary = run_summary(end_date)

    end_rows = by_run.get(end_date, [])
    missing_21_declared = False
    excluded_row_432 = False
    selected_row_435 = False

    for row in end_rows:
        notes = (row.get("notes", "") or "").strip()
        row_index = parse_int(row.get("row_index", ""))
        missing_ids = parse_missing_pot_ids(notes)
        if "21T" in missing_ids:
            missing_21_declared = True
        if row_index == 432 and row_override_excludes_row(notes):
            excluded_row_432 = True
        if row_index == 435 and "selected_for_25T_reference" in notes:
            selected_row_435 = True

    return {
        "start": start_summary,
        "end": end_summary,
        "missing_21_declared": missing_21_declared,
        "excluded_row_432": excluded_row_432,
        "selected_row_435": selected_row_435,
    }


def check_consistency(
    labeled_csv: Path,
    series_map_csv: Path,
    pot_overrides_csv: Path,
    baseline_map_csv: Path,
    row_overrides_csv: Path,
    phase_timeline_csv: Path,
) -> Dict[str, object]:
    rows = read_rows(labeled_csv)
    run_dates = sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )

    series_map = load_series_variety_map(series_map_csv)
    pot_overrides = load_pot_series_overrides(pot_overrides_csv)
    baseline_map = load_baseline_variety_map(baseline_map_csv)
    row_overrides = load_row_overrides(row_overrides_csv)
    phase_timeline = load_phase_timeline(phase_timeline_csv)

    pot_to_series: Dict[str, set[str]] = defaultdict(set)
    pot_to_variety: Dict[str, set[str]] = defaultdict(set)
    duplicate_pots_by_run: Dict[str, List[str]] = {}

    for run_date in run_dates:
        selected = [
            row
            for row in rows
            if (row.get("capture_date", "") or "").strip() == run_date
        ]
        expected = min(32, len(selected))
        mapped_rows, _ = build_mapping(
            rows=rows,
            run_date=run_date,
            expected_pots=expected,
            potting_date="2026-02-24",
            day_one_photo_date="2026-02-25",
            lifecycle_stage="sapling",
            assume_sequential_pot_ids=True,
            tomato_only_run=True,
            series_variety_map=series_map,
            pot_series_overrides=pot_overrides,
            baseline_variety_map=baseline_map,
            baseline_reconcile=True,
            context_id="context_default",
            row_overrides=row_overrides,
            phase_timeline=phase_timeline,
        )

        per_run_counts: Dict[str, int] = defaultdict(int)
        for row in mapped_rows:
            pot_id = (row.get("pot_id", "") or "").strip()
            packet = (row.get("packet_number", "") or "").strip()
            variety = (row.get("variety_name", "") or "").strip()
            if not pot_id:
                continue
            per_run_counts[pot_id] += 1
            if packet:
                pot_to_series[pot_id].add(packet)
            if variety:
                pot_to_variety[pot_id].add(variety)

        duplicates = sorted(
            [pot_id for pot_id, count in per_run_counts.items() if count > 1],
            key=lambda pot_id: parse_int(pot_id[:-1]),
        )
        if duplicates:
            duplicate_pots_by_run[run_date] = duplicates

    inconsistent_pots: Dict[str, Dict[str, List[str]]] = {}
    for pot_id in sorted(pot_to_series.keys(), key=lambda value: parse_int(value[:-1])):
        series_values = sorted(pot_to_series.get(pot_id, set()))
        variety_values = sorted(pot_to_variety.get(pot_id, set()))
        if len(series_values) > 1 or len(variety_values) > 1:
            inconsistent_pots[pot_id] = {
                "series_values": series_values,
                "variety_values": variety_values,
            }

    return {
        "run_dates": run_dates,
        "duplicate_pots_by_run": duplicate_pots_by_run,
        "inconsistent_pots": inconsistent_pots,
        "inconsistent_pot_count": len(inconsistent_pots),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify Phase 1 seedling lock-in (day one + last day anchors)."
    )
    parser.add_argument(
        "--phase-timeline-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_phase_timeline.csv"),
        help="Phase timeline CSV with phase boundaries.",
    )
    parser.add_argument(
        "--row-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides.csv"),
        help="Canonical manual row override CSV.",
    )
    parser.add_argument(
        "--pot-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Canonical pot-series override CSV.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-to-variety lookup CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path("releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Baseline mapping CSV used by mapping resolver.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed photos CSV.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("data/intake/google_photos/phase_one_seedling_lock_report.json"),
        help="Output JSON report path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    problems: List[str] = []

    phase_rows = load_phase_timeline(args.phase_timeline_csv)
    phase_row = find_phase_row(phase_rows)
    if not phase_row:
        problems.append(f"Missing phase row: {REQUIRED_PHASE_ID}")

    phase_start = (phase_row.get("phase_start_run_date", "") or "").strip()
    phase_end = (phase_row.get("phase_end_run_date", "") or "").strip()
    phase_start_label = (phase_row.get("phase_start_label", "") or "").strip()
    phase_end_label = (phase_row.get("phase_end_label", "") or "").strip()
    phase_lock_status = (phase_row.get("phase_lock_status", "") or "").strip()

    if phase_start != REQUIRED_START_DATE:
        problems.append(f"phase_start_run_date expected {REQUIRED_START_DATE} but got {phase_start}")
    if phase_end != REQUIRED_END_DATE:
        problems.append(f"phase_end_run_date expected {REQUIRED_END_DATE} but got {phase_end}")
    if phase_start_label != REQUIRED_START_LABEL:
        problems.append(f"phase_start_label expected '{REQUIRED_START_LABEL}' but got '{phase_start_label}'")
    if phase_end_label != REQUIRED_END_LABEL:
        problems.append(f"phase_end_label expected '{REQUIRED_END_LABEL}' but got '{phase_end_label}'")
    if phase_lock_status != "locked":
        problems.append("Phase lock status must be locked")

    anchor = collect_anchor_rows(args.row_overrides_csv, REQUIRED_START_DATE, REQUIRED_END_DATE)
    if int(anchor["start"]["rows"]) != 32:
        problems.append("Phase-1 start run must have exactly 32 override rows")
    if int(anchor["start"]["reviewed_rows"]) != 32:
        problems.append("Phase-1 start run must have exactly 32 reviewed rows")
    if int(anchor["start"]["unique_pot_count"]) != 32:
        problems.append("Phase-1 start run must map 32 unique pots")

    if int(anchor["end"]["rows"]) != 32:
        problems.append("Phase-1 end run must have exactly 32 override rows")
    if int(anchor["end"]["reviewed_rows"]) != 32:
        problems.append("Phase-1 end run must have exactly 32 reviewed rows")
    if int(anchor["end"]["unique_pot_count"]) != 31:
        problems.append("Phase-1 end run must map 31 unique pots (21T missing)")
    if not bool(anchor["missing_21_declared"]):
        problems.append("Phase-1 end run must declare missing_pot=21T")
    if not bool(anchor["excluded_row_432"]):
        problems.append("Phase-1 end run must exclude row 432 as duplicate")
    if not bool(anchor["selected_row_435"]):
        problems.append("Phase-1 end run must keep row 435 as canonical 25T reference")

    with args.pot_overrides_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        pot_override_rows = list(csv.DictReader(handle))
    pot_ids = [((row.get("pot_id", "") or "").strip()) for row in pot_override_rows if (row.get("pot_id", "") or "").strip()]
    if len(pot_ids) != 32:
        problems.append("Pot-series override table must contain exactly 32 pots")
    if len(set(pot_ids)) != 32:
        problems.append("Pot-series override table contains duplicate pot IDs")

    consistency = check_consistency(
        labeled_csv=args.labeled_csv,
        series_map_csv=args.series_map_csv,
        pot_overrides_csv=args.pot_overrides_csv,
        baseline_map_csv=args.baseline_map_csv,
        row_overrides_csv=args.row_overrides_csv,
        phase_timeline_csv=args.phase_timeline_csv,
    )
    if int(consistency["inconsistent_pot_count"]) > 0:
        problems.append("Cross-run pot/varietal inconsistencies detected")
    if consistency["duplicate_pots_by_run"]:
        problems.append("Duplicate pot IDs detected within one or more runs")

    report: Dict[str, object] = {
        "phase_id": REQUIRED_PHASE_ID,
        "phase_start_run_date": phase_start,
        "phase_end_run_date": phase_end,
        "phase_start_label": phase_start_label,
        "phase_end_label": phase_end_label,
        "phase_lock_status": phase_lock_status,
        "anchor_summary": anchor,
        "consistency": consistency,
        "problems": problems,
        "status": "pass" if not problems else "fail",
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"phase_id={REQUIRED_PHASE_ID}")
    print(f"phase_start={phase_start}")
    print(f"phase_end={phase_end}")
    print(f"phase_start_label={phase_start_label}")
    print(f"phase_end_label={phase_end_label}")
    print(f"phase_lock_status={phase_lock_status}")
    print(f"start_rows={anchor['start']['rows']} start_unique_pots={anchor['start']['unique_pot_count']}")
    print(f"end_rows={anchor['end']['rows']} end_unique_pots={anchor['end']['unique_pot_count']}")
    print(f"inconsistent_pot_count={consistency['inconsistent_pot_count']}")
    print(f"duplicate_run_count={len(consistency['duplicate_pots_by_run'])}")
    print(f"status={'pass' if not problems else 'fail'}")
    print(f"report_json={args.report_json}")

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
