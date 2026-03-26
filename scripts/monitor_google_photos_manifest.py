#!/usr/bin/env python3
"""Track Google Photos manifest deltas with date-focused reporting."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sort_date_counts(counter: Counter[str]) -> Dict[str, int]:
    return {key: int(counter[key]) for key in sorted(counter.keys())}


def build_snapshot(rows: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, str]], Dict[str, int], str]:
    assets: Dict[str, Dict[str, str]] = {}
    counts = Counter()
    for row in rows:
        asset_id = (row.get("source_asset_id", "") or "").strip()
        if not asset_id:
            continue
        capture_date = (row.get("capture_date", "") or "").strip()
        counts[capture_date] += 1
        assets[asset_id] = {
            "capture_date": capture_date,
            "captured_at": (row.get("captured_at", "") or "").strip(),
            "photo_index": (row.get("photo_index", "") or "").strip(),
        }
    date_counts = sort_date_counts(counts)
    latest_capture_date = max((key for key in date_counts if key), default="")
    return assets, date_counts, latest_capture_date


def load_state_assets(state_json: Path) -> Tuple[Dict[str, Dict[str, str]], Dict[str, int], str]:
    if not state_json.exists():
        return {}, {}, ""
    payload = json.loads(state_json.read_text(encoding="utf-8"))
    assets = payload.get("assets") or {}
    if not isinstance(assets, dict):
        assets = {}
    date_counts = payload.get("counts_by_date") or {}
    if not isinstance(date_counts, dict):
        date_counts = {}
    latest_capture_date = str(payload.get("latest_capture_date", "") or "").strip()
    return assets, {str(key): int(value) for key, value in date_counts.items()}, latest_capture_date


def summarize_ids(ids: List[str], source_assets: Dict[str, Dict[str, str]]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for asset_id in ids:
        capture_date = str((source_assets.get(asset_id, {}) or {}).get("capture_date", "") or "")
        counter[capture_date] += 1
    return sort_date_counts(counter)


def collect_samples(ids: List[str], source_assets: Dict[str, Dict[str, str]], limit: int = 20) -> List[Dict[str, str]]:
    samples: List[Dict[str, str]] = []
    for asset_id in ids[:limit]:
        meta = source_assets.get(asset_id, {}) or {}
        samples.append(
            {
                "source_asset_id": asset_id,
                "capture_date": str(meta.get("capture_date", "") or ""),
                "captured_at": str(meta.get("captured_at", "") or ""),
                "photo_index": str(meta.get("photo_index", "") or ""),
            }
        )
    return samples


def append_history_row(history_csv: Path, row: Dict[str, str]) -> None:
    history_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_at_utc",
        "manifest_csv",
        "comparison_source",
        "total_assets",
        "unique_dates",
        "latest_capture_date",
        "comparison_latest_capture_date",
        "added_count",
        "removed_count",
        "forward_added_count",
        "forward_removed_count",
    ]
    write_header = not history_csv.exists()
    with history_csv.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor Google Photos manifest changes by capture_date (new vs removed assets)."
    )
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=Path("data/intake/google_photos/album_manifest.csv"),
        help="Current manifest CSV from the latest intake.",
    )
    parser.add_argument(
        "--compare-manifest-csv",
        type=Path,
        default=None,
        help="Optional previous manifest CSV. If absent, falls back to state JSON.",
    )
    parser.add_argument(
        "--state-json",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_state.json"),
        help="Persistent state snapshot for future comparisons.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_latest.json"),
        help="Output JSON summary for the current run.",
    )
    parser.add_argument(
        "--history-csv",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_history.csv"),
        help="Append-only history of summary counts per run.",
    )
    parser.add_argument(
        "--run-at-utc",
        default="",
        help="Optional run timestamp override (ISO-8601 UTC).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.manifest_csv.exists():
        raise SystemExit(f"manifest_csv_not_found={args.manifest_csv}")

    run_at_utc = args.run_at_utc.strip() or iso_now_utc()

    current_rows = read_rows(args.manifest_csv)
    current_assets, current_counts_by_date, current_latest_date = build_snapshot(current_rows)

    comparison_source = ""
    previous_assets: Dict[str, Dict[str, str]]
    previous_counts_by_date: Dict[str, int]
    previous_latest_date: str
    if args.compare_manifest_csv and args.compare_manifest_csv.exists():
        previous_rows = read_rows(args.compare_manifest_csv)
        previous_assets, previous_counts_by_date, previous_latest_date = build_snapshot(previous_rows)
        comparison_source = str(args.compare_manifest_csv)
    else:
        previous_assets, previous_counts_by_date, previous_latest_date = load_state_assets(args.state_json)
        comparison_source = str(args.state_json) if previous_assets else "none"

    current_ids = set(current_assets.keys())
    previous_ids = set(previous_assets.keys())
    added_ids = sorted(current_ids - previous_ids)
    removed_ids = sorted(previous_ids - current_ids)

    added_by_date = summarize_ids(added_ids, current_assets)
    removed_by_date = summarize_ids(removed_ids, previous_assets)

    forward_added_ids = [
        asset_id
        for asset_id in added_ids
        if not previous_latest_date
        or str((current_assets.get(asset_id, {}) or {}).get("capture_date", "") or "") >= previous_latest_date
    ]
    forward_removed_ids = [
        asset_id
        for asset_id in removed_ids
        if not previous_latest_date
        or str((previous_assets.get(asset_id, {}) or {}).get("capture_date", "") or "") >= previous_latest_date
    ]

    report = {
        "run_at_utc": run_at_utc,
        "manifest_csv": str(args.manifest_csv),
        "comparison_source": comparison_source,
        "current": {
            "asset_count": len(current_assets),
            "unique_capture_dates": len(current_counts_by_date),
            "latest_capture_date": current_latest_date,
            "counts_by_date": current_counts_by_date,
        },
        "comparison": {
            "asset_count": len(previous_assets),
            "unique_capture_dates": len(previous_counts_by_date),
            "latest_capture_date": previous_latest_date,
            "counts_by_date": previous_counts_by_date,
        },
        "delta": {
            "added_count": len(added_ids),
            "removed_count": len(removed_ids),
            "added_by_capture_date": added_by_date,
            "removed_by_capture_date": removed_by_date,
            "forward_added_count": len(forward_added_ids),
            "forward_removed_count": len(forward_removed_ids),
            "forward_added_sample": collect_samples(forward_added_ids, current_assets),
            "forward_removed_sample": collect_samples(forward_removed_ids, previous_assets),
        },
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    state_payload = {
        "run_at_utc": run_at_utc,
        "manifest_csv": str(args.manifest_csv),
        "asset_count": len(current_assets),
        "unique_capture_dates": len(current_counts_by_date),
        "latest_capture_date": current_latest_date,
        "counts_by_date": current_counts_by_date,
        "assets": current_assets,
    }
    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(state_payload, ensure_ascii=True), encoding="utf-8")

    append_history_row(
        args.history_csv,
        {
            "run_at_utc": run_at_utc,
            "manifest_csv": str(args.manifest_csv),
            "comparison_source": comparison_source,
            "total_assets": str(len(current_assets)),
            "unique_dates": str(len(current_counts_by_date)),
            "latest_capture_date": current_latest_date,
            "comparison_latest_capture_date": previous_latest_date,
            "added_count": str(len(added_ids)),
            "removed_count": str(len(removed_ids)),
            "forward_added_count": str(len(forward_added_ids)),
            "forward_removed_count": str(len(forward_removed_ids)),
        },
    )

    print(f"run_at_utc={run_at_utc}")
    print(f"manifest_csv={args.manifest_csv}")
    print(f"comparison_source={comparison_source}")
    print(f"current_asset_count={len(current_assets)}")
    print(f"current_latest_capture_date={current_latest_date}")
    print(f"added_count={len(added_ids)}")
    print(f"removed_count={len(removed_ids)}")
    print(f"forward_added_count={len(forward_added_ids)}")
    print(f"forward_removed_count={len(forward_removed_ids)}")
    print(f"report_json={args.report_json}")
    print(f"state_json={args.state_json}")
    print(f"history_csv={args.history_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
