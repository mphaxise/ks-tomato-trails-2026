#!/usr/bin/env python3
"""Build a tomato-run view page for active tracking."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List

from build_experiment_trails_page import build_page, read_rows


def derive_run_date(rows: List[Dict[str, str]], run_date: str) -> str:
    requested = run_date.strip()
    if requested:
        return requested
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


def read_mapping_rows(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        (row.get("source_asset_id", "") or "").strip(): row
        for row in rows
        if (row.get("source_asset_id", "") or "").strip()
    }


def build_tomato_run_rows(
    rows: List[Dict[str, str]],
    run_date: str,
    mapping_by_asset: Dict[str, Dict[str, str]],
) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    for row in rows:
        if (row.get("capture_date", "") or "").strip() != run_date:
            continue

        row_copy = dict(row)
        row_copy["classification_label"] = "tomato"
        row_copy["species_scientific_name"] = (
            (row_copy.get("species_scientific_name", "") or "").strip()
            or "Solanum lycopersicum"
        )

        mapping = mapping_by_asset.get((row_copy.get("source_asset_id", "") or "").strip())
        if mapping:
            pot_id = (mapping.get("pot_id", "") or "").strip()
            packet_number = (mapping.get("packet_number", "") or "").strip()
            mapped_variety = (mapping.get("variety_name", "") or "").strip()
            if mapped_variety:
                row_copy["variety_name"] = mapped_variety
                if (row_copy.get("species_common_name", "") or "").strip().lower() in {
                    "",
                    "unknown",
                }:
                    row_copy["species_common_name"] = mapped_variety
            elif pot_id:
                row_copy["variety_name"] = f"Unresolved (Pot {pot_id})"
                row_copy["species_common_name"] = "Tomato"

            mapping_note_parts: List[str] = []
            if pot_id:
                mapping_note_parts.append(f"Pot ID: {pot_id}")
            if packet_number:
                mapping_note_parts.append(f"Packet Number: {packet_number}")
            if mapping_note_parts:
                prefix = " | ".join(mapping_note_parts)
                note = (row_copy.get("specific_note", "") or "").strip()
                row_copy["specific_note"] = f"{prefix}. {note}".strip()

        if (row_copy.get("species_common_name", "") or "").strip().lower() in {"", "unknown"}:
            row_copy["species_common_name"] = "Tomato"

        output.append(row_copy)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build tomato-only tracker HTML from labeled CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="CSV containing labeled rows",
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Tomato run date (YYYY-MM-DD). Defaults to latest capture date.",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Optional mapping CSV from build_tomato_pot_mapping.py",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/tomato-trails-view.html"),
        help="Output HTML file",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.input_csv)
    run_date = derive_run_date(rows, args.run_date)
    mapping_by_asset = read_mapping_rows(args.mapping_csv)
    tomato_rows = build_tomato_run_rows(rows, run_date, mapping_by_asset)
    page = build_page(tomato_rows, args.input_csv)
    page = page.replace(
        "K's Experiment Trails 2026: View-Only Catalog",
        f"K's Tomato Trails 2026: Tomato Pots View-Only ({run_date})",
    ).replace(
        "Read-only photo catalog with canonical variety, taxonomy, weather hypothesis, and harvest window fields.",
        "Active tomato-pot run catalog. Non-tomato plants are preserved in the separate snapshot archive.",
    )

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"run_date={run_date}")
    print(f"tomato_rows={len(tomato_rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
