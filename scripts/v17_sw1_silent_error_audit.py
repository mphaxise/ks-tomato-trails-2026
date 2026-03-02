#!/usr/bin/env python3
"""Sprint 1: silent-error-rate audit for pot-ID mapping."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import build_tomato_pot_mapping as mapping_builder


CAPTION_GT_RE = re.compile(
    r"\b(?:tomato|non_tomato)[_\s-]*([0-9]{1,3})\b", re.IGNORECASE
)
READY_STATUSES = {"ready_direct", "ready_auto_resolved"}

DETAIL_FIELDS = [
    "run_date",
    "row_index",
    "source_asset_id",
    "true_pot_id",
    "predicted_pot_id",
    "pot_correct",
    "is_error",
    "is_silent_error",
    "error_class",
    "mapping_status",
    "final_status",
    "resolution_source",
    "mapping_note",
    "truth_source",
    "truth_note",
]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def normalize_pot_id(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", (raw or "").strip()).upper()
    if not cleaned:
        return ""
    matched = re.fullmatch(r"([0-9]{1,3})T?", cleaned)
    if not matched:
        return ""
    number = int(matched.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def row_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        (row.get("run_date", "") or "").strip(),
        (row.get("row_index", "") or "").strip(),
        (row.get("source_asset_id", "") or "").strip(),
    )


def extract_caption_truth(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    truth_rows: List[Dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        caption = (row.get("caption", "") or "").strip()
        matched = CAPTION_GT_RE.search(caption)
        if not matched:
            continue
        pot_id = normalize_pot_id(matched.group(1))
        if not pot_id:
            continue
        truth_rows.append(
            {
                "run_date": (row.get("capture_date", "") or "").strip(),
                "row_index": str(idx),
                "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                "true_pot_id": pot_id,
                "truth_source": "caption_tag",
                "truth_note": "Derived from *_NN caption token",
            }
        )
    return truth_rows


def load_truth_csv(path: Path) -> List[Dict[str, str]]:
    rows = read_csv_rows(path)
    truth_rows: List[Dict[str, str]] = []
    for row in rows:
        run_date = (row.get("run_date", "") or "").strip()
        row_index = (row.get("row_index", "") or "").strip()
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        true_pot_id = normalize_pot_id((row.get("true_pot_id", "") or "").strip())
        if not run_date or not row_index or not source_asset_id or not true_pot_id:
            continue
        truth_rows.append(
            {
                "run_date": run_date,
                "row_index": row_index,
                "source_asset_id": source_asset_id,
                "true_pot_id": true_pot_id,
                "truth_source": (row.get("truth_source", "") or "ground_truth_csv").strip(),
                "truth_note": (row.get("truth_note", "") or "").strip(),
            }
        )
    return truth_rows


def split_run_dates(value: str) -> List[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def filter_truth_rows(
    truth_rows: Sequence[Dict[str, str]],
    run_dates: Sequence[str],
) -> List[Dict[str, str]]:
    if not run_dates:
        return list(truth_rows)
    allowed = set(run_dates)
    return [row for row in truth_rows if (row.get("run_date", "") or "").strip() in allowed]


def build_prediction_map(
    *,
    labeled_rows: List[Dict[str, str]],
    run_dates: Sequence[str],
    expected_pots: int,
    potting_date: str,
    day_one_photo_date: str,
    lifecycle_stage: str,
    context_id: str,
    assume_sequential_pot_ids: bool,
    tomato_only_run: bool,
    baseline_reconcile: bool,
    series_map_csv: Path | None,
    pot_series_overrides_csv: Path | None,
    baseline_map_csv: Path | None,
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    series_variety_map = mapping_builder.load_series_variety_map(series_map_csv)
    pot_series_overrides = mapping_builder.load_pot_series_overrides(pot_series_overrides_csv)
    baseline_variety_map = mapping_builder.load_baseline_variety_map(baseline_map_csv)

    output: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for run_date in sorted(run_dates):
        mapping_rows, _report = mapping_builder.build_mapping(
            rows=labeled_rows,
            run_date=run_date,
            expected_pots=expected_pots,
            potting_date=potting_date,
            day_one_photo_date=day_one_photo_date,
            lifecycle_stage=lifecycle_stage,
            assume_sequential_pot_ids=assume_sequential_pot_ids,
            tomato_only_run=tomato_only_run,
            series_variety_map=series_variety_map,
            pot_series_overrides=pot_series_overrides,
            baseline_variety_map=baseline_variety_map,
            baseline_reconcile=baseline_reconcile,
            context_id=context_id,
        )
        for mapping_row in mapping_rows:
            output[row_key(mapping_row)] = mapping_row
    return output


def classify_error_class(row: Dict[str, object]) -> str:
    if not row.get("is_error", 0):
        return "correct"
    if row.get("is_silent_error", 0):
        return "silent_error"
    mapping_status = str(row.get("mapping_status", "") or "")
    if mapping_status and mapping_status != "ok":
        return "surfaced_error"
    if not str(row.get("predicted_pot_id", "") or ""):
        return "missing_prediction"
    return "surfaced_error"


def build_detail_rows(
    truth_rows: Sequence[Dict[str, str]],
    prediction_map: Dict[Tuple[str, str, str], Dict[str, str]],
) -> List[Dict[str, object]]:
    details: List[Dict[str, object]] = []
    for truth in truth_rows:
        key = row_key(truth)
        predicted = prediction_map.get(key, {})

        true_pot_id = normalize_pot_id((truth.get("true_pot_id", "") or "").strip())
        predicted_pot_id = normalize_pot_id((predicted.get("pot_id", "") or "").strip())
        pot_correct = int(bool(true_pot_id and predicted_pot_id and true_pot_id == predicted_pot_id))
        is_error = int(not pot_correct)
        mapping_status = (predicted.get("mapping_status", "") or "").strip()
        final_status = (predicted.get("final_status", "") or "").strip()
        is_ready = final_status in READY_STATUSES
        is_silent_error = int(bool(is_error and mapping_status == "ok" and is_ready))

        row: Dict[str, object] = {
            "run_date": (truth.get("run_date", "") or "").strip(),
            "row_index": (truth.get("row_index", "") or "").strip(),
            "source_asset_id": (truth.get("source_asset_id", "") or "").strip(),
            "true_pot_id": true_pot_id,
            "predicted_pot_id": predicted_pot_id,
            "pot_correct": pot_correct,
            "is_error": is_error,
            "is_silent_error": is_silent_error,
            "mapping_status": mapping_status,
            "final_status": final_status,
            "resolution_source": (predicted.get("resolution_source", "") or "").strip(),
            "mapping_note": (predicted.get("mapping_note", "") or "").strip(),
            "truth_source": (truth.get("truth_source", "") or "").strip(),
            "truth_note": (truth.get("truth_note", "") or "").strip(),
        }
        row["error_class"] = classify_error_class(row)
        details.append(row)

    details.sort(
        key=lambda row: (
            str(row.get("run_date", "")),
            int(str(row.get("row_index", "0")) or "0"),
            str(row.get("source_asset_id", "")),
        )
    )
    return details


def build_summary(detail_rows: Sequence[Dict[str, object]], selected_run_dates: Sequence[str]) -> Dict[str, object]:
    total_rows = len(detail_rows)
    error_rows = [row for row in detail_rows if int(row.get("is_error", 0))]
    silent_rows = [row for row in error_rows if int(row.get("is_silent_error", 0))]
    surfaced_rows = [row for row in error_rows if not int(row.get("is_silent_error", 0))]

    class_counts = Counter(str(row.get("error_class", "") or "") for row in detail_rows)
    run_counts = Counter(str(row.get("run_date", "") or "") for row in detail_rows)
    resolution_counts = Counter(
        str(row.get("resolution_source", "") or "") for row in error_rows
    )

    total_errors = len(error_rows)
    silent_errors = len(silent_rows)
    surfaced_errors = len(surfaced_rows)

    silent_error_rate_of_errors = (
        float(silent_errors) / float(total_errors) if total_errors else 0.0
    )
    silent_error_rate_of_truth_rows = (
        float(silent_errors) / float(total_rows) if total_rows else 0.0
    )
    pot_accuracy = (
        float(total_rows - total_errors) / float(total_rows) if total_rows else 0.0
    )

    verdict = "no_errors_observed"
    if total_errors > 0:
        if silent_error_rate_of_errors < 0.05:
            verdict = "pass"
        elif silent_error_rate_of_errors > 0.15:
            verdict = "fail"
        else:
            verdict = "watch"

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_run_dates": list(selected_run_dates),
        "truth_rows": total_rows,
        "pot_accuracy": round(pot_accuracy, 4),
        "total_errors": total_errors,
        "silent_errors": silent_errors,
        "surfaced_errors": surfaced_errors,
        "silent_error_rate_of_errors": round(silent_error_rate_of_errors, 4),
        "silent_error_rate_of_truth_rows": round(silent_error_rate_of_truth_rows, 4),
        "sw1_verdict": verdict,
        "error_class_counts": dict(sorted(class_counts.items())),
        "truth_rows_by_run_date": dict(sorted(run_counts.items())),
        "error_resolution_source_counts": dict(sorted(resolution_counts.items())),
    }


def to_markdown(
    *,
    summary: Dict[str, object],
    truth_source: str,
    input_csv: Path,
    details_csv: Path,
    summary_json: Path,
) -> str:
    run_dates = summary.get("selected_run_dates", [])
    if not isinstance(run_dates, list):
        run_dates = []
    run_dates_text = ", ".join(str(item) for item in run_dates) if run_dates else "(auto)"

    error_class_counts = summary.get("error_class_counts", {})
    if not isinstance(error_class_counts, dict):
        error_class_counts = {}

    resolution_counts = summary.get("error_resolution_source_counts", {})
    if not isinstance(resolution_counts, dict):
        resolution_counts = {}

    limitations: List[str] = []
    if truth_source == "caption":
        limitations.append(
            "Caption-tag truth is concentrated on packet-label day (`2026-02-25`) and is not a full weak-run proxy."
        )
    run_date_set = {str(item) for item in run_dates}
    if not {"2026-02-28", "2026-03-01"} & run_date_set:
        limitations.append(
            "Current audit does not include the known weak runs (`2026-02-28`, `2026-03-01`) where OCR failed."
        )

    lines = [
        "# V1.7 SW-1 Silent Error Rate Audit",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        "",
        "## Inputs",
        "",
        f"- Labeled CSV: `{input_csv}`",
        f"- Truth source: `{truth_source}`",
        f"- Run dates: `{run_dates_text}`",
        "",
        "## Core Metrics",
        "",
        f"- Truth rows audited: `{summary.get('truth_rows', 0)}`",
        f"- Pot-ID accuracy: `{summary.get('pot_accuracy', 0)}`",
        f"- Total errors: `{summary.get('total_errors', 0)}`",
        f"- Silent errors: `{summary.get('silent_errors', 0)}`",
        f"- Surfaced errors: `{summary.get('surfaced_errors', 0)}`",
        f"- Silent error rate (of errors): `{summary.get('silent_error_rate_of_errors', 0)}`",
        f"- Silent error rate (of truth rows): `{summary.get('silent_error_rate_of_truth_rows', 0)}`",
        f"- SW-1 verdict: `{summary.get('sw1_verdict', '')}`",
        "",
        "## Error Class Counts",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]

    for key, value in sorted(error_class_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Error Resolution Source Counts",
            "",
            "| Resolution Source | Error Count |",
            "|---|---:|",
        ]
    )
    for key, value in sorted(resolution_counts.items()):
        label = key or "(empty)"
        lines.append(f"| `{label}` | {value} |")

    lines.extend(
        [
            "",
            "## Limits",
            "",
        ]
    )
    if limitations:
        for item in limitations:
            lines.append(f"- {item}")
    else:
        lines.append("- No additional limits recorded.")

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Detail CSV: `{details_csv}`",
            f"- Summary JSON: `{summary_json}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SW-1 silent error rate audit.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled input CSV used to run mapping.",
    )
    parser.add_argument(
        "--truth-source",
        choices=["caption", "csv"],
        default="caption",
        help="Ground truth source mode. caption uses *_NN tokens in caption.",
    )
    parser.add_argument(
        "--ground-truth-csv",
        type=Path,
        default=Path(""),
        help="Optional explicit ground-truth CSV when --truth-source=csv.",
    )
    parser.add_argument(
        "--run-dates",
        default="",
        help="Optional comma-separated run dates (YYYY-MM-DD) to audit.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected unique pot count when running mapping.",
    )
    parser.add_argument(
        "--potting-date",
        default="2026-02-24",
        help="Potting date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--day-one-photo-date",
        default="2026-02-25",
        help="Day-one photo date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--lifecycle-stage",
        default="sapling",
        help="Lifecycle label passed to mapping run.",
    )
    parser.add_argument(
        "--context-id",
        default="context_default",
        help="Context ID passed to mapping run.",
    )
    parser.add_argument(
        "--assume-sequential-pot-ids",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Infer pot IDs from row position when missing.",
    )
    parser.add_argument(
        "--tomato-only-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat run as tomato-only in mapping logic.",
    )
    parser.add_argument(
        "--baseline-reconcile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply baseline reconciliation in mapping logic.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series map CSV path.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot override CSV path.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline mapping CSV path.",
    )
    parser.add_argument(
        "--output-details-csv",
        type=Path,
        default=Path("data/research/v1_7/sw1_silent_error_audit_details.csv"),
        help="Output CSV path for row-level audit details.",
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("data/research/v1_7/sw1_silent_error_summary.json"),
        help="Output JSON path for summary metrics.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.7-SW1-SILENT-ERROR-AUDIT.md"),
        help="Output markdown report path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    labeled_rows = read_csv_rows(args.input_csv)
    run_date_filter = split_run_dates(args.run_dates)

    if args.truth_source == "caption":
        truth_rows = extract_caption_truth(labeled_rows)
    else:
        if not args.ground_truth_csv or str(args.ground_truth_csv) == ".":
            raise ValueError("--ground-truth-csv is required when --truth-source=csv")
        truth_rows = load_truth_csv(args.ground_truth_csv)

    truth_rows = filter_truth_rows(truth_rows, run_date_filter)
    if not truth_rows:
        raise ValueError("No truth rows found for the selected criteria.")

    by_run_date: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in truth_rows:
        by_run_date[(row.get("run_date", "") or "").strip()].append(row)
    selected_run_dates = sorted(by_run_date.keys())

    prediction_map = build_prediction_map(
        labeled_rows=labeled_rows,
        run_dates=selected_run_dates,
        expected_pots=args.expected_pots,
        potting_date=args.potting_date,
        day_one_photo_date=args.day_one_photo_date,
        lifecycle_stage=args.lifecycle_stage,
        context_id=args.context_id,
        assume_sequential_pot_ids=args.assume_sequential_pot_ids,
        tomato_only_run=args.tomato_only_run,
        baseline_reconcile=args.baseline_reconcile,
        series_map_csv=args.series_map_csv,
        pot_series_overrides_csv=args.pot_series_overrides_csv,
        baseline_map_csv=args.baseline_map_csv,
    )

    detail_rows = build_detail_rows(truth_rows, prediction_map)
    summary = build_summary(detail_rows, selected_run_dates)
    report_md = to_markdown(
        summary=summary,
        truth_source=args.truth_source,
        input_csv=args.input_csv,
        details_csv=args.output_details_csv,
        summary_json=args.output_summary_json,
    )

    write_csv(args.output_details_csv, detail_rows, DETAIL_FIELDS)
    write_json(args.output_summary_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_md, encoding="utf-8")

    print(f"truth_source={args.truth_source}")
    print(f"truth_rows={summary['truth_rows']}")
    print(f"selected_run_dates={','.join(selected_run_dates)}")
    print(f"pot_accuracy={summary['pot_accuracy']}")
    print(f"total_errors={summary['total_errors']}")
    print(f"silent_errors={summary['silent_errors']}")
    print(f"surfaced_errors={summary['surfaced_errors']}")
    print(f"silent_error_rate_of_errors={summary['silent_error_rate_of_errors']}")
    print(f"sw1_verdict={summary['sw1_verdict']}")
    print(f"output_details_csv={args.output_details_csv}")
    print(f"output_summary_json={args.output_summary_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
