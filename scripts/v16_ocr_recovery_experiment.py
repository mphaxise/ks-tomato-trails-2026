#!/usr/bin/env python3
"""Evaluate OCR recovery variants for difficult intake runs and build manual queue."""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import cv2

from build_tomato_pot_mapping import (
    build_mapping,
    load_baseline_variety_map,
    load_pot_series_overrides,
    load_series_variety_map,
    read_rows,
)

MAX_POT_NUMBER = 40


@dataclass(frozen=True)
class FocusRow:
    run_date: str
    row_index: int
    pot_id: str
    pot_number: int
    source_asset_id: str
    photo_url: str
    image_path: Path


@dataclass(frozen=True)
class VisualPrediction:
    run_date: str
    row_index: int
    source_asset_id: str
    true_pot_id: str
    predicted_pot_id: str
    top1_score: float
    top3_pot_ids: str
    top3_scores: str
    top1_match: int
    top3_match: int


def pot_number_from_pot_id(pot_id: str) -> int:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return 0
    return int(matched.group(1))


def parse_numeric_tokens(text: str) -> List[int]:
    numbers: List[int] = []
    seen = set()
    for raw in re.findall(r"\b([0-9]{1,3})\b", text or ""):
        value = int(raw)
        if value <= 0 or value > MAX_POT_NUMBER or value in seen:
            continue
        numbers.append(value)
        seen.add(value)
    return numbers


def ocr_image_with_tesseract(image: cv2.typing.MatLike, psm: int) -> str:
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
    x0 = int(width * 0.28)
    x1 = int(width * 0.72)
    y0 = int(height * 0.45)
    y1 = int(height * 0.98)
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


def build_variants(image: cv2.typing.MatLike) -> Dict[str, Tuple[cv2.typing.MatLike, int]]:
    center = crop_center(image)
    label_band = crop_label_band(image)
    return {
        "full_raw_psm6": (image, 6),
        "full_raw_psm11": (image, 11),
        "center_clahe_psm6": (to_clahe_binary(center, upscale=2.0), 6),
        "center_clahe_psm11": (to_clahe_binary(center, upscale=2.0), 11),
        "label_otsu_psm7": (to_clahe_binary(label_band, upscale=3.0), 7),
        "label_adaptive_psm6": (to_adaptive_binary(label_band, upscale=3.0), 6),
    }


def choose_expected_for_run(
    rows: Sequence[Dict[str, str]], run_date: str, expected_pots: int
) -> int:
    count = sum(
        1
        for row in rows
        if (row.get("capture_date", "") or "").strip() == run_date
    )
    if count >= expected_pots:
        return expected_pots
    return count


def build_focus_rows(
    labeled_rows: List[Dict[str, str]],
    run_dates: Sequence[str],
    expected_pots: int,
    images_dir: Path,
    series_variety_map: Dict[int, str],
    pot_series_overrides: Dict[str, int],
    baseline_variety_map: Dict[str, str],
) -> List[FocusRow]:
    output: List[FocusRow] = []
    for run_date in run_dates:
        expected = choose_expected_for_run(labeled_rows, run_date, expected_pots)
        mapping_rows, _ = build_mapping(
            rows=labeled_rows,
            run_date=run_date,
            expected_pots=expected,
            potting_date="2026-02-24",
            day_one_photo_date="2026-02-25",
            lifecycle_stage="sapling",
            assume_sequential_pot_ids=True,
            tomato_only_run=True,
            series_variety_map=series_variety_map,
            pot_series_overrides=pot_series_overrides,
            baseline_variety_map=baseline_variety_map,
            baseline_reconcile=True,
            context_id="context_default",
        )
        for row in mapping_rows:
            pot_id = (row.get("pot_id", "") or "").strip()
            pot_number = pot_number_from_pot_id(pot_id)
            row_index = int((row.get("row_index", "") or "0").strip() or 0)
            source_asset_id = (row.get("source_asset_id", "") or "").strip()
            if not pot_id or pot_number <= 0 or row_index <= 0 or not source_asset_id:
                continue
            image_path = images_dir / f"{row_index:02d}_{source_asset_id}.jpg"
            if not image_path.exists():
                continue
            output.append(
                FocusRow(
                    run_date=run_date,
                    row_index=row_index,
                    pot_id=pot_id,
                    pot_number=pot_number,
                    source_asset_id=source_asset_id,
                    photo_url=(row.get("photo_url", "") or "").strip(),
                    image_path=image_path,
                )
            )
    return output


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def save_manual_queue_crops(
    row: FocusRow,
    image: cv2.typing.MatLike,
    queue_dir: Path,
) -> Dict[str, str]:
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_id = f"{row.run_date}_{row.pot_id}_{row.row_index}_{row.source_asset_id[:8]}"
    full_out = queue_dir / f"{queue_id}_full.jpg"
    center_out = queue_dir / f"{queue_id}_center.jpg"
    label_out = queue_dir / f"{queue_id}_label.jpg"
    cv2.imwrite(str(full_out), image)
    cv2.imwrite(str(center_out), crop_center(image))
    cv2.imwrite(str(label_out), crop_label_band(image))
    return {
        "full_crop_path": str(full_out),
        "center_crop_path": str(center_out),
        "label_crop_path": str(label_out),
    }


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


