#!/usr/bin/env python3
"""Build a self-contained reviewer pack for a single run date under /tmp."""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List


def run_cmd(cmd: List[str]) -> None:
    print(f"+ {' '.join(shlex.quote(part) for part in cmd)}")
    subprocess.run(cmd, check=True)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def resolve_latest_run_date(labeled_csv: Path) -> str:
    rows = read_csv_rows(labeled_csv)
    run_dates = sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )
    if not run_dates:
        raise ValueError(f"No capture_date values found in {labeled_csv}")
    return run_dates[-1]


def filter_queue_rows(queue_csv: Path, run_date: str, output_csv: Path) -> List[Dict[str, str]]:
    rows = read_csv_rows(queue_csv)
    selected = [
        row for row in rows if (row.get("run_date", "") or "").strip() == run_date
    ]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return []
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(selected)
    return selected


def summarize_queue_rows(rows: List[Dict[str, str]]) -> Dict[str, object]:
    signal_counts = Counter()
    for row in rows:
        matched_count = int((row.get("matched_variant_count", "") or "0").strip() or 0)
        detected_numbers = [
            token.strip()
            for token in (row.get("ensemble_numbers_detected", "") or "").split(",")
            if token.strip()
        ]
        if matched_count > 0:
            signal_counts["ocr_match"] += 1
        elif detected_numbers:
            signal_counts["weak_ocr"] += 1
        else:
            signal_counts["no_signal"] += 1
    return {
        "rows_total": len(rows),
        "signal_tier_counts": dict(signal_counts),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an isolated hard-row reviewer pack for one run date."
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Run date to package (YYYY-MM-DD). Defaults to latest capture date.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/tmp/tomato_reviewer_packs"),
        help="Root directory for isolated reviewer pack outputs.",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Reuse an existing OCR queue instead of rerunning OCR recovery.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled intake CSV.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory with downloaded intake images.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-to-variety map CSV.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot override CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path("releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Baseline mapping CSV for continuity.",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Latest mapping CSV used for suggested variety names.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count for full watering-day runs.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    py = sys.executable
    run_date = args.run_date.strip() or resolve_latest_run_date(args.labeled_csv)
    pack_slug = run_date.replace("-", "_")
    pack_dir = args.output_root / f"reviewer_pack_{pack_slug}"
    ocr_dir = pack_dir / "ocr_recovery"
    queue_csv = ocr_dir / "manual_label_queue.csv"
    filtered_queue_csv = pack_dir / f"manual_label_queue_{pack_slug}.csv"
    reviewer_dir = pack_dir / "reviewer_page"
    reviewer_html = reviewer_dir / "index.html"
    reviewer_assets_dir = reviewer_dir / "assets"

    if not args.skip_ocr:
        run_cmd(
            [
                py,
                "scripts/v16_ocr_recovery_experiment.py",
                "--labeled-csv",
                str(args.labeled_csv),
                "--images-dir",
                str(args.images_dir),
                "--run-dates",
                run_date,
                "--expected-pots",
                str(args.expected_pots),
                "--series-map-csv",
                str(args.series_map_csv),
                "--pot-series-overrides-csv",
                str(args.pot_series_overrides_csv),
                "--baseline-map-csv",
                str(args.baseline_map_csv),
                "--output-dir",
                str(ocr_dir),
            ]
        )

    if not queue_csv.exists():
        raise FileNotFoundError(
            f"Expected OCR queue CSV at {queue_csv}. Run without --skip-ocr or fix the OCR output."
        )

    queue_rows = filter_queue_rows(queue_csv, run_date, filtered_queue_csv)
    if not queue_rows:
        raise ValueError(f"No manual queue rows found for run_date={run_date}")

    run_cmd(
        [
            py,
            "scripts/build_hard_row_reviewer_page.py",
            "--queue-csv",
            str(filtered_queue_csv),
            "--mapping-csv",
            str(args.mapping_csv),
            "--assets-dir",
            str(reviewer_assets_dir),
            "--output-html",
            str(reviewer_html),
        ]
    )

    summary = summarize_queue_rows(queue_rows)
    summary.update(
        {
            "run_date": run_date,
            "pack_dir": str(pack_dir),
            "ocr_dir": str(ocr_dir),
            "queue_csv": str(filtered_queue_csv),
            "reviewer_html": str(reviewer_html),
        }
    )
    summary_path = pack_dir / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"run_date={run_date}")
    print(f"pack_dir={pack_dir}")
    print(f"queue_rows={summary['rows_total']}")
    print(f"signal_tier_counts={json.dumps(summary['signal_tier_counts'], sort_keys=True)}")
    print(f"reviewer_html={reviewer_html}")
    print(f"summary_json={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
