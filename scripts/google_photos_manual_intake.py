#!/usr/bin/env python3
"""Normalize manual Google Photos baseline rows into V1 intake records."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

OUTPUT_FIELDS = [
    "variety_name",
    "plant_id_or_pot_id",
    "photo",
    "capture_date",
    "seed_source_or_packet_name",
    "notes",
    "source_platform",
    "source_asset_id",
    "source_url",
    "captured_at",
    "uploaded_at",
    "timezone",
    "latitude",
    "longitude",
    "device_model",
    "inferred_variety_id",
    "inferred_plant_id",
]


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    return re.sub(r"_+", "_", cleaned).strip("_")


def load_variety_lookup(path: Path) -> Dict[str, Tuple[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected array in {path}")

    lookup: Dict[str, Tuple[str, str]] = {}

    def add_key(key: str, value: Tuple[str, str]) -> None:
        normalized = slugify(key)
        if normalized and normalized not in lookup:
            lookup[normalized] = value

    for item in raw:
        if not isinstance(item, dict):
            continue
        variety_id = str(item.get("id", "")).strip()
        variety_name = str(item.get("name", "")).strip()
        if not variety_id or not variety_name:
            continue
        pair = (variety_id, variety_name)
        add_key(variety_id, pair)
        add_key(variety_name, pair)
        add_key(variety_id.replace("_", " "), pair)

    if not lookup:
        raise ValueError(f"No valid variety records found in {path}")
    return lookup


def resolve_variety(token: str, lookup: Dict[str, Tuple[str, str]]) -> Tuple[str, str]:
    normalized = slugify(token)
    if normalized in lookup:
        return lookup[normalized]
    raise ValueError(f"Unknown variety '{token}'")


def parse_caption(caption: str) -> Tuple[str, str, str, str]:
    parts = [part.strip() for part in caption.split("|")]
    if len(parts) < 3:
        raise ValueError(
            "Caption must use '<variety> | <plant/pot id> | <seed source or unknown>'"
        )

    variety_token = parts[0]
    plant_id = parts[1]
    seed_source = parts[2] or "unknown"
    notes_from_caption = " | ".join(parts[3:]).strip()

    if not variety_token:
        raise ValueError("Caption is missing variety value")
    if not plant_id:
        raise ValueError("Caption is missing plant/pot id")

    return variety_token, plant_id, seed_source, notes_from_caption


def parse_iso_datetime_to_date(value: str) -> str:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return date.fromisoformat(text[:10]).isoformat()


def derive_capture_date(row: Dict[str, str]) -> str:
    explicit = row.get("capture_date", "").strip()
    if explicit:
        return date.fromisoformat(explicit).isoformat()

    for fallback_field in ("captured_at", "uploaded_at"):
        candidate = row.get(fallback_field, "").strip()
        if candidate:
            return parse_iso_datetime_to_date(candidate)

    raise ValueError("Missing capture_date (and no captured_at/uploaded_at fallback)")


def make_asset_id(source_url: str, row_number: int) -> str:
    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
    return f"manual_{row_number}_{digest}"


def normalize_row(
    row: Dict[str, str],
    row_number: int,
    variety_lookup: Dict[str, Tuple[str, str]],
    default_album_url: str = "",
) -> Dict[str, str]:
    if None in row:
        raise ValueError("Malformed CSV row (too many columns)")
    if any(value is None for value in row.values()):
        raise ValueError("Malformed CSV row (missing one or more columns)")

    def cell(key: str) -> str:
        return (row.get(key, "") or "").strip()

    source_url = cell("photo_url") or cell("source_url") or default_album_url
    if not source_url:
        raise ValueError("Missing photo_url/source_url (and no default album URL)")

    caption = cell("caption")
    if not caption:
        raise ValueError("Missing caption")

    variety_token, plant_id, seed_source, caption_notes = parse_caption(caption)
    variety_id, variety_name = resolve_variety(variety_token, variety_lookup)
    capture_date = derive_capture_date(row)

    notes_bits = [cell("notes"), caption_notes]
    notes = "; ".join(bit for bit in notes_bits if bit)

    source_asset_id = cell("source_asset_id") or make_asset_id(source_url, row_number)

    return {
        "variety_name": variety_name,
        "plant_id_or_pot_id": plant_id,
        "photo": source_url,
        "capture_date": capture_date,
        "seed_source_or_packet_name": seed_source,
        "notes": notes,
        "source_platform": "google_photos",
        "source_asset_id": source_asset_id,
        "source_url": source_url,
        "captured_at": cell("captured_at"),
        "uploaded_at": cell("uploaded_at"),
        "timezone": cell("timezone"),
        "latitude": cell("latitude"),
        "longitude": cell("longitude"),
        "device_model": cell("device_model"),
        "inferred_variety_id": variety_id,
        "inferred_plant_id": plant_id,
    }


def run_pipeline(
    input_csv: Path,
    output_csv: Path,
    varieties_json: Path,
    default_album_url: str = "",
) -> int:
    variety_lookup = load_variety_lookup(varieties_json)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{input_csv} is missing a CSV header")
        rows = list(reader)

    normalized_rows: List[Dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        try:
            normalized_rows.append(
                normalize_row(row, index, variety_lookup, default_album_url)
            )
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"{input_csv}:{index} -> {exc}") from exc

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(normalized_rows)

    return len(normalized_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize manual Google Photos baseline intake CSV for V1."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input CSV with photo_url + caption rows",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output CSV path for normalized baseline rows",
    )
    parser.add_argument(
        "--varieties",
        default=Path("data/varieties.json"),
        type=Path,
        help="Path to variety registry JSON",
    )
    parser.add_argument(
        "--album-url",
        default="",
        help=(
            "Default shared album URL used when a row does not include photo_url/source_url"
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    row_count = run_pipeline(args.input, args.output, args.varieties, args.album_url)
    print(f"normalized_rows={row_count}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