def evaluate_visual_similarity(
    baseline_rows: Sequence[FocusRow],
    target_rows: Sequence[FocusRow],
) -> Tuple[List[VisualPrediction], Dict[str, object]]:
    baseline_features: Dict[str, cv2.typing.MatLike] = {}
    for row in baseline_rows:
        image = cv2.imread(str(row.image_path))
        if image is None:
            continue
        baseline_features[row.pot_id] = compute_visual_feature(image)

    predictions: List[VisualPrediction] = []
    top1_total = 0
    top1_matches = 0
    top3_matches = 0

    for row in target_rows:
        image = cv2.imread(str(row.image_path))
        if image is None:
            continue
        feature = compute_visual_feature(image)
        scores: List[Tuple[float, str]] = []
        for pot_id, baseline_feature in baseline_features.items():
            score = float(feature.dot(baseline_feature))
            scores.append((score, pot_id))
        if not scores:
            continue
        scores.sort(key=lambda item: item[0], reverse=True)
        top = scores[0]
        top3 = scores[:3]
        predicted = top[1]
        top3_ids = [pot for _, pot in top3]
        top3_scores = [f"{score:.5f}" for score, _ in top3]
        top1_match = 1 if predicted == row.pot_id else 0
        top3_match = 1 if row.pot_id in top3_ids else 0
        top1_total += 1
        top1_matches += top1_match
        top3_matches += top3_match
        predictions.append(
            VisualPrediction(
                run_date=row.run_date,
                row_index=row.row_index,
                source_asset_id=row.source_asset_id,
                true_pot_id=row.pot_id,
                predicted_pot_id=predicted,
                top1_score=top[0],
                top3_pot_ids=",".join(top3_ids),
                top3_scores=",".join(top3_scores),
                top1_match=top1_match,
                top3_match=top3_match,
            )
        )

    summary = {
        "rows_total": top1_total,
        "top1_match_rows": top1_matches,
        "top3_match_rows": top3_matches,
        "top1_match_rate": round(
            (float(top1_matches) / float(top1_total)) if top1_total else 0.0,
            4,
        ),
        "top3_match_rate": round(
            (float(top3_matches) / float(top1_total)) if top1_total else 0.0,
            4,
        ),
    }
    return predictions, summary


