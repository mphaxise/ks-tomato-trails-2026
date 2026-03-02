#!/usr/bin/env python3
"""Profile batch drift and propose a robust v1.6 random-intake pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
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

PROFILE_FIELDS = [
    "capture_date",
    "uploaded_dates",
    "total_rows",
    "tomato_rows",
    "non_tomato_rows",
    "unknown_rows",
    "caption_rate",
    "ocr_nonempty_rate",
    "non_unknown_label_rate",
    "packet_crop_rate",
    "low_resolution_rate",
    "full_resolution_rate",
    "portrait_rate",
    "landscape_rate",
    "blur_median",
    "brightness_median",
    "sequential_inferred_rate",
    "ocr_confirmed_rate",
    "auto_resolved_rate",
    "continuity_resolution_rate",
    "mode",
]

CONTINUITY_SOURCES = {
    "manual_override",
    "baseline_continuity",
    "historical_continuity",
    "series_map",
    "sequence_inference",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def round4(value: float) -> float:
    return round(float(value), 4)


def median_or_zero(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def read_manifest_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def build_manifest_by_asset(rows: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    by_asset: Dict[str, Dict[str, str]] = {}
    for row in rows:
        asset = (row.get("source_asset_id", "") or "").strip()
        if not asset:
            continue
        by_asset[asset] = row
    return by_asset


def build_image_lookup(images_dir: Path) -> Dict[str, Path]:
    lookup: Dict[str, Path] = {}
    for path in sorted(images_dir.glob("*.jpg")):
        stem = path.stem
        if "_" not in stem:
            continue
        _, source_asset_id = stem.split("_", 1)
        lookup[source_asset_id] = path
    return lookup


def image_metrics(image_path: Path) -> Tuple[int, int, float, float]:
    image = cv2.imread(str(image_path))
    if image is None:
        return (0, 0, 0.0, 0.0)
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    brightness = float(hsv[:, :, 2].mean())
    return (width, height, blur_score, brightness)


def classify_run_mode(profile: Dict[str, object]) -> str:
    total_rows = int(profile.get("total_rows", 0) or 0)
    caption_rate = float(profile.get("caption_rate", 0.0) or 0.0)
    non_unknown_label_rate = float(profile.get("non_unknown_label_rate", 0.0) or 0.0)
    full_resolution_rate = float(profile.get("full_resolution_rate", 0.0) or 0.0)
    sequential_inferred_rate = float(profile.get("sequential_inferred_rate", 0.0) or 0.0)

    if (
        caption_rate >= 0.70
        and non_unknown_label_rate >= 0.60
        and full_resolution_rate >= 0.50
    ):
        return "baseline_labeled_single_pot"

    if (
        30 <= total_rows <= 34
        and sequential_inferred_rate >= 0.90
        and non_unknown_label_rate <= 0.20
    ):
        return "watering_day_unlabeled_sequence"

    return "random_mixed_context"


def build_profile(
    run_date: str,
    labeled_rows: Sequence[Dict[str, str]],
    manifest_by_asset: Dict[str, Dict[str, str]],
    image_by_asset: Dict[str, Path],
    packet_crop_dir: Path,
    series_variety_map: Dict[int, str],
    pot_series_overrides: Dict[str, int],
    baseline_variety_map: Dict[str, str],
) -> Dict[str, object]:
    selected: List[Tuple[int, Dict[str, str]]] = [
        (index, row)
        for index, row in enumerate(labeled_rows, start=1)
        if (row.get("capture_date", "") or "").strip() == run_date
    ]
    total_rows = len(selected)

    label_counts = {"tomato": 0, "non_tomato": 0, "unknown": 0}
    caption_nonblank = 0
    ocr_nonempty = 0
    packet_crops_found = 0

    portrait_count = 0
    landscape_count = 0
    low_resolution_count = 0
    full_resolution_count = 0
    blur_scores: List[float] = []
    brightness_scores: List[float] = []

    uploaded_dates = set()
    for row_index, row in selected:
        label = (row.get("classification_label", "") or "").strip()
        if label not in label_counts:
            label = "unknown"
        label_counts[label] += 1

        if (row.get("caption", "") or "").strip():
            caption_nonblank += 1
        if (row.get("ocr_excerpt", "") or "").strip():
            ocr_nonempty += 1

        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue

        manifest_row = manifest_by_asset.get(source_asset_id)
        if manifest_row is not None:
            uploaded_at = (manifest_row.get("uploaded_at", "") or "").strip()
            if uploaded_at:
                uploaded_dates.add(uploaded_at[:10])

        packet_crop = packet_crop_dir / f"{row_index:02d}_{source_asset_id}.jpg"
        if packet_crop.exists():
            packet_crops_found += 1

        image_path = image_by_asset.get(source_asset_id)
        if image_path is None or not image_path.exists():
            continue
        width, height, blur, brightness = image_metrics(image_path)
        if width <= 0 or height <= 0:
            continue

        blur_scores.append(blur)
        brightness_scores.append(brightness)
        if height > width:
            portrait_count += 1
        elif width > height:
            landscape_count += 1

        long_side = max(width, height)
        if long_side <= 700:
            low_resolution_count += 1
        if long_side >= 2000:
            full_resolution_count += 1

    expected_pots = 32 if 30 <= total_rows <= 34 else total_rows
    _, mapping_report = build_mapping(
        rows=list(labeled_rows),
        run_date=run_date,
        expected_pots=expected_pots,
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

    mapping_rows = int(mapping_report.get("selected_rows", 0) or 0)
    final_status_counts = mapping_report.get("final_status_counts", {})
    resolution_source_counts = mapping_report.get("resolution_source_counts", {})
    if not isinstance(final_status_counts, dict):
        final_status_counts = {}
    if not isinstance(resolution_source_counts, dict):
        resolution_source_counts = {}

    continuity_count = sum(
        int(resolution_source_counts.get(source, 0) or 0)
        for source in CONTINUITY_SOURCES
    )

    non_unknown_count = label_counts["tomato"] + label_counts["non_tomato"]
    profile: Dict[str, object] = {
        "capture_date": run_date,
        "uploaded_dates": ",".join(sorted(uploaded_dates)),
        "total_rows": total_rows,
        "tomato_rows": label_counts["tomato"],
        "non_tomato_rows": label_counts["non_tomato"],
        "unknown_rows": label_counts["unknown"],
        "caption_rate": round4(safe_ratio(caption_nonblank, total_rows)),
        "ocr_nonempty_rate": round4(safe_ratio(ocr_nonempty, total_rows)),
        "non_unknown_label_rate": round4(safe_ratio(non_unknown_count, total_rows)),
        "packet_crop_rate": round4(safe_ratio(packet_crops_found, total_rows)),
        "low_resolution_rate": round4(safe_ratio(low_resolution_count, total_rows)),
        "full_resolution_rate": round4(safe_ratio(full_resolution_count, total_rows)),
        "portrait_rate": round4(safe_ratio(portrait_count, total_rows)),
        "landscape_rate": round4(safe_ratio(landscape_count, total_rows)),
        "blur_median": round4(median_or_zero(blur_scores)),
        "brightness_median": round4(median_or_zero(brightness_scores)),
        "sequential_inferred_rate": round4(
            safe_ratio(int(mapping_report.get("sequential_inferred_rows", 0) or 0), mapping_rows)
        ),
        "ocr_confirmed_rate": round4(
            safe_ratio(int(mapping_report.get("ocr_confirmed_rows", 0) or 0), mapping_rows)
        ),
        "auto_resolved_rate": round4(
            safe_ratio(int(final_status_counts.get("ready_auto_resolved", 0) or 0), mapping_rows)
        ),
        "continuity_resolution_rate": round4(safe_ratio(continuity_count, mapping_rows)),
        "mode": "",
        "mapping_report": mapping_report,
    }
    profile["mode"] = classify_run_mode(profile)
    return profile


def build_recommended_routine(latest_mode: str) -> List[Dict[str, object]]:
    latest_mode_hint = {
        "baseline_labeled_single_pot": "Current batch resembles captioned baseline photos.",
        "watering_day_unlabeled_sequence": (
            "Current batch resembles unlabeled watering-day one-pot sequence uploads."
        ),
        "random_mixed_context": "Current batch resembles mixed/random context photos.",
    }.get(latest_mode, "Current batch mode is mixed/unknown.")

    return [
        {
            "stage": 1,
            "name": "Batch Partitioning",
            "goal": "Split intake into coherent run-date batches before vision processing.",
            "algorithms": [
                "metadata grouping by capture_date + uploaded_at",
                "duplicate check on source_asset_id",
                "row count expectation check (target 32 for watering-day tomato runs)",
            ],
            "gate": "Proceed only when a batch key and candidate run size are identified.",
        },
        {
            "stage": 2,
            "name": "Frame-Type Routing",
            "goal": "Route each photo to the right path before OCR/mapping.",
            "algorithms": [
                "quality gate (blur + brightness) to flag recapture rows",
                "single-pot vs multi-pot/context classifier",
                f"latest-run hint: {latest_mode_hint}",
            ],
            "gate": "Rows are labeled as baseline_single_pot, watering_day_sequence, or random_context.",
        },
        {
            "stage": 3,
            "name": "Pot Detection",
            "goal": "Find candidate pot regions per image and estimate per-row pot count.",
            "algorithms": [
                "pot bounding-box detector (YOLO/Detectron fine-tuned on local data)",
                "center-priority heuristic for single-pot expected rows",
                "multi-pot branch keeps all candidate boxes with confidence",
            ],
            "gate": "At least one pot candidate per tomato-target row, otherwise queue capture review.",
        },
        {
            "stage": 4,
            "name": "Label/OCR Extraction",
            "goal": "Extract pot tag and packet number only from detected label zones.",
            "algorithms": [
                "label-region crop via text detector",
                "OCR ensemble (psm variants) on label crop, not full frame",
                "regex parse for pot_tag / packet_tag / numeric candidates",
            ],
            "gate": "Return structured tokens with confidence and raw OCR excerpt.",
        },
        {
            "stage": 5,
            "name": "Identity Resolution",
            "goal": "Map pots/plants to canonical database IDs with continuity-first logic.",
            "algorithms": [
                "manual pot-series overrides (highest priority)",
                "baseline continuity reconciliation by pot_id",
                "historical/series-map fallback when OCR is weak",
                "sequence inference only for near-complete watering-day batches",
            ],
            "gate": "Every tomato-target row has pot_id + variety_name or is explicitly marked review-needed.",
        },
        {
            "stage": 6,
            "name": "Confidence And Review Queue",
            "goal": "Auto-accept high-confidence rows and isolate ambiguous rows.",
            "algorithms": [
                "final_status scoring: ready_direct / ready_auto_resolved / review_needed_*",
                "review_stage routing: capture, ocr, mapping",
                "strict run check (expected pot count + duplicates + conflicts)",
            ],
            "gate": "Only ready rows publish to main mapping; review rows stay in queue.",
        },
        {
            "stage": 7,
            "name": "Persist And Learn",
            "goal": "Store provenance and improve model thresholds over time.",
            "algorithms": [
                "persist resolution_source and mapping notes per row",
                "track per-batch drift metrics (label rate, OCR rate, resolution rate)",
                "feed reviewed corrections back into overrides/training set",
            ],
            "gate": "Each completed batch updates drift history and training corpus.",
        },
    ]


def build_summary_payload(profiles: Sequence[Dict[str, object]]) -> Dict[str, object]:
    ordered = sorted(profiles, key=lambda item: str(item["capture_date"]))
    latest = ordered[-1]
    latest_mode = str(latest["mode"])
    baseline_like_count = sum(
        1 for item in ordered if str(item.get("mode", "")) == "baseline_labeled_single_pot"
    )
    watering_like_count = sum(
        1
        for item in ordered
        if str(item.get("mode", "")) == "watering_day_unlabeled_sequence"
    )

    latest_unknown_rate = float(latest["unknown_rows"]) / max(
        int(latest["total_rows"]), 1
    )
    baseline_unknown_rate = 0.0
    baseline_candidates = [
        item
        for item in ordered
        if str(item.get("mode", "")) == "baseline_labeled_single_pot"
    ]
    if baseline_candidates:
        baseline_row = baseline_candidates[-1]
        baseline_unknown_rate = float(baseline_row["unknown_rows"]) / max(
            int(baseline_row["total_rows"]), 1
        )

    key_insights = [
        (
            "Baseline-style single-pot labeled photos are now rare in this dataset."
            f" baseline_like_runs={baseline_like_count} total_runs={len(ordered)}"
        ),
        (
            "Watering-day unlabeled sequence runs dominate recent intake."
            f" watering_like_runs={watering_like_count} total_runs={len(ordered)}"
        ),
        (
            "Latest run depends heavily on continuity mapping rather than OCR labels."
            f" latest_unknown_rate={round4(latest_unknown_rate)}"
            f" baseline_unknown_rate={round4(baseline_unknown_rate)}"
            f" latest_continuity_resolution_rate={latest['continuity_resolution_rate']}"
        ),
    ]

    compact_profiles = []
    for profile in ordered:
        compact_profiles.append(
            {
                key: profile[key]
                for key in PROFILE_FIELDS
            }
        )

    return {
        "generated_at_utc": iso_now(),
        "latest_run_date": latest["capture_date"],
        "latest_run_mode": latest_mode,
        "profiles": compact_profiles,
        "key_insights": key_insights,
        "recommended_routine": build_recommended_routine(latest_mode),
    }


def write_profiles_csv(path: Path, profiles: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROFILE_FIELDS)
        writer.writeheader()
        for profile in sorted(profiles, key=lambda item: str(item["capture_date"])):
            writer.writerow({field: profile.get(field, "") for field in PROFILE_FIELDS})


def write_summary_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build v1.6 random-intake batch drift summary and routine plan."
    )
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=Path("data/intake/google_photos/album_manifest.csv"),
        help="Album manifest CSV with uploaded_at/source_asset_id metadata.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed intake CSV.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Downloaded full image directory.",
    )
    parser.add_argument(
        "--packet-crop-dir",
        type=Path,
        default=Path("local/non_tomato_species/packet_crops"),
        help="Packet crop directory.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-number to variety map CSV.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot-level series override CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline mapping CSV used for continuity reconciliation.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/v1_6/batch_drift_summary.csv"),
        help="Output CSV path for per-batch profile rows.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_6/intake_pipeline_plan.json"),
        help="Output JSON path for routine recommendation.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    labeled_rows = read_rows(args.labeled_csv)
    manifest_rows = read_manifest_rows(args.manifest_csv)
    manifest_by_asset = build_manifest_by_asset(manifest_rows)
    image_by_asset = build_image_lookup(args.images_dir)
    series_variety_map = load_series_variety_map(args.series_map_csv)
    pot_series_overrides = load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(args.baseline_map_csv)

    run_dates = sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in labeled_rows
            if (row.get("capture_date", "") or "").strip()
        }
    )
    if not run_dates:
        raise ValueError("No capture_date values found in labeled CSV")

    profiles: List[Dict[str, object]] = []
    for run_date in run_dates:
        profiles.append(
            build_profile(
                run_date=run_date,
                labeled_rows=labeled_rows,
                manifest_by_asset=manifest_by_asset,
                image_by_asset=image_by_asset,
                packet_crop_dir=args.packet_crop_dir,
                series_variety_map=series_variety_map,
                pot_series_overrides=pot_series_overrides,
                baseline_variety_map=baseline_variety_map,
            )
        )

    summary_payload = build_summary_payload(profiles)
    write_profiles_csv(args.output_csv, profiles)
    write_summary_json(args.output_json, summary_payload)

    latest_run_date = summary_payload["latest_run_date"]
    latest_run_mode = summary_payload["latest_run_mode"]
    print(f"run_dates={','.join(run_dates)}")
    print(f"latest_run_date={latest_run_date}")
    print(f"latest_run_mode={latest_run_mode}")
    print(f"output_csv={args.output_csv}")
    print(f"output_json={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
