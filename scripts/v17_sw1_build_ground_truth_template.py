#!/usr/bin/env python3
"""Build SW-1 weak-run ground-truth template from the hard queue."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


OUTPUT_FIELDS = [
    "run_date",
    "row_index",
    "source_asset_id",
    "photo_url",
    "predicted_pot_id",
    "predicted_pot_number",
    "ocr_match_variants",
    "ocr_numbers_detected",
    "label_crop_path",
    "center_crop_path",
    "full_crop_path",
    "true_pot_id",
    "true_variety_name",
    "truth_source",
    "truth_note",
    "reviewer",
    "reviewed_at",
]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_int(value: str) -> int:
    text = (value or "").strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def split_csv_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def round_robin_sample(rows: Sequence[Dict[str, str]], sample_size: int) -> List[Dict[str, str]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("run_date", "") or "").strip()].append(dict(row))

    run_dates = sorted(grouped.keys())
    for run_date in run_dates:
        grouped[run_date].sort(key=lambda row: parse_int(row.get("row_index", "")))

    picked: List[Dict[str, str]] = []
    cursors = {run_date: 0 for run_date in run_dates}

    while len(picked) < sample_size:
        progressed = False
        for run_date in run_dates:
            idx = cursors[run_date]
            rows_for_run = grouped[run_date]
            if idx >= len(rows_for_run):
                continue
            picked.append(rows_for_run[idx])
            cursors[run_date] = idx + 1
            progressed = True
            if len(picked) >= sample_size:
                break
        if not progressed:
            break

    return picked


def to_template_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    for row in rows:
        output.append(
            {
                "run_date": (row.get("run_date", "") or "").strip(),
                "row_index": (row.get("row_index", "") or "").strip(),
                "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "predicted_pot_id": (row.get("pot_id", "") or "").strip(),
                "predicted_pot_number": (row.get("pot_number", "") or "").strip(),
                "ocr_match_variants": (row.get("matched_variant_count", "") or "").strip(),
                "ocr_numbers_detected": (row.get("ensemble_numbers_detected", "") or "").strip(),
                "label_crop_path": (row.get("label_crop_path", "") or "").strip(),
                "center_crop_path": (row.get("center_crop_path", "") or "").strip(),
                "full_crop_path": (row.get("full_crop_path", "") or "").strip(),
                "true_pot_id": "",
                "true_variety_name": "",
                "truth_source": "",
                "truth_note": "",
                "reviewer": "",
                "reviewed_at": "",
            }
        )
    return output


def to_markdown(
    *,
    input_csv: Path,
    output_csv: Path,
    sample_rows: int,
    run_counts: Dict[str, int],
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# V1.7 SW-1 Weak-Run Ground Truth Template",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Inputs",
        "",
        f"- Queue CSV: `{input_csv}`",
        f"- Output template CSV: `{output_csv}`",
        f"- Sample rows: `{sample_rows}`",
        "",
        "## Run-Date Distribution",
        "",
        "| Run Date | Rows |",
        "|---|---:|",
    ]
    for run_date, count in sorted(run_counts.items()):
        lines.append(f"| `{run_date}` | {count} |")

    lines.extend(
        [
            "",
            "## Reviewer Instructions",
            "",
            "1. For each row, set `true_pot_id` (required) and `true_variety_name` (if known).",
            "2. Set `truth_source` to values such as `label_visible`, `context_memory`, or `cannot_verify`.",
            "3. If a row cannot be verified, leave `true_pot_id` blank and record reason in `truth_note`.",
            "4. After review, run `scripts/v17_sw1_silent_error_audit.py --truth-source csv --ground-truth-csv <reviewed_csv> --run-dates 2026-02-28,2026-03-01`.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a weak-run ground-truth template for SW-1."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/manual_label_queue.csv"),
        help="Hard queue CSV.",
    )
    parser.add_argument(
        "--run-dates",
        default="2026-02-28,2026-03-01",
        help="Comma-separated run dates to include.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Total rows to sample across run dates.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/v1_7/sw1_weak_run_ground_truth_template.csv"),
        help="Output template CSV path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.7-SW1-WEAK-RUN-GROUND-TRUTH-TEMPLATE.md"),
        help="Output markdown summary path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_csv_rows(args.input_csv)
    include_run_dates = set(split_csv_list(args.run_dates))
    filtered = [
        row
        for row in rows
        if (row.get("run_date", "") or "").strip() in include_run_dates
    ]

    sampled = round_robin_sample(filtered, sample_size=max(args.sample_size, 0))
    template_rows = to_template_rows(sampled)
    write_csv(args.output_csv, template_rows)

    run_counts: Dict[str, int] = defaultdict(int)
    for row in sampled:
        run_counts[(row.get("run_date", "") or "").strip()] += 1

    markdown = to_markdown(
        input_csv=args.input_csv,
        output_csv=args.output_csv,
        sample_rows=len(sampled),
        run_counts=dict(run_counts),
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"input_csv={args.input_csv}")
    print(f"run_dates={','.join(sorted(include_run_dates))}")
    print(f"sample_size={args.sample_size}")
    print(f"sampled_rows={len(sampled)}")
    print(f"output_csv={args.output_csv}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