def run_experiment(
    labeled_csv: Path,
    images_dir: Path,
    output_dir: Path,
    run_dates: Sequence[str],
    expected_pots: int,
    series_map_csv: Path,
    pot_series_overrides_csv: Path,
    baseline_map_csv: Path,
    visual_baseline_run_date: str,
) -> Dict[str, object]:
    labeled_rows = read_rows(labeled_csv)
    series_variety_map = load_series_variety_map(series_map_csv)
    pot_series_overrides = load_pot_series_overrides(pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(baseline_map_csv)

    focus_rows = build_focus_rows(
        labeled_rows=labeled_rows,
        run_dates=run_dates,
        expected_pots=expected_pots,
        images_dir=images_dir,
        series_variety_map=series_variety_map,
        pot_series_overrides=pot_series_overrides,
        baseline_variety_map=baseline_variety_map,
    )
    if not focus_rows:
        raise ValueError("No focus rows found for selected run dates.")

    baseline_rows = build_focus_rows(
        labeled_rows=labeled_rows,
        run_dates=[visual_baseline_run_date],
        expected_pots=expected_pots,
        images_dir=images_dir,
        series_variety_map=series_variety_map,
        pot_series_overrides=pot_series_overrides,
        baseline_variety_map=baseline_variety_map,
    )

    variant_stats: Dict[str, Dict[str, float]] = {}
    detail_rows: List[Dict[str, object]] = []
    union_numbers_by_row: Dict[Tuple[str, int, str], set] = {}
    variant_matches_by_row: Dict[Tuple[str, int, str], int] = {}
    row_lookup: Dict[Tuple[str, int, str], FocusRow] = {}

    for focus in focus_rows:
        image = cv2.imread(str(focus.image_path))
        if image is None:
            continue
        row_key = (focus.run_date, focus.row_index, focus.source_asset_id)
        union_numbers_by_row.setdefault(row_key, set())
        variant_matches_by_row.setdefault(row_key, 0)
        row_lookup[row_key] = focus

        for variant_name, (variant_image, psm) in build_variants(image).items():
            text = ocr_image_with_tesseract(variant_image, psm=psm)
            numbers = parse_numeric_tokens(text)
            matched = focus.pot_number in numbers
            has_text = bool(text)
            has_digits = bool(numbers)

            stats = variant_stats.setdefault(
                variant_name,
                {
                    "rows_total": 0.0,
                    "rows_with_text": 0.0,
                    "rows_with_digits": 0.0,
                    "pot_match_rows": 0.0,
                    "text_length_sum": 0.0,
                },
            )
            stats["rows_total"] += 1.0
            stats["rows_with_text"] += 1.0 if has_text else 0.0
            stats["rows_with_digits"] += 1.0 if has_digits else 0.0
            stats["pot_match_rows"] += 1.0 if matched else 0.0
            stats["text_length_sum"] += float(len(text))

            union_numbers_by_row[row_key].update(numbers)
            if matched:
                variant_matches_by_row[row_key] += 1

            detail_rows.append(
                {
                    "run_date": focus.run_date,
                    "row_index": focus.row_index,
                    "pot_id": focus.pot_id,
                    "pot_number": focus.pot_number,
                    "source_asset_id": focus.source_asset_id,
                    "variant": variant_name,
                    "psm": psm,
                    "match": 1 if matched else 0,
                    "has_text": 1 if has_text else 0,
                    "has_digits": 1 if has_digits else 0,
                    "text_length": len(text),
                    "numbers_detected": ",".join(str(value) for value in numbers),
                    "ocr_text": text,
                    "image_path": str(focus.image_path),
                    "photo_url": focus.photo_url,
                }
            )

    summary_rows: List[Dict[str, object]] = []
    for variant_name, stats in sorted(
        variant_stats.items(), key=lambda item: item[0]
    ):
        rows_total = int(stats["rows_total"])
        rows_with_text = int(stats["rows_with_text"])
        rows_with_digits = int(stats["rows_with_digits"])
        pot_match_rows = int(stats["pot_match_rows"])
        text_length_mean = (
            float(stats["text_length_sum"]) / float(rows_total) if rows_total else 0.0
        )
        summary_rows.append(
            {
                "variant": variant_name,
                "rows_total": rows_total,
                "rows_with_text": rows_with_text,
                "rows_with_digits": rows_with_digits,
                "pot_match_rows": pot_match_rows,
                "pot_match_rate": round(
                    (float(pot_match_rows) / float(rows_total)) if rows_total else 0.0, 4
                ),
                "digits_rate": round(
                    (float(rows_with_digits) / float(rows_total)) if rows_total else 0.0,
                    4,
                ),
                "text_rate": round(
                    (float(rows_with_text) / float(rows_total)) if rows_total else 0.0, 4
                ),
                "text_length_mean": round(text_length_mean, 2),
            }
        )

    summary_rows.sort(key=lambda row: (-float(row["pot_match_rate"]), row["variant"]))

    manual_queue_dir = output_dir / "manual_label_queue"
    manual_queue_rows: List[Dict[str, object]] = []
    ensemble_match_rows = 0
    for row_key, numbers in union_numbers_by_row.items():
        focus = row_lookup[row_key]
        ensemble_match = focus.pot_number in numbers
        if ensemble_match:
            ensemble_match_rows += 1
            continue
        image = cv2.imread(str(focus.image_path))
        if image is None:
            continue
        crop_paths = save_manual_queue_crops(focus, image, manual_queue_dir)
        manual_queue_rows.append(
            {
                "run_date": focus.run_date,
                "row_index": focus.row_index,
                "pot_id": focus.pot_id,
                "pot_number": focus.pot_number,
                "source_asset_id": focus.source_asset_id,
                "photo_url": focus.photo_url,
                "image_path": str(focus.image_path),
                "matched_variant_count": int(variant_matches_by_row[row_key]),
                "ensemble_numbers_detected": ",".join(str(v) for v in sorted(numbers)),
                "task": "human_label_pot_number_and_variety",
                **crop_paths,
            }
        )

    rows_total = len(union_numbers_by_row)
    ensemble_match_rate = (
        float(ensemble_match_rows) / float(rows_total) if rows_total else 0.0
    )

    write_csv(
        output_dir / "ocr_variant_eval_details.csv",
        fieldnames=[
            "run_date",
            "row_index",
            "pot_id",
            "pot_number",
            "source_asset_id",
            "variant",
            "psm",
            "match",
            "has_text",
            "has_digits",
            "text_length",
            "numbers_detected",
            "ocr_text",
            "image_path",
            "photo_url",
        ],
        rows=detail_rows,
    )
    write_csv(
        output_dir / "ocr_variant_ranked_summary.csv",
        fieldnames=[
            "variant",
            "rows_total",
            "rows_with_text",
            "rows_with_digits",
            "pot_match_rows",
            "pot_match_rate",
            "digits_rate",
            "text_rate",
            "text_length_mean",
        ],
        rows=summary_rows,
    )
    write_csv(
        output_dir / "manual_label_queue.csv",
        fieldnames=[
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
        ],
        rows=manual_queue_rows,
    )

    visual_predictions, visual_summary = evaluate_visual_similarity(
        baseline_rows=baseline_rows, target_rows=focus_rows
    )
    write_csv(
        output_dir / "visual_similarity_predictions.csv",
        fieldnames=[
            "run_date",
            "row_index",
            "source_asset_id",
            "true_pot_id",
            "predicted_pot_id",
            "top1_score",
            "top3_pot_ids",
            "top3_scores",
            "top1_match",
            "top3_match",
        ],
        rows=[prediction.__dict__ for prediction in visual_predictions],
    )
    write_csv(
        output_dir / "visual_similarity_summary.csv",
        fieldnames=[
            "rows_total",
            "top1_match_rows",
            "top3_match_rows",
            "top1_match_rate",
            "top3_match_rate",
            "baseline_run_date",
        ],
        rows=[{**visual_summary, "baseline_run_date": visual_baseline_run_date}],
    )

    return {
        "focus_rows": rows_total,
        "summary_rows": len(summary_rows),
        "manual_queue_rows": len(manual_queue_rows),
        "ensemble_match_rows": ensemble_match_rows,
        "ensemble_match_rate": round(ensemble_match_rate, 4),
        "best_variant": summary_rows[0]["variant"] if summary_rows else "",
        "best_variant_match_rate": summary_rows[0]["pot_match_rate"] if summary_rows else 0.0,
        "visual_top1_match_rate": visual_summary["top1_match_rate"],
        "visual_top3_match_rate": visual_summary["top3_match_rate"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run OCR recovery experiment on difficult intake runs."
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled intake CSV.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory with downloaded intake images.",
    )
    parser.add_argument(
        "--run-dates",
        default="2026-02-28,2026-03-01",
        help="Comma-separated run dates to analyze.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count for full watering-day runs.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-to-variety map CSV.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot override CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline mapping CSV for continuity.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery"),
        help="Output folder for OCR experiment artifacts.",
    )
    parser.add_argument(
        "--visual-baseline-run-date",
        default="2026-02-27",
        help="Run date to use as baseline templates for visual similarity matching.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_dates = [part.strip() for part in args.run_dates.split(",") if part.strip()]
    if not run_dates:
        raise ValueError("No valid run dates provided.")

    result = run_experiment(
        labeled_csv=args.labeled_csv,
        images_dir=args.images_dir,
        output_dir=args.output_dir,
        run_dates=run_dates,
        expected_pots=args.expected_pots,
        series_map_csv=args.series_map_csv,
        pot_series_overrides_csv=args.pot_series_overrides_csv,
        baseline_map_csv=args.baseline_map_csv,
        visual_baseline_run_date=args.visual_baseline_run_date.strip(),
    )

    print(f"run_dates={','.join(run_dates)}")
    for key in (
        "focus_rows",
        "summary_rows",
        "manual_queue_rows",
        "ensemble_match_rows",
        "ensemble_match_rate",
        "best_variant",
        "best_variant_match_rate",
        "visual_top1_match_rate",
        "visual_top3_match_rate",
    ):
        print(f"{key}={result[key]}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
