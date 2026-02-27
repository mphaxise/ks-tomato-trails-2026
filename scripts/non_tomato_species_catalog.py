#!/usr/bin/env python3
"""Build and maintain a separate local non-tomato species catalog."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class SpeciesMatch:
    common_name: str
    scientific_name: str
    confidence: float
    method: str


SPECIES_RULES: List[Tuple[re.Pattern[str], SpeciesMatch]] = [
    (
        re.compile(r"\bcollard(s)?\b", re.IGNORECASE),
        SpeciesMatch(
            "Collards",
            "Brassica oleracea var. viridis",
            0.95,
            "caption_keyword",
        ),
    ),
    (
        re.compile(r"\bleek(s)?\b", re.IGNORECASE),
        SpeciesMatch("Leek", "Allium porrum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\ballium\\s+porrum\b", re.IGNORECASE),
        SpeciesMatch("Leek", "Allium porrum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bspinach\b", re.IGNORECASE),
        SpeciesMatch("Spinach", "Spinacia oleracea", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bspinacia\b", re.IGNORECASE),
        SpeciesMatch("Spinach", "Spinacia oleracea", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bcabbage\b", re.IGNORECASE),
        SpeciesMatch(
            "Red Cabbage",
            "Brassica oleracea var. capitata",
            0.95,
            "caption_keyword",
        ),
    ),
    (
        re.compile(r"\bchard\b", re.IGNORECASE),
        SpeciesMatch(
            "Swiss Chard",
            "Beta vulgaris subsp. vulgaris",
            0.9,
            "caption_keyword",
        ),
    ),
    (
        re.compile(r"\bpea(s)?\b", re.IGNORECASE),
        SpeciesMatch("Pea", "Pisum sativum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bpisum\b", re.IGNORECASE),
        SpeciesMatch("Pea", "Pisum sativum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bturnip(s)?\b", re.IGNORECASE),
        SpeciesMatch(
            "Turnip",
            "Brassica rapa subsp. rapa",
            0.95,
            "caption_keyword",
        ),
    ),
    (
        re.compile(r"\bbrassica\\s+rapa\b", re.IGNORECASE),
        SpeciesMatch("Turnip", "Brassica rapa", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bmarigold(s)?\b", re.IGNORECASE),
        SpeciesMatch("Marigold", "Tagetes spp.", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bbasil\b", re.IGNORECASE),
        SpeciesMatch("Basil", "Ocimum basilicum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bpepper(s)?\b", re.IGNORECASE),
        SpeciesMatch("Pepper", "Capsicum annuum", 0.9, "caption_keyword"),
    ),
    (
        re.compile(r"\bcucumber(s)?\b", re.IGNORECASE),
        SpeciesMatch("Cucumber", "Cucumis sativus", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bsquash\b", re.IGNORECASE),
        SpeciesMatch("Squash", "Cucurbita spp.", 0.85, "caption_keyword"),
    ),
    (
        re.compile(r"\bzucchini\b", re.IGNORECASE),
        SpeciesMatch("Zucchini", "Cucurbita pepo", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\blettuce\b", re.IGNORECASE),
        SpeciesMatch("Lettuce", "Lactuca sativa", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bcilantro\b", re.IGNORECASE),
        SpeciesMatch("Cilantro", "Coriandrum sativum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bparsley\b", re.IGNORECASE),
        SpeciesMatch("Parsley", "Petroselinum crispum", 0.95, "caption_keyword"),
    ),
    (
        re.compile(r"\bnasturtium\b", re.IGNORECASE),
        SpeciesMatch("Nasturtium", "Tropaeolum majus", 0.95, "caption_keyword"),
    ),
]


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    return re.sub(r"_+", "_", cleaned).strip("_")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_tomato_lookup(varieties_json: Path) -> Dict[str, str]:
    raw = json.loads(varieties_json.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected array in {varieties_json}")

    lookup: Dict[str, str] = {}

    def add_key(value: str) -> None:
        normalized = slugify(value)
        if normalized:
            lookup[normalized] = normalized

    for item in raw:
        if not isinstance(item, dict):
            continue
        variety_id = str(item.get("id", "")).strip()
        variety_name = str(item.get("name", "")).strip()
        if not variety_id and not variety_name:
            continue
        if variety_id:
            add_key(variety_id)
            add_key(variety_id.replace("_", " "))
        if variety_name:
            add_key(variety_name)

    if not lookup:
        raise ValueError(f"No tomato varieties loaded from {varieties_json}")
    return lookup


def parse_iso_datetime_to_date(value: str) -> str:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return date.fromisoformat(text[:10]).isoformat()


def derive_capture_date(row: Dict[str, str]) -> str:
    explicit = (row.get("capture_date", "") or "").strip()
    if explicit:
        return date.fromisoformat(explicit).isoformat()

    for field in ("captured_at", "uploaded_at"):
        candidate = (row.get(field, "") or "").strip()
        if candidate:
            return parse_iso_datetime_to_date(candidate)

    raise ValueError("Missing capture_date and no captured_at/uploaded_at fallback")


def build_record_hash(source_url: str, captured_at: str, caption: str) -> str:
    key = f"{source_url}|{captured_at}|{caption}".encode("utf-8")
    return hashlib.sha1(key).hexdigest()


def derive_variety_name(caption: str, explicit_variety: str) -> str:
    value = explicit_variety.strip()
    if value:
        return value
    text = caption.strip()
    if "|" in text:
        return text.split("|", 1)[0].strip()
    return text


def looks_like_tomato(caption: str, notes: str, tomato_lookup: Dict[str, str]) -> bool:
    del notes  # Notes can mention nearby tomatoes; use caption-only tomato detection.
    text = caption.strip()
    if not text:
        return False
    if re.search(r"\btomato(es)?\b", text, flags=re.IGNORECASE):
        return True

    if "|" in caption:
        first_token = caption.split("|", 1)[0].strip()
        if slugify(first_token) in tomato_lookup:
            return True

    normalized = slugify(text)
    for key in tomato_lookup:
        if key and re.search(rf"\b{re.escape(key)}\b", normalized):
            return True
    return False


def classify_species(caption: str, notes: str) -> SpeciesMatch:
    text = f"{caption}\n{notes}".strip()
    for pattern, match in SPECIES_RULES:
        if pattern.search(text):
            return match
    return SpeciesMatch("unknown", "unknown", 0.3, "unresolved_manual_needed")


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS non_tomato_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_hash TEXT NOT NULL UNIQUE,
            source_platform TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_asset_id TEXT NOT NULL,
            caption TEXT NOT NULL,
            capture_date TEXT NOT NULL,
            captured_at TEXT,
            uploaded_at TEXT,
            timezone TEXT,
            latitude TEXT,
            longitude TEXT,
            device_model TEXT,
            species_common_name TEXT NOT NULL,
            variety_name TEXT,
            species_scientific_name TEXT NOT NULL,
            specific_note TEXT,
            weather_hypothesis TEXT,
            expected_harvest_window TEXT,
            classification_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            labeling_method TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    ensure_schema_columns(conn)
    conn.commit()


def ensure_schema_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(non_tomato_observations)").fetchall()
    }
    required = {
        "variety_name": "TEXT",
        "specific_note": "TEXT",
        "weather_hypothesis": "TEXT",
        "expected_harvest_window": "TEXT",
    }
    for column, sql_type in required.items():
        if column not in existing:
            conn.execute(
                f"ALTER TABLE non_tomato_observations ADD COLUMN {column} {sql_type}"
            )


def upsert_non_tomato_row(conn: sqlite3.Connection, row: Dict[str, str]) -> str:
    existing = conn.execute(
        "SELECT id FROM non_tomato_observations WHERE record_hash = ?",
        (row["record_hash"],),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE non_tomato_observations
            SET source_platform = ?,
                source_url = ?,
                source_asset_id = ?,
                caption = ?,
                capture_date = ?,
                captured_at = ?,
                uploaded_at = ?,
                timezone = ?,
                latitude = ?,
                longitude = ?,
                device_model = ?,
                species_common_name = ?,
                variety_name = ?,
                species_scientific_name = ?,
                specific_note = ?,
                weather_hypothesis = ?,
                expected_harvest_window = ?,
                classification_label = ?,
                confidence = ?,
                labeling_method = ?,
                notes = ?,
                updated_at = ?
            WHERE record_hash = ?
            """,
            (
                row["source_platform"],
                row["source_url"],
                row["source_asset_id"],
                row["caption"],
                row["capture_date"],
                row["captured_at"],
                row["uploaded_at"],
                row["timezone"],
                row["latitude"],
                row["longitude"],
                row["device_model"],
                row["species_common_name"],
                row["variety_name"],
                row["species_scientific_name"],
                row["specific_note"],
                row["weather_hypothesis"],
                row["expected_harvest_window"],
                row["classification_label"],
                row["confidence"],
                row["labeling_method"],
                row["notes"],
                row["updated_at"],
                row["record_hash"],
            ),
        )
        return "updated"

    conn.execute(
        """
        INSERT INTO non_tomato_observations (
            record_hash,
            source_platform,
            source_url,
            source_asset_id,
            caption,
            capture_date,
            captured_at,
            uploaded_at,
            timezone,
            latitude,
            longitude,
            device_model,
            species_common_name,
            variety_name,
            species_scientific_name,
            specific_note,
            weather_hypothesis,
            expected_harvest_window,
            classification_label,
            confidence,
            labeling_method,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["record_hash"],
            row["source_platform"],
            row["source_url"],
            row["source_asset_id"],
            row["caption"],
            row["capture_date"],
            row["captured_at"],
            row["uploaded_at"],
            row["timezone"],
            row["latitude"],
            row["longitude"],
            row["device_model"],
            row["species_common_name"],
            row["variety_name"],
            row["species_scientific_name"],
            row["specific_note"],
            row["weather_hypothesis"],
            row["expected_harvest_window"],
            row["classification_label"],
            row["confidence"],
            row["labeling_method"],
            row["notes"],
            row["created_at"],
            row["updated_at"],
        ),
    )
    return "inserted"


def catalog_non_tomato_rows(
    input_csv: Path,
    db_path: Path,
    varieties_json: Path,
) -> Dict[str, int]:
    tomato_lookup = load_tomato_lookup(varieties_json)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{input_csv} is missing a CSV header")
        rows = list(reader)

    with sqlite3.connect(db_path) as conn:
        initialize_database(conn)
        inserted = 0
        updated = 0
        skipped_tomato = 0

        for index, raw in enumerate(rows, start=2):
            if None in raw:
                raise ValueError(f"{input_csv}:{index} -> Malformed CSV row (extra columns)")
            if any(value is None for value in raw.values()):
                raise ValueError(
                    f"{input_csv}:{index} -> Malformed CSV row (missing columns)"
                )

            def cell(key: str) -> str:
                return (raw.get(key, "") or "").strip()

            caption = cell("caption")
            if not caption:
                raise ValueError(f"{input_csv}:{index} -> Missing caption")

            notes = cell("notes")
            label_input = cell("classification_label").lower()
            if label_input == "tomato":
                skipped_tomato += 1
                continue
            if label_input not in {"non_tomato", "unknown", ""}:
                label_input = "unknown"

            if label_input != "non_tomato" and looks_like_tomato(caption, notes, tomato_lookup):
                skipped_tomato += 1
                continue

            source_url = cell("photo_url") or cell("source_url")
            if not source_url:
                raise ValueError(f"{input_csv}:{index} -> Missing photo_url/source_url")

            source_asset_id = cell("source_asset_id")
            if not source_asset_id:
                source_asset_id = f"manual_{index}_{hashlib.sha1(source_url.encode('utf-8')).hexdigest()[:10]}"

            captured_at = cell("captured_at")
            uploaded_at = cell("uploaded_at")
            capture_date = derive_capture_date(raw)
            species = classify_species(caption, notes)
            species_common_name = cell("species_common_name") or species.common_name
            species_scientific_name = (
                cell("species_scientific_name") or species.scientific_name
            )
            confidence = cell("confidence")
            if not confidence:
                confidence = str(species.confidence)
            labeling_method = cell("labeling_method") or species.method
            variety_name = derive_variety_name(caption, cell("variety_name"))
            specific_note = cell("specific_note")
            weather_hypothesis = cell("weather_hypothesis")
            expected_harvest_window = cell("expected_harvest_window")
            now = iso_now()
            record_hash = build_record_hash(source_url, captured_at, caption)

            result = upsert_non_tomato_row(
                conn,
                {
                    "record_hash": record_hash,
                    "source_platform": cell("source_platform") or "google_photos",
                    "source_url": source_url,
                    "source_asset_id": source_asset_id,
                    "caption": caption,
                    "capture_date": capture_date,
                    "captured_at": captured_at,
                    "uploaded_at": uploaded_at,
                    "timezone": cell("timezone"),
                    "latitude": cell("latitude"),
                    "longitude": cell("longitude"),
                    "device_model": cell("device_model"),
                    "species_common_name": species_common_name,
                    "variety_name": variety_name,
                    "species_scientific_name": species_scientific_name,
                    "specific_note": specific_note,
                    "weather_hypothesis": weather_hypothesis,
                    "expected_harvest_window": expected_harvest_window,
                    "classification_label": "non_tomato",
                    "confidence": confidence,
                    "labeling_method": labeling_method,
                    "notes": notes,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            if result == "inserted":
                inserted += 1
            else:
                updated += 1

        conn.commit()

    return {
        "processed_rows": len(rows),
        "non_tomato_rows": inserted + updated,
        "inserted": inserted,
        "updated": updated,
        "skipped_tomato": skipped_tomato,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Catalog non-tomato photo rows into a separate local SQLite DB."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="CSV with mixed photo rows (tomato and non-tomato)",
    )
    parser.add_argument(
        "--db-path",
        default=Path("local/non_tomato_species/non_tomato_species.db"),
        type=Path,
        help="SQLite DB path for separate non-tomato catalog",
    )
    parser.add_argument(
        "--varieties",
        default=Path("data/varieties.json"),
        type=Path,
        help="Tomato varieties JSON used to filter tomato photos",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stats = catalog_non_tomato_rows(args.input, args.db_path, args.varieties)
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"db_path={args.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
