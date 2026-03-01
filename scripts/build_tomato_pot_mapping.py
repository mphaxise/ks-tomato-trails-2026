#!/usr/bin/env python3
"""Build tomato pot-to-variety mapping for a watering-day run with verifiers."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Set, Tuple


MAPPING_FIELDS = [
    "run_date",
    "row_index",
    "source_asset_id",
    "capture_date",
    "captured_at",
    "photo_url",
    "classification_label",
    "pot_id",
    "packet_number",
    "variety_name",
    "species_common_name",
    "labeling_method",
    "confidence",
    "lifecycle_stage",
    "potting_date",
    "day_one_photo_date",
    "day_since_potting",
    "experiment_day",
    "mapping_status",
    "mapping_note",
]

POT_KEY_RE = re.compile(r"\bpot[_\s-]*tag\s*=\s*([a-z0-9_-]+)\b", re.IGNORECASE)
PACKET_KEY_RE = re.compile(
    r"\bpacket[_\s-]*tag\s*=\s*([a-z0-9_-]+)\b", re.IGNORECASE
)
POT_TEXT_RE = re.compile(r"\b([0-9]{1,3})\s*t\b", re.IGNORECASE)
PACKET_TEXT_RE = re.compile(r"\bpacket[_\s-]*([0-9]{1,3})\b", re.IGNORECASE)
NUMBER_TEXT_RE = re.compile(r"\b([0-9]{1,3})\b")
TOMATO_CAPTION_ID_RE = re.compile(r"\btomato[_\s-]*([0-9]{1,3})\b", re.IGNORECASE)
VARIETY_NAME_ALIASES = {
    "bes yellow latvian": "Iles Yellow Latvian",
    "walmea wild cherry": "Waimea Wild Cherry",
}


def normalize_label(value: str) -> str:
    label = (value or "").strip()
    if label in {"tomato", "non_tomato", "unknown"}:
        return label
    return "unknown"


def normalize_pot_id(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", (raw or "").strip()).upper()
    if not cleaned:
        return ""

    match = re.fullmatch(r"([0-9]{1,3})T?", cleaned)
    if not match:
        return ""

    number = int(match.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def normalize_packet_number(raw: str) -> str:
    cleaned = re.sub(r"[^0-9]", "", (raw or "").strip())
    if not cleaned:
        return ""
    number = int(cleaned)
    if number <= 0:
        return ""
    return str(number)


def canonicalize_variety_name(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    key = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return VARIETY_NAME_ALIASES.get(key, value)


def extract_pot_id(*texts: str) -> str:
    for text in texts:
        value = text or ""
        key_match = POT_KEY_RE.search(value)
        if key_match:
            normalized = normalize_pot_id(key_match.group(1))
            if normalized:
                return normalized

    for text in texts:
        value = text or ""
        match = POT_TEXT_RE.search(value)
        if match:
            normalized = normalize_pot_id(match.group(1))
            if normalized:
                return normalized

    for text in texts:
        value = text or ""
        match = TOMATO_CAPTION_ID_RE.search(value)
        if match:
            normalized = normalize_pot_id(match.group(1))
            if normalized:
                return normalized

    return ""


def extract_packet_number(*texts: str) -> str:
    for text in texts:
        value = text or ""
        key_match = PACKET_KEY_RE.search(value)
        if key_match:
            normalized = normalize_packet_number(key_match.group(1))
            if normalized:
                return normalized

    for text in texts:
        value = text or ""
        match = PACKET_TEXT_RE.search(value)
        if match:
            normalized = normalize_packet_number(match.group(1))
            if normalized:
                return normalized

    return ""


def extract_numeric_candidates(*texts: str) -> List[int]:
    values: List[int] = []
    seen = set()
    for text in texts:
        for raw in NUMBER_TEXT_RE.findall(text or ""):
            number = int(raw)
            if number <= 0 or number in seen:
                continue
            seen.add(number)
            values.append(number)
    return values


def derive_variety_name(row: Dict[str, str]) -> str:
    explicit = (row.get("variety_name", "") or "").strip()
    if explicit and explicit.lower() not in {"unknown", "tomato"}:
        return canonicalize_variety_name(explicit)

    common_name = (row.get("species_common_name", "") or "").strip()
    if common_name and common_name.lower() not in {"tomato", "unknown"}:
        return canonicalize_variety_name(common_name)

    caption = (row.get("caption", "") or "").strip()
    if "|" in caption:
        return canonicalize_variety_name(caption.split("|", 1)[0].strip())
    return ""


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


def pot_number_from_pot_id(pot_id: str) -> int:
    match = re.fullmatch(r"([0-9]{1,3})T", pot_id)
    if not match:
        return 0
    return int(match.group(1))


def build_historical_variety_lookup(
    rows: List[Dict[str, str]], run_date: str
) -> Dict[int, str]:
    lookup: Dict[int, str] = {}
    for row in rows:
        capture_date = (row.get("capture_date", "") or "").strip()
        if not capture_date or capture_date >= run_date:
            continue
        if normalize_label((row.get("classification_label", "") or "").strip()) != "tomato":
            continue

        caption = (row.get("caption", "") or "").strip()
        match = TOMATO_CAPTION_ID_RE.search(caption)
        if not match:
            continue

        pot_number = int(match.group(1))
        variety_name = derive_variety_name(row)
        if not variety_name:
            continue
        lookup[pot_number] = variety_name
    return lookup


def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} is missing a CSV header")
        return list(reader)


def load_series_variety_map(csv_path: Path | None) -> Dict[int, str]:
    if csv_path is None or not csv_path.exists():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} is missing a CSV header")

        mapping: Dict[int, str] = {}
        for row in reader:
            number_text = (row.get("series_number", "") or "").strip()
            variety_name = canonicalize_variety_name(
                (row.get("variety_name", "") or "").strip()
            )
            if not number_text or not variety_name:
                continue
            mapping[int(number_text)] = variety_name
    return mapping


def load_pot_series_overrides(csv_path: Path | None) -> Dict[str, int]:
    if csv_path is None or not csv_path.exists():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} is missing a CSV header")

        mapping: Dict[str, int] = {}
        for row in reader:
            pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
            series_text = (row.get("series_number", "") or "").strip()
            if not pot_id or not series_text:
                continue
            series_number = int(series_text)
            if series_number <= 0:
                continue
            mapping[pot_id] = series_number
    return mapping


def load_baseline_variety_map(csv_path: Path | None) -> Dict[str, str]:
    if csv_path is None or not csv_path.exists():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} is missing a CSV header")

        mapping: Dict[str, str] = {}
        for row in reader:
            pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
            variety_name = canonicalize_variety_name(
                (row.get("variety_name", "") or "").strip()
            )
            if not pot_id or not variety_name:
                continue
            mapping[pot_id] = variety_name
    return mapping


def canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()


def parse_iso_date(value: str, field_name: str) -> date:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"Missing required date: {field_name}")
    return date.fromisoformat(text)


def day_since(start: date, target_iso_date: str) -> int:
    return (date.fromisoformat(target_iso_date) - start).days


def build_mapping(
    rows: List[Dict[str, str]],
    run_date: str,
    expected_pots: int,
    potting_date: str = "2026-02-24",
    day_one_photo_date: str = "2026-02-25",
    lifecycle_stage: str = "sapling",
    assume_sequential_pot_ids: bool = True,
    tomato_only_run: bool = True,
    series_variety_map: Dict[int, str] | None = None,
    pot_series_overrides: Dict[str, int] | None = None,
    baseline_variety_map: Dict[str, str] | None = None,
    baseline_reconcile: bool = True,
) -> Tuple[List[Dict[str, str]], Dict[str, object]]:
    selected: List[Tuple[int, Dict[str, str]]] = [
        (index, row)
        for index, row in enumerate(rows, start=1)
        if (row.get("capture_date", "") or "").strip() == run_date
    ]
    if not selected:
        raise ValueError(f"No rows found for run_date={run_date}")
    series_variety_map = series_variety_map or {}
    pot_series_overrides = pot_series_overrides or {}
    baseline_variety_map = baseline_variety_map or {}
    series_number_by_variety: Dict[str, int] = {
        canonical_key(name): number
        for number, name in series_variety_map.items()
        if canonical_key(name)
    }
    potting_day = parse_iso_date(potting_date, "potting_date")
    day_one_day = parse_iso_date(day_one_photo_date, "day_one_photo_date")

    historical_variety_lookup = build_historical_variety_lookup(rows, run_date)

    mapping_rows: List[Dict[str, str]] = []
    errors: List[str] = []
    warnings: List[str] = []
    label_counts: Counter[str] = Counter()
    tomato_candidate_rows = 0

    pot_to_rows: DefaultDict[str, List[int]] = defaultdict(list)
    pot_to_varieties: DefaultDict[str, Set[str]] = defaultdict(set)
    packet_to_varieties: DefaultDict[str, Set[str]] = defaultdict(set)
    sequential_inferred_rows = 0
    ocr_confirmed_rows = 0
    historical_variety_rows = 0
    pot_override_rows = 0
    skipped_extra_rows = 0
    baseline_applied_rows = 0

    for run_position, (row_index, row) in enumerate(selected, start=1):
        label = normalize_label((row.get("classification_label", "") or "").strip())
        label_counts[label] += 1

        notes = (row.get("notes", "") or "").strip()
        caption = (row.get("caption", "") or "").strip()
        ocr_excerpt = (row.get("ocr_excerpt", "") or "").strip()
        number_candidates = extract_numeric_candidates(notes, caption, ocr_excerpt)

        pot_id = extract_pot_id(
            (row.get("pot_tag", "") or "").strip(),
            notes,
            caption,
            ocr_excerpt,
        )
        inferred_sequential = False
        if (
            not pot_id
            and assume_sequential_pot_ids
            and expected_pots > 0
            and run_position > expected_pots
        ):
            warnings.append(
                f"row {row_index}: skipped extra row beyond expected_pots={expected_pots} with no explicit pot_id"
            )
            skipped_extra_rows += 1
            continue
        if not pot_id and assume_sequential_pot_ids:
            pot_id = f"{run_position}T"
            inferred_sequential = True
            sequential_inferred_rows += 1

        pot_number = pot_number_from_pot_id(pot_id)
        if pot_number and pot_number in number_candidates:
            ocr_confirmed_rows += 1

        packet_number = extract_packet_number(
            (row.get("packet_tag", "") or "").strip(),
            notes,
            caption,
            ocr_excerpt,
        )
        if not packet_number and number_candidates:
            fallback_numbers = [
                number
                for number in number_candidates
                if number != pot_number and number <= 40
            ]
            if fallback_numbers:
                packet_number = str(fallback_numbers[0])

        manual_series_override_applied = False
        if pot_id and pot_id in pot_series_overrides:
            override_number = str(pot_series_overrides[pot_id])
            if packet_number and packet_number != override_number:
                warnings.append(
                    f"row {row_index}: pot {pot_id} override series={override_number} replaces detected series={packet_number}"
                )
            packet_number = override_number
            manual_series_override_applied = True
            pot_override_rows += 1

        baseline_variety = canonicalize_variety_name(
            baseline_variety_map.get(pot_id, "")
        )
        baseline_series = ""
        if baseline_variety:
            baseline_series_number = series_number_by_variety.get(
                canonical_key(baseline_variety), 0
            )
            if baseline_series_number > 0:
                baseline_series = str(baseline_series_number)

        baseline_series_applied = False
        if baseline_series and not manual_series_override_applied:
            if not packet_number:
                packet_number = baseline_series
                baseline_series_applied = True
            elif baseline_reconcile and packet_number != baseline_series:
                warnings.append(
                    f"row {row_index}: baseline series={baseline_series} replaces detected series={packet_number} for pot {pot_id}"
                )
                packet_number = baseline_series
                baseline_series_applied = True

        variety_name = canonicalize_variety_name(derive_variety_name(row))
        series_map_applied = False
        if not variety_name and pot_number in historical_variety_lookup:
            variety_name = historical_variety_lookup[pot_number]
            historical_variety_rows += 1
        if not variety_name and packet_number:
            mapped_name = canonicalize_variety_name(
                series_variety_map.get(int(packet_number), "")
            )
            if mapped_name:
                variety_name = mapped_name
                series_map_applied = True
        if manual_series_override_applied and packet_number:
            override_name = canonicalize_variety_name(
                series_variety_map.get(int(packet_number), "")
            )
            if override_name:
                if variety_name and canonical_key(variety_name) != canonical_key(
                    override_name
                ):
                    warnings.append(
                        f"row {row_index}: pot {pot_id} override variety '{override_name}' replaces detected variety '{variety_name}'"
                    )
                variety_name = override_name
                series_map_applied = True

        baseline_variety_applied = False
        if baseline_variety and not manual_series_override_applied:
            if not variety_name:
                variety_name = baseline_variety
                baseline_variety_applied = True
            elif baseline_reconcile and canonical_key(variety_name) != canonical_key(
                baseline_variety
            ):
                warnings.append(
                    f"row {row_index}: baseline variety '{baseline_variety}' replaces detected variety '{variety_name}' for pot {pot_id}"
                )
                variety_name = baseline_variety
                baseline_variety_applied = True

        if variety_name and packet_number:
            mapped_name = canonicalize_variety_name(
                series_variety_map.get(int(packet_number), "")
            )
            if mapped_name and canonical_key(mapped_name) != canonical_key(variety_name):
                warnings.append(
                    f"row {row_index}: packet_number={packet_number} maps to '{mapped_name}' but row variety is '{variety_name}'"
                )

        is_tomato_candidate = (
            True if tomato_only_run else (label == "tomato" or bool(pot_id))
        )
        if is_tomato_candidate:
            tomato_candidate_rows += 1

        mapping_status = "ok"
        mapping_notes: List[str] = []
        if inferred_sequential:
            mapping_notes.append("pot_id_inferred_from_run_sequence")
        if label != "tomato" and tomato_only_run:
            mapping_notes.append("label_not_tomato_run_assumed_tomato")
        if pot_number and pot_number in number_candidates:
            mapping_notes.append("ocr_confirms_pot_number")
        if variety_name and pot_number in historical_variety_lookup:
            if historical_variety_lookup[pot_number] == variety_name:
                mapping_notes.append("variety_from_historical_pot_mapping")
        if series_map_applied:
            mapping_notes.append("variety_from_series_number_map")
        if manual_series_override_applied:
            mapping_notes.append("series_from_manual_pot_override")
        if baseline_series_applied:
            mapping_notes.append("series_from_baseline_pot_mapping")
        if baseline_variety_applied:
            mapping_notes.append("variety_from_baseline_pot_mapping")

        if not is_tomato_candidate:
            mapping_status = "needs_review"
            mapping_notes.append("row_not_detected_as_tomato")
        else:
            if not pot_id:
                mapping_status = "needs_review"
                mapping_notes.append("missing_pot_id")
                errors.append(
                    f"row {row_index}: tomato row is missing pot_id (expected format like 12T)"
                )
            if not variety_name:
                mapping_status = "needs_review"
                mapping_notes.append("missing_variety_name")
                errors.append(
                    f"row {row_index}: tomato row is missing variety_name/species mapping"
                )

        if baseline_series_applied or baseline_variety_applied:
            baseline_applied_rows += 1

        if pot_id:
            pot_to_rows[pot_id].append(row_index)
            if variety_name:
                pot_to_varieties[pot_id].add(variety_name)
        if packet_number and variety_name:
            packet_to_varieties[packet_number].add(variety_name)

        species_common_name = canonicalize_variety_name(
            (row.get("species_common_name", "") or "").strip()
        )
        if not species_common_name and variety_name:
            species_common_name = variety_name

        mapping_rows.append(
            {
                "run_date": run_date,
                "row_index": str(row_index),
                "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                "capture_date": (row.get("capture_date", "") or "").strip(),
                "captured_at": (row.get("captured_at", "") or "").strip(),
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "classification_label": label,
                "pot_id": pot_id,
                "packet_number": packet_number,
                "variety_name": variety_name,
                "species_common_name": species_common_name,
                "labeling_method": (row.get("labeling_method", "") or "").strip(),
                "confidence": (row.get("confidence", "") or "").strip(),
                "lifecycle_stage": lifecycle_stage,
                "potting_date": potting_date,
                "day_one_photo_date": day_one_photo_date,
                "day_since_potting": str(day_since(potting_day, run_date)),
                "experiment_day": str(day_since(day_one_day, run_date) + 1),
                "mapping_status": mapping_status,
                "mapping_note": "; ".join(mapping_notes),
            }
        )

    duplicate_pots = {pot: idxs for pot, idxs in pot_to_rows.items() if len(idxs) > 1}
    if duplicate_pots:
        for pot, idxs in sorted(duplicate_pots.items()):
            errors.append(f"pot {pot}: duplicate rows {idxs}")

    for pot, varieties in sorted(pot_to_varieties.items()):
        if len(varieties) > 1:
            errors.append(
                f"pot {pot}: conflicting varieties {sorted(varieties)}"
            )

    for packet_number, varieties in sorted(packet_to_varieties.items()):
        if len(varieties) > 1:
            warnings.append(
                f"packet {packet_number}: conflicting varieties {sorted(varieties)}"
            )

    unique_pot_count = len(pot_to_rows)
    if expected_pots > 0 and unique_pot_count != expected_pots:
        errors.append(
            f"unique_pot_count={unique_pot_count} does not match expected_pots={expected_pots}"
        )

    if tomato_candidate_rows != len(selected):
        warnings.append(
            f"run contains non-tomato/unknown rows: tomato_candidates={tomato_candidate_rows} total_rows={len(selected)}"
        )

    report: Dict[str, object] = {
        "run_date": run_date,
        "lifecycle_stage": lifecycle_stage,
        "potting_date": potting_date,
        "day_one_photo_date": day_one_photo_date,
        "day_since_potting": day_since(potting_day, run_date),
        "experiment_day": day_since(day_one_day, run_date) + 1,
        "selected_rows": len(selected),
        "tomato_candidate_rows": tomato_candidate_rows,
        "label_counts": dict(label_counts),
        "expected_pots": expected_pots,
        "unique_pot_count": unique_pot_count,
        "sequential_inferred_rows": sequential_inferred_rows,
        "ocr_confirmed_rows": ocr_confirmed_rows,
        "historical_variety_rows": historical_variety_rows,
        "historical_variety_lookup_size": len(historical_variety_lookup),
        "series_variety_map_size": len(series_variety_map),
        "pot_series_overrides_size": len(pot_series_overrides),
        "pot_override_rows": pot_override_rows,
        "baseline_variety_map_size": len(baseline_variety_map),
        "baseline_applied_rows": baseline_applied_rows,
        "skipped_extra_rows": skipped_extra_rows,
        "missing_pot_rows": [
            int(row["row_index"])
            for row in mapping_rows
            if row["mapping_status"] != "ok" and "missing_pot_id" in row["mapping_note"]
        ],
        "errors": errors,
        "warnings": warnings,
    }
    return mapping_rows, report


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAPPING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build tomato pot-to-variety mapping and verifier report."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Input labeled CSV",
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Run capture date (YYYY-MM-DD). Defaults to latest date in input CSV.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected unique pot count for this run (default: 32).",
    )
    parser.add_argument(
        "--potting-date",
        default="2026-02-24",
        help="Date seedlings were potted into current pots (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--day-one-photo-date",
        default="2026-02-25",
        help="Date of first baseline photo set for day-one indexing (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--lifecycle-stage",
        default="sapling",
        help="Lifecycle stage label for this mapping run (default: sapling).",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help=(
            "Optional one-time tomato number series map CSV with "
            "'series_number,variety_name'."
        ),
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help=(
            "Optional pot-level series override CSV with "
            "'pot_id,series_number'."
        ),
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help=(
            "Optional stable baseline mapping CSV used for automatic pot-level "
            "series/variety reconciliation."
        ),
    )
    parser.add_argument(
        "--baseline-reconcile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When baseline mapping is available, reconcile conflicting detected "
            "series/variety to baseline pot assignments (default: true)."
        ),
    )
    parser.add_argument(
        "--assume-sequential-pot-ids",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "If pot tags are missing, infer pot IDs from row order in the run "
            "(1T..NT). Default: true."
        ),
    )
    parser.add_argument(
        "--tomato-only-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Treat all run rows as tomato candidates. Default: true for the "
            "tomato-only phase."
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Output CSV path for per-row tomato mapping",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_report_latest.json"),
        help="Output JSON path for verifier report",
    )
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Return non-zero when verifier errors are present (default: true).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.input_csv)
    series_variety_map = load_series_variety_map(args.series_map_csv)
    pot_series_overrides = load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(args.baseline_map_csv)
    run_date = derive_run_date(rows, args.run_date)
    mapping_rows, report = build_mapping(
        rows,
        run_date,
        args.expected_pots,
        args.potting_date,
        args.day_one_photo_date,
        args.lifecycle_stage,
        args.assume_sequential_pot_ids,
        args.tomato_only_run,
        series_variety_map,
        pot_series_overrides,
        baseline_variety_map,
        args.baseline_reconcile,
    )
    write_csv(args.output_csv, mapping_rows)
    write_json(args.report_json, report)

    print(f"input_csv={args.input_csv}")
    print(f"run_date={run_date}")
    print(f"lifecycle_stage={report['lifecycle_stage']}")
    print(f"potting_date={report['potting_date']}")
    print(f"day_one_photo_date={report['day_one_photo_date']}")
    print(f"day_since_potting={report['day_since_potting']}")
    print(f"experiment_day={report['experiment_day']}")
    print(f"selected_rows={report['selected_rows']}")
    print(f"unique_pot_count={report['unique_pot_count']}")
    print(f"sequential_inferred_rows={report['sequential_inferred_rows']}")
    print(f"ocr_confirmed_rows={report['ocr_confirmed_rows']}")
    print(f"historical_variety_rows={report['historical_variety_rows']}")
    print(f"series_variety_map_size={report['series_variety_map_size']}")
    print(f"pot_series_overrides_size={report['pot_series_overrides_size']}")
    print(f"pot_override_rows={report['pot_override_rows']}")
    print(f"baseline_variety_map_size={report['baseline_variety_map_size']}")
    print(f"baseline_applied_rows={report['baseline_applied_rows']}")
    print(f"skipped_extra_rows={report['skipped_extra_rows']}")
    print(f"errors={len(report['errors'])}")
    print(f"warnings={len(report['warnings'])}")
    print(f"output_csv={args.output_csv}")
    print(f"report_json={args.report_json}")

    has_errors = bool(report["errors"])
    if args.strict and has_errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
