#!/usr/bin/env python3
"""Auto-label non-tomato species from image packet text using OCR."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

NON_TOMATO_KEYWORDS: List[Tuple[re.Pattern[str], str, str, float]] = [
    (re.compile(r"\bcollard(s)?\b"), "Collards", "Brassica oleracea var. viridis", 0.95),
    (re.compile(r"\bbrassica\s+oleracea\b"), "Collards", "Brassica oleracea", 0.95),
    (re.compile(r"\bleek(s)?\b"), "Leek", "Allium porrum", 0.95),
    (re.compile(r"\ballium\s+porrum\b"), "Leek", "Allium porrum", 0.95),
    (re.compile(r"\bspinach\b"), "Spinach", "Spinacia oleracea", 0.95),
    (re.compile(r"\bspinacia\b"), "Spinach", "Spinacia oleracea", 0.95),
    (re.compile(r"\bkale\b"), "Kale", "Brassica napus", 0.95),
    (re.compile(r"\bbrassica\s+napus\b"), "Kale", "Brassica napus", 0.95),
    (re.compile(r"\bcabbage\b"), "Red Cabbage", "Brassica oleracea var. capitata", 0.95),
    (re.compile(r"\bchard\b"), "Swiss Chard", "Beta vulgaris subsp. vulgaris", 0.9),
    (re.compile(r"\bpea(s)?\b"), "Pea", "Pisum sativum", 0.95),
    (re.compile(r"\bpisum\b"), "Pea", "Pisum sativum", 0.95),
    (re.compile(r"\bturnip(s)?\b"), "Turnip", "Brassica rapa subsp. rapa", 0.95),
    (re.compile(r"\bbrassica\s+rapa\b"), "Turnip", "Brassica rapa", 0.95),
    (re.compile(r"\blettuce\b"), "Lettuce", "Lactuca sativa", 0.95),
    (re.compile(r"\bbasil\b"), "Basil", "Ocimum basilicum", 0.95),
    (re.compile(r"\bpepper(s)?\b"), "Pepper", "Capsicum annuum", 0.9),
    (re.compile(r"\bcucumber(s)?\b"), "Cucumber", "Cucumis sativus", 0.95),
    (re.compile(r"\bcilantro\b"), "Cilantro", "Coriandrum sativum", 0.95),
    (re.compile(r"\bparsley\b"), "Parsley", "Petroselinum crispum", 0.95),
    (re.compile(r"\bkale\b"), "Kale", "Brassica oleracea var. sabellica", 0.95),
]

TOMATO_KEYWORDS = [
    re.compile(r"\btomato(es)?\b"),
    re.compile(r"\bstupice\b"),
    re.compile(r"\bglacier\b"),
    re.compile(r"\bsiletz\b"),
    re.compile(r"\blegend\b"),
    re.compile(r"\bsungold\b"),
    re.compile(r"\bearly\s+girl\b"),
    re.compile(r"\bjuliet\b"),
    re.compile(r"\bblack\s+krim\b"),
    re.compile(r"\bsan\s+marzano\b"),
    re.compile(r"\bbrandywine\b"),
    re.compile(r"\bcherokee\s+purple\b"),
    re.compile(r"\bsunset\b"),
    re.compile(r"\btomatofest\b"),
    re.compile(r"\bheinz\b"),
    re.compile(r"\btrifel+e\b"),
    re.compile(r"\bjapanese\s+black\b"),
    re.compile(r"\bsan\s+francisco\s+fog\b"),
    re.compile(r"\bbes\s+yellow\s+latvian\b"),
    re.compile(r"\btaxi\b"),
    re.compile(r"\bnikolayev\s+yellow\s+cherry\b"),
    re.compile(r"\bsunset'?s\s+red\s+horizon\b"),
    re.compile(r"\bwalmea\s+wild\s+cherry\b"),
    re.compile(r"\bsasha\s+altai\b"),
    re.compile(r"\bazoychka\b"),
    re.compile(r"\bgold\s+dust\b"),
]

OUTPUT_FIELDS = [
    "photo_url",
    "caption",
    "capture_date",
    "captured_at",
    "uploaded_at",
    "timezone",
    "latitude",
    "longitude",
    "device_model",
    "notes",
    "source_asset_id",
    "source_platform",
    "species_common_name",
    "variety_name",
    "species_scientific_name",
    "specific_note",
    "weather_hypothesis",
    "expected_harvest_window",
    "classification_label",
    "confidence",
    "labeling_method",
    "ocr_excerpt",
]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def derive_variety_name(caption: str) -> str:
    text = (caption or "").strip()
    if not text:
        return ""
    if "|" in text:
        return text.split("|", 1)[0].strip()
    return text


def ocr_file_text(image_path: Path, psm: str) -> str:
    try:
        result = subprocess.run(
            ["tesseract", str(image_path), "stdout", "--psm", psm],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    return re.sub(r"\s+", " ", result.stdout).strip()


def extract_ocr_text(image_paths: Iterable[Path], psm_modes: Tuple[str, ...]) -> str:
    texts: List[str] = []
    seen = set()
    for image_path in image_paths:
        for psm in psm_modes:
            text = ocr_file_text(image_path, psm)
            normalized = normalize_text(text)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            texts.append(text)
    return " | ".join(texts)


def load_manual_overrides(overrides_csv: Path | None) -> Dict[int, Dict[str, str]]:
    if overrides_csv is None or not overrides_csv.exists():
        return {}
    with overrides_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    overrides: Dict[int, Dict[str, str]] = {}
    for raw in rows:
        row_index_text = (raw.get("row_index", "") or "").strip()
        if not row_index_text:
            continue
        row_index = int(row_index_text)
        overrides[row_index] = {key: (value or "").strip() for key, value in raw.items()}
    return overrides


def apply_manual_override(
    row_index: int,
    source_asset_id: str,
    output_row: Dict[str, str],
    overrides: Dict[int, Dict[str, str]],
) -> Dict[str, str]:
    override = overrides.get(row_index)
    if not override:
        return output_row

    expected_asset_id = (override.get("source_asset_id", "") or "").strip()
    if expected_asset_id and expected_asset_id != source_asset_id:
        print(
            f"row={row_index} override_skipped=asset_mismatch "
            f"expected={expected_asset_id} actual={source_asset_id}"
        )
        return output_row

    for field in (
        "classification_label",
        "species_common_name",
        "variety_name",
        "species_scientific_name",
        "specific_note",
        "weather_hypothesis",
        "expected_harvest_window",
        "confidence",
        "labeling_method",
        "caption",
    ):
        value = (override.get(field, "") or "").strip()
        if value:
            output_row[field] = value

    notes_append = (override.get("notes_append", "") or "").strip()
    if notes_append:
        output_row["notes"] = (
            f"{output_row.get('notes', '').strip()}; {notes_append}".strip("; ").strip()
        )

    override_excerpt = (override.get("ocr_excerpt", "") or "").strip()
    if override_excerpt:
        output_row["ocr_excerpt"] = override_excerpt

    if not output_row.get("labeling_method", "").strip():
        output_row["labeling_method"] = "manual_override"

    return output_row


def classify_from_text(ocr_text: str) -> Dict[str, str]:
    text = normalize_text(ocr_text)
    if not text:
        return {
            "classification_label": "unknown",
            "species_common_name": "unknown",
            "species_scientific_name": "unknown",
            "confidence": "0.3",
            "labeling_method": "ocr_no_text",
        }

    for pattern, common, scientific, confidence in NON_TOMATO_KEYWORDS:
        if pattern.search(text):
            return {
                "classification_label": "non_tomato",
                "species_common_name": common,
                "species_scientific_name": scientific,
                "confidence": str(confidence),
                "labeling_method": "ocr_keyword",
            }

    for pattern in TOMATO_KEYWORDS:
        if pattern.search(text):
            return {
                "classification_label": "tomato",
                "species_common_name": "Tomato",
                "species_scientific_name": "Solanum lycopersicum",
                "confidence": "0.9",
                "labeling_method": "ocr_keyword",
            }

    return {
        "classification_label": "unknown",
        "species_common_name": "unknown",
        "species_scientific_name": "unknown",
        "confidence": "0.4",
        "labeling_method": "ocr_unresolved",
    }


def label_rows(
    mixed_csv: Path,
    image_dir: Path,
    packet_crop_dir: Path,
    output_csv: Path,
    non_tomato_only_csv: Path,
    overrides_csv: Path | None,
) -> Dict[str, int]:
    with mixed_csv.open("r", encoding="utf-8", newline="") as handle:
        input_rows = list(csv.DictReader(handle))
    overrides = load_manual_overrides(overrides_csv)

    labeled_rows: List[Dict[str, str]] = []
    non_tomato_rows: List[Dict[str, str]] = []

    tomato_count = 0
    non_tomato_count = 0
    unknown_count = 0

    for idx, row in enumerate(input_rows, start=1):
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        image_path = image_dir / f"{idx:02d}_{source_asset_id}.jpg"
        crop_path = packet_crop_dir / f"{idx:02d}_{source_asset_id}.jpg"
        ocr_text = ""
        classification = {
            "classification_label": "unknown",
            "species_common_name": "unknown",
            "species_scientific_name": "unknown",
            "confidence": "0.4",
            "labeling_method": "ocr_unresolved",
        }

        if crop_path.exists():
            ocr_text = extract_ocr_text([crop_path], psm_modes=("6", "11"))
            classification = classify_from_text(ocr_text)

        if (
            classification["classification_label"] == "unknown"
            and image_path.exists()
        ):
            full_image_text = extract_ocr_text([image_path], psm_modes=("6",))
            ocr_text = " | ".join(value for value in (ocr_text, full_image_text) if value)
            classification = classify_from_text(ocr_text)

        output_row = {
            "photo_url": (row.get("photo_url", "") or "").strip(),
            "caption": (row.get("caption", "") or "").strip(),
            "capture_date": (row.get("capture_date", "") or "").strip(),
            "captured_at": (row.get("captured_at", "") or "").strip(),
            "uploaded_at": (row.get("uploaded_at", "") or "").strip(),
            "timezone": (row.get("timezone", "") or "").strip(),
            "latitude": (row.get("latitude", "") or "").strip(),
            "longitude": (row.get("longitude", "") or "").strip(),
            "device_model": (row.get("device_model", "") or "").strip(),
            "notes": (row.get("notes", "") or "").strip(),
            "source_asset_id": source_asset_id,
            "source_platform": (row.get("source_platform", "") or "").strip(),
            "species_common_name": classification["species_common_name"],
            "variety_name": derive_variety_name((row.get("caption", "") or "").strip()),
            "species_scientific_name": classification["species_scientific_name"],
            "specific_note": (row.get("specific_note", "") or "").strip(),
            "weather_hypothesis": (row.get("weather_hypothesis", "") or "").strip(),
            "expected_harvest_window": (
                (row.get("expected_harvest_window", "") or "").strip()
            ),
            "classification_label": classification["classification_label"],
            "confidence": classification["confidence"],
            "labeling_method": classification["labeling_method"],
            "ocr_excerpt": ocr_text[:500],
        }
        output_row = apply_manual_override(idx, source_asset_id, output_row, overrides)

        label = output_row["classification_label"]
        if label == "tomato":
            tomato_count += 1
        elif label == "non_tomato":
            non_tomato_count += 1
            if not output_row["caption"]:
                output_row["caption"] = (
                    f"{classification['species_common_name']} | "
                    f"non_tomato_{idx:02d} | unknown"
                )
            ocr_note = f"OCR: {ocr_text[:200]}" if ocr_text else "OCR: no text"
            output_row["notes"] = (
                f"{output_row['notes']}; {ocr_note}".strip("; ").strip()
            )
            non_tomato_rows.append(output_row.copy())
        else:
            unknown_count += 1

        labeled_rows.append(output_row)
        print(
            f"row={idx} asset={source_asset_id} label={label} "
            f"species={output_row['species_common_name']}"
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(labeled_rows)

    non_tomato_only_csv.parent.mkdir(parents=True, exist_ok=True)
    with non_tomato_only_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(non_tomato_rows)

    return {
        "processed_rows": len(input_rows),
        "tomato_rows": tomato_count,
        "non_tomato_rows": non_tomato_count,
        "unknown_rows": unknown_count,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OCR packet labels and classify non-tomato species from album images."
    )
    parser.add_argument(
        "--mixed-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos.csv"),
        help="Input mixed intake CSV",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory containing downloaded photos named '<index>_<source_asset_id>.jpg'",
    )
    parser.add_argument(
        "--packet-crop-dir",
        type=Path,
        default=Path("local/non_tomato_species/packet_crops"),
        help="Directory containing packet crop images named '<index>_<source_asset_id>.jpg'",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled.csv"),
        help="Output CSV with OCR labels for all rows",
    )
    parser.add_argument(
        "--non-tomato-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_non_tomato_labeled.csv"),
        help="Output CSV containing only non-tomato rows",
    )
    parser.add_argument(
        "--overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_label_overrides_v1.csv"),
        help="Optional manual override CSV keyed by row_index",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stats = label_rows(
        args.mixed_csv,
        args.image_dir,
        args.packet_crop_dir,
        args.output_csv,
        args.non_tomato_csv,
        args.overrides_csv,
    )
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"output_csv={args.output_csv}")
    print(f"non_tomato_csv={args.non_tomato_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
