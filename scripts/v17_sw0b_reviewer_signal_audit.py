#!/usr/bin/env python3
"""Sprint 0b: classify hard-queue rows by reviewer signal quality."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def parse_pot_number(pot_id: str) -> int:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return 0
    return int(matched.group(1))


def parse_numbers(raw: str) -> List[int]:
    out: List[int] = []
    seen = set()
    for token in re.findall(r"\b([0-9]{1,3})\b", raw or ""):
        value = int(token)
        if value <= 0 or value > 99 or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def classify_signal_tier(
    *,
    matched_variant_count: int,
    suggested_pot_id: str,
    ensemble_numbers_detected: str,
) -> Tuple[str, str]:
    if matched_variant_count <= 0:
        return (
            "TYPE_III",
            "OCR Match Variants is 0; suggestion is sequence/continuity placeholder",
        )

    pot_number = parse_pot_number(suggested_pot_id)
    numbers = set(parse_numbers(ensemble_numbers_detected))
    if pot_number > 0 and pot_number in numbers:
        return (
            "TYPE_I",
            "Detected numbers include suggested pot number",
        )

    return (
        "TYPE_II",
        "OCR produced numeric tokens but they do not support suggested pot",
    )


def build_audit_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        pot_id = (row.get("pot_id", "") or "").strip()
        matched_variant_count = parse_int(row.get("matched_variant_count", "0") or "0", default=0)
        ensemble_numbers_detected = (row.get("ensemble_numbers_detected", "") or "").strip()
        numbers = parse_numbers(ensemble_numbers_detected)
        signal_tier, signal_reason = classify_signal_tier(
            matched_variant_count=matched_variant_count,
            suggested_pot_id=pot_id,
            ensemble_numbers_detected=ensemble_numbers_detected,
        )
        out.append(
            {
                "run_date": (row.get("run_date", "") or "").strip(),
                "row_index": (row.get("row_index", "") or "").strip(),
                "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                "pot_id": pot_id,
                "pot_number": parse_pot_number(pot_id),
                "matched_variant_count": matched_variant_count,
                "ensemble_numbers_detected": ensemble_numbers_detected,
                "numbers_detected_count": len(numbers),
                "signal_tier": signal_tier,
                "signal_reason": signal_reason,
            }
        )
    return out


def build_summary(rows: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(rows)
    tier_counts = Counter((row.get("signal_tier", "") or "") for row in rows)
    by_run: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        run_date = str(row.get("run_date", "") or "")
        tier = str(row.get("signal_tier", "") or "")
        by_run[run_date][tier] += 1

    tier_percentages = {
        tier: round((count / total) * 100.0, 2) if total else 0.0
        for tier, count in sorted(tier_counts.items())
    }

    placeholder_rows = tier_counts.get("TYPE_III", 0)
    return {
        "total_rows": total,
        "signal_tier_counts": dict(sorted(tier_counts.items())),
        "signal_tier_percentages": tier_percentages,
        "placeholder_row_count": placeholder_rows,
        "placeholder_row_percent": round((placeholder_rows / total) * 100.0, 2) if total else 0.0,
        "by_run_date": {run_date: dict(sorted(counts.items())) for run_date, counts in sorted(by_run.items())},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify hard queue rows by reviewer signal quality tiers.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/manual_label_queue.csv"),
        help="Input hard-row queue CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/v1_7/sw0b_signal_quality_audit.csv"),
        help="Detailed per-row signal classification output.",
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("data/research/v1_7/sw0b_signal_quality_summary.json"),
        help="Summary counts/percentages JSON output.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_csv_rows(args.input_csv)
    audit_rows = build_audit_rows(rows)
    summary = build_summary(audit_rows)

    write_csv(
        args.output_csv,
        audit_rows,
        fieldnames=[
            "run_date",
            "row_index",
            "source_asset_id",
            "pot_id",
            "pot_number",
            "matched_variant_count",
            "ensemble_numbers_detected",
            "numbers_detected_count",
            "signal_tier",
            "signal_reason",
        ],
    )

    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"output_csv={args.output_csv}")
    print(f"output_summary_json={args.output_summary_json}")
    print(f"signal_tier_counts={summary['signal_tier_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
