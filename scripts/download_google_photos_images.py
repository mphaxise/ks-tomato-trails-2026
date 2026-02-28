#!/usr/bin/env python3
"""Download Google Photos image rows from intake CSV into local files."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List


def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} is missing a CSV header")
        return list(reader)


def latest_capture_date(rows: List[Dict[str, str]]) -> str:
    dates = sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )
    if not dates:
        raise ValueError("No capture_date values found in input CSV")
    return dates[-1]


def file_name(row_index: int, source_asset_id: str) -> str:
    return f"{row_index:02d}_{source_asset_id}.jpg"


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["curl", "-sS", "-L", "-A", "Mozilla/5.0", url, "-o", str(output_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "curl failed")


def run(
    input_csv: Path,
    output_dir: Path,
    run_date: str,
    all_dates: bool,
    skip_existing: bool,
) -> Dict[str, int | str]:
    rows = read_rows(input_csv)
    active_run_date = run_date.strip() if run_date.strip() else latest_capture_date(rows)

    selected_rows = 0
    downloaded_rows = 0
    skipped_existing_rows = 0
    skipped_missing_url = 0
    failed_downloads = 0

    for index, row in enumerate(rows, start=1):
        capture_date = (row.get("capture_date", "") or "").strip()
        if not all_dates and capture_date != active_run_date:
            continue

        selected_rows += 1
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        photo_url = (row.get("photo_url", "") or "").strip()

        if not source_asset_id or not photo_url:
            skipped_missing_url += 1
            continue

        target_path = output_dir / file_name(index, source_asset_id)
        if skip_existing and target_path.exists():
            skipped_existing_rows += 1
            continue

        try:
            download_file(photo_url, target_path)
            downloaded_rows += 1
        except Exception as exc:  # pylint: disable=broad-except
            failed_downloads += 1
            print(
                f"download_failed row={index} asset={source_asset_id} error={exc}"
            )

    return {
        "input_rows": len(rows),
        "selected_rows": selected_rows,
        "downloaded_rows": downloaded_rows,
        "skipped_existing_rows": skipped_existing_rows,
        "skipped_missing_url": skipped_missing_url,
        "failed_downloads": failed_downloads,
        "run_date": active_run_date,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download Google Photos image URLs from a mixed intake CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos.csv"),
        help="Mixed intake CSV with photo_url/source_asset_id rows",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory for downloaded images",
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Capture date to download (YYYY-MM-DD). Defaults to latest date found.",
    )
    parser.add_argument(
        "--all-dates",
        action="store_true",
        help="Download all rows instead of only the selected run date.",
    )
    parser.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip files that already exist (default: true).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    stats = run(
        args.input_csv,
        args.output_dir,
        args.run_date,
        args.all_dates,
        args.skip_existing,
    )
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"output_dir={args.output_dir}")
    return 1 if int(stats["failed_downloads"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
