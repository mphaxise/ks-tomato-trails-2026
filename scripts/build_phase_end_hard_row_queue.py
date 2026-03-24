#!/usr/bin/env python3
"""Build a focused hard-row queue for skipped phase-end run rows."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import cv2


NUM_RE = re.compile(r"\b([0-9]{1,3})\b")


def parse_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return 0


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} missing CSV header")
        return list(reader)


def crop_center(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    height, width = image.shape[:2]
    x0 = int(width * 0.20)
    x1 = int(width * 0.80)
    y0 = int(height * 0.20)
    y1 = int(height * 0.96)
    if x1 <= x0 or y1 <= y0:
        return image
    return image[y0:y1, x0:x1]


def crop_label_band(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    height, width = image.shape[:2]
    x0 = int(width * 0.20)
    x1 = int(width * 0.80)
    y0 = int(height * 0.25)
    y1 = int(height * 0.85)
    if x1 <= x0 or y1 <= y0:
        return image
    return image[y0:y1, x0:x1]


def to_clahe_binary(image: cv2.typing.MatLike, upscale: float = 2.0) -> cv2.typing.MatLike:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)
    scaled = cv2.resize(
        clahe,
        dsize=None,
        fx=upscale,
        fy=upscale,
        interpolation=cv2.INTER_CUBIC,
    )
    _, otsu = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return otsu


def to_adaptive_binary(image: cv2.typing.MatLike, upscale: float = 3.0) -> cv2.typing.MatLike:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(
        gray,
        dsize=None,
        fx=upscale,
        fy=upscale,
        interpolation=cv2.INTER_CUBIC,
    )
    return cv2.adaptiveThreshold(
        scaled,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )


def build_variants(image: cv2.typing.MatLike) -> List[Tuple[str, cv2.typing.MatLike, int]]:
    center = crop_center(image)
    label_band = crop_label_band(image)
    return [
        ("full_raw_psm6", image, 6),
        ("full_raw_psm11", image, 11),
        ("center_clahe_psm6", to_clahe_binary(center, 2.0), 6),
        ("center_clahe_psm11", to_clahe_binary(center, 2.0), 11),
        ("label_otsu_psm7", to_clahe_binary(label_band, 3.0), 7),
        ("label_adaptive_psm11", to_adaptive_binary(label_band, 3.0), 11),
        ("label_adaptive_psm6", to_adaptive_binary(label_band, 3.0), 6),
    ]


def compute_visual_feature(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    roi = crop_center(image)
    resized = cv2.resize(roi, (192, 192), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [16, 16, 16],
        [0, 180, 0, 256, 0, 256],
    ).flatten()
    hist = hist.astype("float32")
    norm = float(cv2.norm(hist))
    if norm > 0:
        hist /= norm
    return hist


def parse_numeric_tokens(text: str, max_pot_number: int) -> List[int]:
    out: List[int] = []
    seen = set()
    for raw in NUM_RE.findall(text or ""):
        value = int(raw)
        if value <= 0 or value > max_pot_number or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def ocr_with_tesseract(image: cv2.typing.MatLike, psm: int) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        if not cv2.imwrite(str(temp_path), image):
            return ""
        result = subprocess.run(
            ["tesseract", str(temp_path), "stdout", "--psm", str(psm)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=7,
            check=False,
        )
        return re.sub(r"\s+", " ", result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return ""
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def normalize_run_dates(raw: str) -> List[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def row_image_path(images_dir: Path, row_index: int, source_asset_id: str) -> Path:
    return images_dir / f"{row_index:02d}_{source_asset_id}.jpg"


def averaged_template_features(
    mapping_rows: Sequence[Dict[str, str]],
    images_dir: Path,
    template_run_dates: Sequence[str],
) -> Dict[str, cv2.typing.MatLike]:
    by_pot: Dict[str, List[cv2.typing.MatLike]] = {}
    for row in mapping_rows:
        run_date = (row.get("run_date", "") or "").strip()
        if run_date not in template_run_dates:
            continue
        pot_id = (row.get("pot_id", "") or "").strip()
        row_index = parse_int(row.get("row_index", ""))
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not pot_id or row_index <= 0 or not source_asset_id:
            continue
        image_path = row_image_path(images_dir, row_index, source_asset_id)
        if not image_path.exists():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        by_pot.setdefault(pot_id, []).append(compute_visual_feature(image))

    averaged: Dict[str, cv2.typing.MatLike] = {}
    for pot_id, vectors in by_pot.items():
        if not vectors:
            continue
        acc = vectors[0].copy()
        for vector in vectors[1:]:
            acc += vector
        acc /= float(len(vectors))
        norm = float(cv2.norm(acc))
        if norm > 0:
            acc /= norm
        averaged[pot_id] = acc
    return averaged


def choose_suggestion(
    votes: Dict[int, int],
    visual_top1_pot: str,
) -> Tuple[int, int, str]:
    if votes:
        sorted_votes = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
        top_num, top_vote_count = sorted_votes[0]
        ties = sum(1 for _, count in sorted_votes if count == top_vote_count)
        if top_vote_count >= 5 and ties == 1:
            return top_num, top_vote_count, "ocr_high"
        if (
            top_vote_count >= 4
            and ties == 1
            and visual_top1_pot == f"{top_num}T"
        ):
            return top_num, top_vote_count, "ocr_visual_medium"
        return top_num, 0, "needs_manual"

    if visual_top1_pot.endswith("T"):
        return parse_int(visual_top1_pot[:-1]), 0, "needs_manual"
    return 0, 0, "needs_manual"


def build_queue(
    labeled_rows: Sequence[Dict[str, str]],
    mapping_rows: Sequence[Dict[str, str]],
    run_date: str,
    template_run_dates: Sequence[str],
    images_dir: Path,
    queue_dir: Path,
    max_pot_number: int,
) -> List[Dict[str, str]]:
    run_rows: List[Tuple[int, Dict[str, str]]] = [
        (index, row)
        for index, row in enumerate(labeled_rows, start=1)
        if (row.get("capture_date", "") or "").strip() == run_date
    ]
    run_indices = {index for index, _ in run_rows}
    mapped_indices = {
        parse_int(row.get("row_index", ""))
        for row in mapping_rows
        if (row.get("run_date", "") or "").strip() == run_date
    }
    extra_indices = sorted(index for index in run_indices if index not in mapped_indices)

    templates = averaged_template_features(
        mapping_rows=mapping_rows,
        images_dir=images_dir,
        template_run_dates=template_run_dates,
    )
    if not templates:
        raise ValueError("No template features available for requested template run dates.")

    queue_dir.mkdir(parents=True, exist_ok=True)
    row_lookup = {index: row for index, row in run_rows}
    out_rows: List[Dict[str, str]] = []

    for row_index in extra_indices:
        row = row_lookup[row_index]
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue
        image_path = row_image_path(images_dir, row_index, source_asset_id)
        if not image_path.exists():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        feature = compute_visual_feature(image)
        scores = sorted(
            (
                (float(feature.dot(template_feature)), pot_id)
                for pot_id, template_feature in templates.items()
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if not scores:
            continue

        visual_top1_score, visual_top1_pot = scores[0]
        visual_top2_score = scores[1][0] if len(scores) > 1 else 0.0
        visual_top3_pots = [pot_id for _, pot_id in scores[:3]]

        votes: Dict[int, int] = {}
        ensemble_numbers = set()
        for _, variant_image, psm in build_variants(image):
            text = ocr_with_tesseract(variant_image, psm=psm)
            for number in parse_numeric_tokens(text, max_pot_number):
                ensemble_numbers.add(number)
                votes[number] = votes.get(number, 0) + 1

        suggested_number, matched_variant_count, method = choose_suggestion(
            votes=votes,
            visual_top1_pot=visual_top1_pot,
        )
        if suggested_number <= 0 or suggested_number > max_pot_number:
            continue
        suggested_pot_id = f"{suggested_number}T"

        queue_id = f"{run_date}_{row_index}_{source_asset_id[:8]}"
        full_crop_path = queue_dir / f"{queue_id}_full.jpg"
        center_crop_path = queue_dir / f"{queue_id}_center.jpg"
        label_crop_path = queue_dir / f"{queue_id}_label.jpg"
        cv2.imwrite(str(full_crop_path), image)
        cv2.imwrite(str(center_crop_path), crop_center(image))
        cv2.imwrite(str(label_crop_path), crop_label_band(image))

        out_rows.append(
            {
                "run_date": run_date,
                "row_index": str(row_index),
                "pot_id": suggested_pot_id,
                "pot_number": str(suggested_number),
                "source_asset_id": source_asset_id,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "image_path": str(image_path),
                "matched_variant_count": str(matched_variant_count),
                "ensemble_numbers_detected": ",".join(
                    str(value) for value in sorted(ensemble_numbers)
                ),
                "task": "human_label_pot_number_and_variety",
                "full_crop_path": str(full_crop_path),
                "center_crop_path": str(center_crop_path),
                "label_crop_path": str(label_crop_path),
                "suggestion_method": method,
                "visual_top1_pot_id": visual_top1_pot,
                "visual_top1_score": f"{visual_top1_score:.5f}",
                "visual_top2_score": f"{visual_top2_score:.5f}",
                "visual_margin": f"{(visual_top1_score - visual_top2_score):.5f}",
                "visual_top3_pot_ids": ",".join(visual_top3_pots),
                "ocr_votes_json": json.dumps(votes, sort_keys=True),
            }
        )

    out_rows.sort(key=lambda row: parse_int(row.get("row_index", "0")))
    return out_rows


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    fieldnames = [
        "run_date",
        "row_index",
        "pot_id",
        "pot_number",
        "source_asset_id",
        "photo_url",
        "image_path",
        "matched_variant_count",
        "ensemble_numbers_detected",
        "task",
        "full_crop_path",
        "center_crop_path",
        "label_crop_path",
        "suggestion_method",
        "visual_top1_pot_id",
        "visual_top1_score",
        "visual_top2_score",
        "visual_margin",
        "visual_top3_pot_ids",
        "ocr_votes_json",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build manual hard-row queue for skipped run rows."
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled intake CSV.",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Current mapping CSV with canonical mapped rows.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory with downloaded intake images.",
    )
    parser.add_argument(
        "--run-date",
        default="2026-03-22",
        help="Run date to build queue for (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--template-run-dates",
        default="2026-03-11,2026-03-22",
        help="Comma-separated run dates used to build visual templates.",
    )
    parser.add_argument(
        "--max-pot-number",
        type=int,
        default=32,
        help="Maximum valid pot number to retain from OCR.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/v1_6/phase_end_2026-03-22"),
        help="Output directory for queue CSV and crops.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    template_run_dates = normalize_run_dates(args.template_run_dates)
    if not template_run_dates:
        raise ValueError("No template run dates provided.")

    labeled_rows = read_csv_rows(args.labeled_csv)
    mapping_rows = read_csv_rows(args.mapping_csv)
    queue_dir = args.output_dir / "manual_label_queue"
    queue_rows = build_queue(
        labeled_rows=labeled_rows,
        mapping_rows=mapping_rows,
        run_date=args.run_date.strip(),
        template_run_dates=template_run_dates,
        images_dir=args.images_dir,
        queue_dir=queue_dir,
        max_pot_number=args.max_pot_number,
    )
    queue_csv = args.output_dir / "manual_label_queue.csv"
    write_csv(queue_csv, queue_rows)

    method_counts = Counter((row.get("suggestion_method", "") or "").strip() for row in queue_rows)
    weak_rows = sum(1 for row in queue_rows if (row.get("matched_variant_count", "") or "0") == "0")

    print(f"run_date={args.run_date.strip()}")
    print(f"template_run_dates={','.join(template_run_dates)}")
    print(f"queue_rows={len(queue_rows)}")
    print(f"weak_rows={weak_rows}")
    print(f"method_counts={dict(method_counts)}")
    print(f"queue_csv={queue_csv}")
    print(f"queue_dir={queue_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
