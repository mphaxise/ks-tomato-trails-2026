#!/usr/bin/env python3
"""Build a tomato-run view page for active tracking."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from build_experiment_trails_page import build_page, read_rows
from stable_generated_output import stabilize_rendered_text, write_text_if_changed

VARIETY_NAME_ALIASES = {
    "bes yellow latvian": "Iles Yellow Latvian",
    "walmea wild cherry": "Waimea Wild Cherry",
}

FINAL_STATUS_LABELS = {
    "ready_direct": "Ready (Direct)",
    "ready_auto_resolved": "Ready (Auto-Resolved)",
    "review_needed_pot_id": "Review Needed: Pot ID",
    "review_needed_variety": "Review Needed: Variety",
    "review_needed_mapping": "Review Needed: Mapping",
}


def canonicalize_variety_name(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    key = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return VARIETY_NAME_ALIASES.get(key, value)


def normalize_classification_label(raw: str) -> str:
    label = (raw or "").strip()
    if label in {"tomato", "non_tomato", "unknown"}:
        return label
    return "unknown"


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


def phase_marker_for_run(
    mapping_by_asset: Dict[str, Dict[str, str]], run_date: str
) -> str:
    for row in mapping_by_asset.values():
        row_run_date = (row.get("run_date", "") or row.get("capture_date", "") or "").strip()
        if row_run_date != run_date:
            continue
        phase_name = (row.get("phase_name", "") or "").strip()
        phase_day_label = (row.get("phase_day_label", "") or "").strip()
        if not phase_name:
            continue
        if phase_day_label:
            return f"Phase marker: {phase_name} - {phase_day_label}."
        return f"Phase marker: {phase_name}."
    return ""


def derive_status_fields(
    mapping: Dict[str, str] | None, source_label: str
) -> Tuple[str, str, str, str]:
    if mapping is None:
        if source_label == "tomato":
            final_status = "ready_direct"
            review_stage = "none"
            resolution_source = "direct_detection"
        else:
            final_status = "review_needed_mapping"
            review_stage = "mapping"
            resolution_source = "manual_review"
        return (
            final_status,
            review_stage,
            resolution_source,
            FINAL_STATUS_LABELS[final_status],
        )

    final_status = (mapping.get("final_status", "") or "").strip()
    review_stage = (mapping.get("review_stage", "") or "").strip()
    resolution_source = (mapping.get("resolution_source", "") or "").strip()
    review_label = (mapping.get("review_status_label", "") or "").strip()
    mapping_status = (mapping.get("mapping_status", "") or "").strip()
    mapping_note = (mapping.get("mapping_note", "") or "").strip()

    if not final_status:
        if mapping_status == "ok":
            final_status = "ready_auto_resolved"
            review_stage = "none"
            resolution_source = "mapping_pipeline"
        elif "missing_pot_id" in mapping_note:
            final_status = "review_needed_pot_id"
            review_stage = "capture"
            resolution_source = "manual_review"
        elif "missing_variety_name" in mapping_note:
            final_status = "review_needed_variety"
            review_stage = "ocr"
            resolution_source = "manual_review"
        else:
            final_status = "review_needed_mapping"
            review_stage = "mapping"
            resolution_source = "manual_review"
    if not review_label:
        review_label = FINAL_STATUS_LABELS.get(final_status, "Review Needed: Mapping")
    if not review_stage:
        review_stage = "none" if final_status.startswith("ready_") else "mapping"
    if not resolution_source:
        resolution_source = "direct_detection" if final_status == "ready_direct" else "mapping_pipeline"
    return final_status, review_stage, resolution_source, review_label


def pot_sort_key(value: str) -> Tuple[int, str]:
    matched = re.fullmatch(r"([0-9]{1,3})T", (value or "").strip())
    if not matched:
        return (10**9, value or "")
    return (int(matched.group(1)), value or "")


def build_tomato_run_rows(
    rows: List[Dict[str, str]],
    run_date: str,
    mapping_by_asset: Dict[str, Dict[str, str]],
) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    for row in rows:
        if (row.get("capture_date", "") or "").strip() != run_date:
            continue

        label = normalize_classification_label((row.get("classification_label", "") or ""))
        mapping = mapping_by_asset.get((row.get("source_asset_id", "") or "").strip())
        if label == "non_tomato" and mapping is None:
            continue
        if label not in {"tomato", "unknown"} and mapping is None:
            continue
        if label == "unknown" and mapping is None:
            # Unknown run rows without mapping are typically context frames, not pot records.
            continue

        row_copy = dict(row)
        final_status, review_stage, resolution_source, review_label = (
            derive_status_fields(mapping, label)
        )
        row_copy["final_status"] = final_status
        row_copy["review_stage"] = review_stage
        row_copy["resolution_source"] = resolution_source
        row_copy["review_status_label"] = review_label
        row_copy["context_id"] = (mapping.get("context_id", "") or "").strip() if mapping else ""
        row_copy["classification_label"] = (
            "tomato"
            if final_status in {"ready_direct", "ready_auto_resolved"}
            else "unknown"
        )
        row_copy["variety_name"] = canonicalize_variety_name(
            (row_copy.get("variety_name", "") or "").strip()
        )
        row_copy["species_scientific_name"] = (
            (row_copy.get("species_scientific_name", "") or "").strip()
            or "Solanum lycopersicum"
        )

        if mapping:
            pot_id = (mapping.get("pot_id", "") or "").strip()
            packet_number = (mapping.get("packet_number", "") or "").strip()
            row_copy["pot_id"] = pot_id
            mapped_variety = canonicalize_variety_name(
                (mapping.get("variety_name", "") or "").strip()
            )
            if mapped_variety:
                row_copy["variety_name"] = mapped_variety
            elif pot_id:
                row_copy["variety_name"] = f"Unresolved (Pot {pot_id})"

            mapping_note_parts: List[str] = []
            if pot_id:
                mapping_note_parts.append(f"Pot ID: {pot_id}")
            if packet_number:
                mapping_note_parts.append(f"Packet Number: {packet_number}")
            mapping_note_parts.append(f"Status: {review_label}")
            if review_stage and review_stage != "none":
                mapping_note_parts.append(f"Review Stage: {review_stage}")
            if resolution_source:
                mapping_note_parts.append(
                    f"Resolution Source: {resolution_source.replace('_', ' ')}"
                )
            if row_copy.get("context_id", ""):
                mapping_note_parts.append(f"Context: {row_copy['context_id']}")
            if mapping_note_parts:
                prefix = " | ".join(mapping_note_parts)
                note = (row_copy.get("specific_note", "") or "").strip()
                row_copy["specific_note"] = f"{prefix}. {note}".strip()

        row_copy["species_common_name"] = "Tomato"

        output.append(row_copy)

    # Keep the latest tomato gallery stable by canonical pot order rather than source row order.
    output.sort(
        key=lambda row: (
            pot_sort_key((row.get("pot_id", "") or "").strip()),
            (row.get("row_index", "") or "").strip(),
            (row.get("source_asset_id", "") or "").strip(),
        )
    )
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
    phase_marker = phase_marker_for_run(mapping_by_asset, run_date)
    page = build_page(tomato_rows, args.input_csv)
    page = page.replace(
        "<title>K's Experiment Trails - View-Only Catalog</title>",
        f"<title>K's Tomato Trails 2026: Tomato Pots View-Only ({run_date})</title>",
    ).replace(
        "K's Experiment Trails 2026: View-Only Catalog",
        f"K's Tomato Trails 2026: Tomato Pots View-Only ({run_date})",
    ).replace(
        "Read-only photo catalog with canonical variety, taxonomy, weather hypothesis, and harvest window fields.",
        (
            "Active tomato-pot run catalog. Non-tomato plants are preserved in the separate snapshot archive."
            + (f" {phase_marker}" if phase_marker else "")
        ),
    )

    page = stabilize_rendered_text(args.output_html, page)
    write_text_if_changed(args.output_html, page)

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"run_date={run_date}")
    print(f"tomato_rows={len(tomato_rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
