#!/usr/bin/env python3
"""Generate label suggestions for newly ingested unknown rows."""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import cv2


@dataclass(frozen=True)
class RefRow:
    row_index: int
    source_asset_id: str
    classification_label: str
    species_common_name: str
    variety_name: str
    species_scientific_name: str
    feature: cv2.typing.MatLike


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def normalize_label(value: str) -> str:
    return (value or "").strip().lower()


def crop_center(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    height, width = image.shape[:2]
    x0 = int(width * 0.20)
    x1 = int(width * 0.80)
    y0 = int(height * 0.20)
    y1 = int(height * 0.96)
    if x1 <= x0 or y1 <= y0:
        return image
    return image[y0:y1, x0:x1]


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


def feature_similarity(a: cv2.typing.MatLike, b: cv2.typing.MatLike) -> float:
    return float(a.dot(b))


def confidence_tier(margin: float) -> str:
    if margin >= 0.08:
        return "high"
    if margin >= 0.05:
        return "medium"
    return "low"


def confidence_value(margin: float) -> float:
    score = 0.55 + (margin * 2.0)
    if score < 0.55:
        score = 0.55
    if score > 0.95:
        score = 0.95
    return round(score, 3)


def read_manifest_ids_from_git_ref(ref: str) -> Set[str]:
    try:
        text = subprocess.check_output(["git", "show", ref], text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Unable to read manifest from git ref {ref}: {exc}") from exc
    rows = list(csv.DictReader(io.StringIO(text)))
    return {(row.get("source_asset_id", "") or "").strip() for row in rows if (row.get("source_asset_id", "") or "").strip()}


def build_reference_rows(rows: Sequence[Dict[str, str]], image_dir: Path) -> List[RefRow]:
    refs: List[RefRow] = []
    for row_index, row in enumerate(rows, start=1):
        label = normalize_label(row.get("classification_label", ""))
        if label not in {"tomato", "non_tomato"}:
            continue
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue
        image_path = image_dir / f"{row_index:02d}_{source_asset_id}.jpg"
        if not image_path.exists():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        refs.append(
            RefRow(
                row_index=row_index,
                source_asset_id=source_asset_id,
                classification_label=label,
                species_common_name=(row.get("species_common_name", "") or "").strip(),
                variety_name=(row.get("variety_name", "") or "").strip(),
                species_scientific_name=(row.get("species_scientific_name", "") or "").strip(),
                feature=compute_visual_feature(image),
            )
        )
    return refs


def find_best_match(feature: cv2.typing.MatLike, refs: Sequence[RefRow], target_label: str) -> Tuple[float, RefRow | None]:
    best_score = -1.0
    best_ref: RefRow | None = None
    for ref in refs:
        if ref.classification_label != target_label:
            continue
        score = feature_similarity(feature, ref.feature)
        if score > best_score:
            best_score = score
            best_ref = ref
    return best_score, best_ref


def derive_species_common(predicted_label: str, ref: RefRow | None) -> str:
    if predicted_label == "tomato":
        return "Tomato"
    if ref and ref.species_common_name:
        return ref.species_common_name
    return "unknown"


def derive_variety(predicted_label: str, ref: RefRow | None) -> str:
    if predicted_label == "tomato" and ref:
        return ref.variety_name or ""
    if predicted_label == "non_tomato" and ref:
        return ref.variety_name or ref.species_common_name or ""
    return ""


def derive_scientific_name(predicted_label: str, ref: RefRow | None) -> str:
    if predicted_label == "tomato":
        return "Solanum lycopersicum"
    if ref and ref.species_scientific_name:
        return ref.species_scientific_name
    return "unknown"


def build_suggestions(
    rows: Sequence[Dict[str, str]],
    refs: Sequence[RefRow],
    image_dir: Path,
    new_asset_ids: Set[str],
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    suggestions: List[Dict[str, object]] = []
    missing_images = 0

    for row_index, row in enumerate(rows, start=1):
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id or source_asset_id not in new_asset_ids:
            continue
        if normalize_label(row.get("classification_label", "")) != "unknown":
            continue

        image_path = image_dir / f"{row_index:02d}_{source_asset_id}.jpg"
        if not image_path.exists():
            missing_images += 1
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            missing_images += 1
            continue

        feature = compute_visual_feature(image)
        tomato_score, tomato_ref = find_best_match(feature, refs, "tomato")
        non_score, non_ref = find_best_match(feature, refs, "non_tomato")

        if tomato_score >= non_score:
            predicted = "tomato"
            margin = tomato_score - non_score
            chosen_ref = tomato_ref
        else:
            predicted = "non_tomato"
            margin = non_score - tomato_score
            chosen_ref = non_ref

        tier = confidence_tier(margin)
        suggestions.append(
            {
                "row_index": row_index,
                "capture_date": (row.get("capture_date", "") or "").strip(),
                "source_asset_id": source_asset_id,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "current_classification_label": "unknown",
                "predicted_classification_label": predicted,
                "predicted_species_common_name": derive_species_common(predicted, chosen_ref),
                "predicted_variety_name": derive_variety(predicted, chosen_ref),
                "predicted_species_scientific_name": derive_scientific_name(predicted, chosen_ref),
                "tomato_similarity": round(tomato_score, 6),
                "non_tomato_similarity": round(non_score, 6),
                "margin": round(margin, 6),
                "confidence_tier": tier,
                "recommended_action": "apply_seed_override" if tier in {"high", "medium"} else "manual_review",
                "nearest_tomato_asset_id": tomato_ref.source_asset_id if tomato_ref else "",
                "nearest_non_tomato_asset_id": non_ref.source_asset_id if non_ref else "",
                "image_path": str(image_path),
            }
        )

    suggestions.sort(
        key=lambda row: (
            row.get("capture_date", ""),
            -float(row.get("margin", 0.0) or 0.0),
            int(row.get("row_index", 0) or 0),
        )
    )

    tier_counts = Counter((row.get("confidence_tier", "") or "") for row in suggestions)
    pred_counts = Counter((row.get("predicted_classification_label", "") or "") for row in suggestions)
    by_date = Counter((row.get("capture_date", "") or "") for row in suggestions)

    summary = {
        "suggestion_rows": len(suggestions),
        "missing_images": missing_images,
        "prediction_counts": dict(sorted(pred_counts.items())),
        "confidence_tier_counts": dict(sorted(tier_counts.items())),
        "capture_date_counts": dict(sorted(by_date.items())),
    }
    return suggestions, summary


def build_override_seed_rows(suggestions: Sequence[Dict[str, object]], min_margin: float) -> List[Dict[str, object]]:
    seed: List[Dict[str, object]] = []
    for row in suggestions:
        margin = float(row.get("margin", 0.0) or 0.0)
        if margin < min_margin:
            continue
        predicted = str(row.get("predicted_classification_label", "") or "")
        seed.append(
            {
                "row_index": int(row.get("row_index", 0) or 0),
                "source_asset_id": str(row.get("source_asset_id", "") or ""),
                "classification_label": predicted,
                "species_common_name": str(row.get("predicted_species_common_name", "") or ""),
                "variety_name": str(row.get("predicted_variety_name", "") or ""),
                "species_scientific_name": str(row.get("predicted_species_scientific_name", "") or ""),
                "confidence": str(confidence_value(margin)),
                "labeling_method": "visual_similarity_nn_v17_seed",
                "notes_append": (
                    "auto-seed from v17 visual similarity; "
                    f"tomato_sim={row.get('tomato_similarity')} non_tomato_sim={row.get('non_tomato_similarity')} "
                    f"margin={row.get('margin')}"
                ),
            }
        )
    return seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate new-batch label suggestions from visual similarity.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Input labeled mixed CSV.",
    )
    parser.add_argument(
        "--current-manifest-csv",
        type=Path,
        default=Path("data/intake/google_photos/album_manifest.csv"),
        help="Current manifest used for new-asset ID set.",
    )
    parser.add_argument(
        "--baseline-manifest-git-ref",
        default="HEAD:data/intake/google_photos/album_manifest.csv",
        help="Git ref path used as baseline manifest for new asset detection.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Image directory for downloaded assets.",
    )
    parser.add_argument(
        "--seed-min-margin",
        type=float,
        default=0.05,
        help="Minimum margin required to include row in override-seed CSV.",
    )
    parser.add_argument(
        "--output-suggestions-csv",
        type=Path,
        default=Path("data/research/v1_7/new_batch_label_suggestions.csv"),
        help="Detailed per-row suggestion output.",
    )
    parser.add_argument(
        "--output-seed-csv",
        type=Path,
        default=Path("data/research/v1_7/new_batch_label_override_seed.csv"),
        help="High-confidence override seed CSV.",
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("data/research/v1_7/new_batch_label_suggestions_summary.json"),
        help="Summary JSON output.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_csv_rows(args.labeled_csv)
    current_manifest_rows = read_csv_rows(args.current_manifest_csv)
    current_ids = {
        (row.get("source_asset_id", "") or "").strip()
        for row in current_manifest_rows
        if (row.get("source_asset_id", "") or "").strip()
    }
    baseline_ids = read_manifest_ids_from_git_ref(args.baseline_manifest_git_ref)
    new_asset_ids = current_ids - baseline_ids

    refs = build_reference_rows(rows, args.image_dir)
    suggestions, summary = build_suggestions(rows, refs, args.image_dir, new_asset_ids)
    seed_rows = build_override_seed_rows(suggestions, min_margin=args.seed_min_margin)

    write_csv(
        args.output_suggestions_csv,
        suggestions,
        fieldnames=[
            "row_index",
            "capture_date",
            "source_asset_id",
            "photo_url",
            "current_classification_label",
            "predicted_classification_label",
            "predicted_species_common_name",
            "predicted_variety_name",
            "predicted_species_scientific_name",
            "tomato_similarity",
            "non_tomato_similarity",
            "margin",
            "confidence_tier",
            "recommended_action",
            "nearest_tomato_asset_id",
            "nearest_non_tomato_asset_id",
            "image_path",
        ],
    )

    write_csv(
        args.output_seed_csv,
        seed_rows,
        fieldnames=[
            "row_index",
            "source_asset_id",
            "classification_label",
            "species_common_name",
            "variety_name",
            "species_scientific_name",
            "confidence",
            "labeling_method",
            "notes_append",
        ],
    )

    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **summary,
        "baseline_manifest_git_ref": args.baseline_manifest_git_ref,
        "baseline_manifest_row_count": len(baseline_ids),
        "current_manifest_row_count": len(current_ids),
        "new_asset_count": len(new_asset_ids),
        "reference_rows": len(refs),
        "seed_rows": len(seed_rows),
        "seed_min_margin": args.seed_min_margin,
    }
    args.output_summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"baseline_manifest_git_ref={args.baseline_manifest_git_ref}")
    print(f"baseline_manifest_row_count={len(baseline_ids)}")
    print(f"current_manifest_row_count={len(current_ids)}")
    print(f"new_asset_count={len(new_asset_ids)}")
    print(f"reference_rows={len(refs)}")
    print(f"suggestion_rows={len(suggestions)}")
    print(f"seed_rows={len(seed_rows)}")
    print(f"output_suggestions_csv={args.output_suggestions_csv}")
    print(f"output_seed_csv={args.output_seed_csv}")
    print(f"output_summary_json={args.output_summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
