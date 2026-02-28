#!/usr/bin/env python3
"""Run v1.4 computer-vision research experiments on tomato pot photos."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np


TOMATO_CAPTION_ID_RE = re.compile(r"\btomato[_\s-]*([0-9]{1,3})\b", re.IGNORECASE)


def tomato_caption_id(caption: str) -> int:
    text = (caption or "").strip()
    if not text:
        return 0
    matched = TOMATO_CAPTION_ID_RE.search(text)
    if not matched:
        return 0
    return int(matched.group(1))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def normalize_pot_id(raw: str) -> str:
    cleaned = "".join(ch for ch in (raw or "").strip().upper() if ch.isalnum())
    if not cleaned:
        return ""
    if cleaned.endswith("T"):
        number = cleaned[:-1]
    else:
        number = cleaned
    if not number.isdigit():
        return ""
    as_int = int(number)
    if as_int <= 0:
        return ""
    return f"{as_int}T"


def pot_number_from_id(pot_id: str) -> int:
    cleaned = normalize_pot_id(pot_id)
    if not cleaned:
        return 0
    return int(cleaned[:-1])


def safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def coefficient_of_variation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = float(np.mean(values))
    if math.isclose(mean, 0.0, abs_tol=1e-9):
        return 0.0
    std = float(np.std(values))
    return std / abs(mean)


def build_image_lookup(images_dir: Path) -> Dict[str, Path]:
    lookup: Dict[str, Path] = {}
    for path in sorted(images_dir.glob("*.jpg")):
        stem = path.stem
        if "_" not in stem:
            continue
        _, asset_id = stem.split("_", 1)
        lookup[asset_id] = path
    return lookup


@dataclass(frozen=True)
class BaselineEntry:
    pot_number: int
    source_asset_id: str
    capture_date: str


def build_baseline_lookup(rows: Sequence[Dict[str, str]]) -> Dict[int, BaselineEntry]:
    best: Dict[int, BaselineEntry] = {}
    for row in rows:
        if (row.get("classification_label", "") or "").strip().lower() != "tomato":
            continue
        pot_number = tomato_caption_id((row.get("caption", "") or "").strip())
        if pot_number <= 0:
            continue
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        capture_date = (row.get("capture_date", "") or "").strip()
        if not source_asset_id or not capture_date:
            continue
        candidate = BaselineEntry(
            pot_number=pot_number,
            source_asset_id=source_asset_id,
            capture_date=capture_date,
        )
        existing = best.get(pot_number)
        if existing is None or candidate.capture_date < existing.capture_date:
            best[pot_number] = candidate
    return best


def compute_vegetation_mask(image_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    b, g, r = cv2.split(image_bgr.astype(np.float32))
    exg = (2.0 * g) - r - b
    exg_mask = (exg > 20.0) & (g > r)

    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    hsv_green = (h >= 25) & (h <= 100) & (s >= 35) & (v >= 30) & (g > r)

    merged = np.where(exg_mask | hsv_green, 255, 0).astype(np.uint8)
    kernel = np.ones((3, 3), dtype=np.uint8)
    merged = cv2.morphologyEx(merged, cv2.MORPH_OPEN, kernel)
    merged = cv2.morphologyEx(merged, cv2.MORPH_CLOSE, kernel)
    return merged


def crop_pot_focus_region(image_bgr: np.ndarray) -> np.ndarray:
    """Crop a center-bottom ROI where the target pot is typically framed."""
    height, width = image_bgr.shape[:2]
    x0 = int(width * 0.22)
    x1 = int(width * 0.78)
    y0 = int(height * 0.30)
    y1 = int(height * 0.96)
    if x1 <= x0 or y1 <= y0:
        return image_bgr
    return image_bgr[y0:y1, x0:x1]


def estimate_plant_count(
    canopy_components: int,
    vegetation_coverage: float,
    largest_component_ratio: float,
) -> int:
    if canopy_components <= 0 and vegetation_coverage < 0.01:
        return 0
    if canopy_components <= 0:
        return 1
    # Seedling-stage heuristic: coverage is usually a better proxy than raw connected
    # components, which often over-splits one plant into many leaf fragments.
    if vegetation_coverage < 0.03:
        return 1
    if vegetation_coverage < 0.07:
        return 2
    estimate = 3
    if largest_component_ratio > 0.06 and canopy_components <= 4:
        estimate = 2
    return max(1, min(estimate, 4))


def compute_cv_metrics(image_bgr: np.ndarray) -> Dict[str, float]:
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError("Expected a BGR image with shape HxWx3")

    image_bgr = crop_pot_focus_region(image_bgr)
    height, width = image_bgr.shape[:2]
    image_area = float(height * width)
    mask = compute_vegetation_mask(image_bgr)

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_component_area = max(150, int(image_area * 0.0004))
    valid_areas: List[int] = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_component_area:
            valid_areas.append(area)

    canopy_components = len(valid_areas)
    canopy_area = float(sum(valid_areas))
    vegetation_coverage = canopy_area / image_area if image_area > 0 else 0.0
    largest_component_ratio = (
        (max(valid_areas) / image_area) if valid_areas and image_area > 0 else 0.0
    )
    plant_count = estimate_plant_count(
        canopy_components=canopy_components,
        vegetation_coverage=vegetation_coverage,
        largest_component_ratio=largest_component_ratio,
    )

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    yellow_mask = (h >= 15) & (h <= 42) & (s >= 40) & (v >= 40)
    canopy_pixels = mask > 0
    canopy_count = int(np.count_nonzero(canopy_pixels))
    yellow_canopy_count = int(np.count_nonzero(yellow_mask & canopy_pixels))
    chlorosis_ratio = (
        (yellow_canopy_count / float(canopy_count)) if canopy_count > 0 else 0.0
    )

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(gray, threshold1=70, threshold2=140)
    edge_density = float(np.count_nonzero(edges)) / image_area if image_area > 0 else 0.0
    brightness_mean = float(v.mean())

    return {
        "width": float(width),
        "height": float(height),
        "vegetation_coverage": float(vegetation_coverage),
        "canopy_components": float(canopy_components),
        "largest_component_ratio": float(largest_component_ratio),
        "plant_count_estimate": float(plant_count),
        "chlorosis_ratio": float(chlorosis_ratio),
        "edge_density": float(edge_density),
        "blur_score": float(blur_score),
        "brightness_mean": float(brightness_mean),
    }


def compute_growth_delta(
    latest_coverage: float,
    baseline_coverage: Optional[float],
) -> Optional[float]:
    if baseline_coverage is None or baseline_coverage <= 0.0:
        return None
    return (latest_coverage - baseline_coverage) / baseline_coverage


def score_health(metrics: Dict[str, float], growth_delta: Optional[float]) -> float:
    coverage_norm = min(metrics["vegetation_coverage"] / 0.10, 1.0)
    chlorosis_norm = 1.0 - min(metrics["chlorosis_ratio"] / 0.45, 1.0)
    component_norm = max(
        0.0, 1.0 - (abs(metrics["plant_count_estimate"] - 2.0) / 3.0)
    )
    if growth_delta is None:
        growth_norm = 0.55
    else:
        growth_norm = max(0.0, min((growth_delta + 0.25) / 1.0, 1.0))

    quality_norm = 1.0
    if metrics["brightness_mean"] < 45 or metrics["brightness_mean"] > 225:
        quality_norm = 0.6
    if metrics["blur_score"] < 120:
        quality_norm *= 0.7

    score = (
        (45.0 * coverage_norm)
        + (20.0 * growth_norm)
        + (20.0 * chlorosis_norm)
        + (10.0 * component_norm)
        + (5.0 * quality_norm)
    )
    return round(max(0.0, min(score, 100.0)), 2)


def derive_survival_hypothesis(
    health_score: float,
    growth_delta: Optional[float],
    vegetation_coverage: float,
) -> str:
    if vegetation_coverage < 0.01:
        return "low"
    if (
        health_score >= 74
        and vegetation_coverage >= 0.07
        and (growth_delta is None or growth_delta >= -0.12)
    ):
        return "high"
    if health_score >= 45:
        return "moderate"
    return "low"


def derive_action_recommendation(
    metrics: Dict[str, float],
    growth_delta: Optional[float],
) -> Tuple[str, str]:
    if metrics["blur_score"] < 120:
        return (
            "retake_photo",
            "Retake this photo closer and in focus before making care changes.",
        )
    if metrics["plant_count_estimate"] >= 3 and metrics["vegetation_coverage"] > 0.055:
        return (
            "thin_seedlings",
            "Thin to the strongest 1-2 seedlings in this pot to reduce competition.",
        )
    if metrics["chlorosis_ratio"] >= 0.30:
        return (
            "check_nutrients",
            "Check nitrogen/magnesium availability and apply half-strength balanced feed.",
        )
    if growth_delta is not None and growth_delta < -0.20:
        return (
            "inspect_root_moisture",
            "Inspect root zone and moisture consistency; growth appears stalled since baseline.",
        )
    if metrics["vegetation_coverage"] < 0.02:
        return (
            "increase_light",
            "Increase direct morning light exposure and monitor soil moisture daily.",
        )
    return (
        "maintain_current_care",
        "Maintain current care and continue weekly monitoring.",
    )


def derive_data_quality_flag(metrics: Dict[str, float]) -> str:
    flags: List[str] = []
    if metrics["blur_score"] < 30:
        flags.append("blur_low")
    if metrics["brightness_mean"] < 45:
        flags.append("underexposed")
    if metrics["brightness_mean"] > 225:
        flags.append("overexposed")
    if metrics["vegetation_coverage"] < 0.01:
        flags.append("low_signal")
    return "|".join(flags) if flags else "ok"


def parse_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Unable to open image: {path}")
    return image


def assess_algorithm_status(
    availability_ratio: float,
    variation_coeff: float,
) -> str:
    if availability_ratio >= 0.9 and variation_coeff >= 0.15:
        return "helpful"
    if availability_ratio >= 0.6:
        return "promising_with_more_data"
    return "limited_current_data"


def build_algorithm_assessments(
    row_results: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    total = float(len(row_results)) if row_results else 1.0

    def metric_values(key: str) -> List[float]:
        values: List[float] = []
        for row in row_results:
            value = safe_float(row.get(key))
            if value is not None:
                values.append(value)
        return values

    def build(
        algorithm_key: str,
        metric_key: str,
        summary_note: str,
        helpful_note: str,
        value_filter=lambda value: True,
    ) -> Dict[str, object]:
        values = [v for v in metric_values(metric_key) if value_filter(v)]
        availability_ratio = len(values) / total
        variation_coeff = coefficient_of_variation(values)
        status = assess_algorithm_status(availability_ratio, variation_coeff)
        return {
            "algorithm_key": algorithm_key,
            "metric_key": metric_key,
            "status": status,
            "availability_ratio": round(availability_ratio, 3),
            "variation_coeff": round(variation_coeff, 3),
            "signal_summary": summary_note,
            "why_helpful": helpful_note,
        }

    growth_values = metric_values("growth_delta")
    growth_availability = len(growth_values) / total
    growth_variation = coefficient_of_variation(growth_values)
    growth_status = (
        "helpful"
        if growth_availability >= 0.6 and growth_variation >= 0.2
        else "promising_with_more_data"
        if growth_availability >= 0.2
        else "limited_current_data"
    )

    assessments = [
        build(
            algorithm_key="vegetation_segmentation_exg_hsv",
            metric_key="vegetation_coverage",
            summary_note="Excess-green + HSV mask for canopy coverage per pot image.",
            helpful_note=(
                "Captures leaf area proxy needed for growth and vigor tracking in "
                "foggy-light conditions."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        build(
            algorithm_key="connected_components_counting",
            metric_key="plant_count_estimate",
            summary_note="Connected-component count over vegetation mask for plant clump estimation.",
            helpful_note=(
                "Helps decide where thinning is needed when multiple seedlings compete "
                "in the same pot."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        build(
            algorithm_key="chlorosis_detection_hsv",
            metric_key="chlorosis_ratio",
            summary_note="HSV yellow-in-canopy ratio for stress/chlorosis proxy.",
            helpful_note=(
                "Flags nutrient or stress risk early when yellowing increases inside "
                "active foliage."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        {
            "algorithm_key": "temporal_growth_delta",
            "metric_key": "growth_delta",
            "status": growth_status,
            "availability_ratio": round(growth_availability, 3),
            "variation_coeff": round(growth_variation, 3),
            "signal_summary": "Canopy coverage delta against earliest baseline photo per pot.",
            "why_helpful": (
                "Gives directional growth signal and helps estimate survival probability, "
                "but currently limited by baseline availability."
            ),
        },
        build(
            algorithm_key="image_quality_gate_laplacian",
            metric_key="blur_score",
            summary_note="Laplacian variance for in-focus image quality gating.",
            helpful_note=(
                "Prevents over-trusting noisy measurements from blurry images by marking "
                "rows that need recapture."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
    ]
    return assessments


def write_outputs_csv(
    output_dir: Path,
    row_results: Sequence[Dict[str, object]],
    algorithm_assessments: Sequence[Dict[str, object]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "cv_experiment_results.csv"
    metrics_fields = [
        "pot_id",
        "pot_number",
        "variety_name",
        "capture_date",
        "source_asset_id",
        "photo_url",
        "image_path",
        "baseline_source_asset_id",
        "baseline_capture_date",
        "plant_count_estimate",
        "canopy_components",
        "vegetation_coverage",
        "chlorosis_ratio",
        "growth_delta",
        "health_score",
        "survival_hypothesis",
        "action_code",
        "action_recommendation",
        "data_quality_flag",
        "blur_score",
        "brightness_mean",
        "edge_density",
    ]
    with metrics_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metrics_fields)
        writer.writeheader()
        for row in row_results:
            writer.writerow({field: row.get(field, "") for field in metrics_fields})

    recommendations_path = output_dir / "pot_recommendations.csv"
    recommendation_fields = [
        "pot_id",
        "survival_hypothesis",
        "health_score",
        "action_code",
        "action_recommendation",
    ]
    with recommendations_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=recommendation_fields)
        writer.writeheader()
        for row in row_results:
            writer.writerow({field: row.get(field, "") for field in recommendation_fields})

    algo_path = output_dir / "algorithm_assessment.csv"
    algo_fields = [
        "algorithm_key",
        "metric_key",
        "status",
        "availability_ratio",
        "variation_coeff",
        "signal_summary",
        "why_helpful",
    ]
    with algo_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=algo_fields)
        writer.writeheader()
        for row in algorithm_assessments:
            writer.writerow({field: row.get(field, "") for field in algo_fields})


def write_summary_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def ensure_db_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_runs (
            run_id TEXT PRIMARY KEY,
            run_date TEXT NOT NULL,
            mapping_csv TEXT NOT NULL,
            labeled_csv TEXT NOT NULL,
            images_dir TEXT NOT NULL,
            output_dir TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            analyzed_rows INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS image_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            pot_id TEXT NOT NULL,
            pot_number INTEGER NOT NULL,
            capture_date TEXT NOT NULL,
            source_asset_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            baseline_source_asset_id TEXT,
            baseline_capture_date TEXT,
            plant_count_estimate INTEGER NOT NULL,
            canopy_components INTEGER NOT NULL,
            vegetation_coverage REAL NOT NULL,
            chlorosis_ratio REAL NOT NULL,
            growth_delta REAL,
            health_score REAL NOT NULL,
            survival_hypothesis TEXT NOT NULL,
            action_code TEXT NOT NULL,
            action_recommendation TEXT NOT NULL,
            data_quality_flag TEXT NOT NULL,
            blur_score REAL NOT NULL,
            brightness_mean REAL NOT NULL,
            edge_density REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, pot_id, source_asset_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algorithm_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            algorithm_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            status TEXT NOT NULL,
            availability_ratio REAL NOT NULL,
            variation_coeff REAL NOT NULL,
            signal_summary TEXT NOT NULL,
            why_helpful TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, algorithm_key)
        )
        """
    )
    conn.commit()


def persist_results(
    db_path: Path,
    run_id: str,
    run_date: str,
    mapping_csv: Path,
    labeled_csv: Path,
    images_dir: Path,
    output_dir: Path,
    total_rows: int,
    row_results: Sequence[Dict[str, object]],
    algorithm_assessments: Sequence[Dict[str, object]],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    now = iso_now()

    with sqlite3.connect(db_path) as conn:
        ensure_db_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO experiment_runs (
                run_id,
                run_date,
                mapping_csv,
                labeled_csv,
                images_dir,
                output_dir,
                total_rows,
                analyzed_rows,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_date,
                str(mapping_csv),
                str(labeled_csv),
                str(images_dir),
                str(output_dir),
                int(total_rows),
                int(len(row_results)),
                now,
            ),
        )

        conn.execute("DELETE FROM image_metrics WHERE run_id = ?", (run_id,))
        for row in row_results:
            conn.execute(
                """
                INSERT INTO image_metrics (
                    run_id,
                    pot_id,
                    pot_number,
                    capture_date,
                    source_asset_id,
                    image_path,
                    baseline_source_asset_id,
                    baseline_capture_date,
                    plant_count_estimate,
                    canopy_components,
                    vegetation_coverage,
                    chlorosis_ratio,
                    growth_delta,
                    health_score,
                    survival_hypothesis,
                    action_code,
                    action_recommendation,
                    data_quality_flag,
                    blur_score,
                    brightness_mean,
                    edge_density,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["pot_id"],
                    int(row["pot_number"]),
                    row["capture_date"],
                    row["source_asset_id"],
                    row["image_path"],
                    row["baseline_source_asset_id"],
                    row["baseline_capture_date"],
                    int(row["plant_count_estimate"]),
                    int(row["canopy_components"]),
                    float(row["vegetation_coverage"]),
                    float(row["chlorosis_ratio"]),
                    safe_float(row["growth_delta"]),
                    float(row["health_score"]),
                    row["survival_hypothesis"],
                    row["action_code"],
                    row["action_recommendation"],
                    row["data_quality_flag"],
                    float(row["blur_score"]),
                    float(row["brightness_mean"]),
                    float(row["edge_density"]),
                    now,
                ),
            )

        conn.execute("DELETE FROM algorithm_assessments WHERE run_id = ?", (run_id,))
        for row in algorithm_assessments:
            conn.execute(
                """
                INSERT INTO algorithm_assessments (
                    run_id,
                    algorithm_key,
                    metric_key,
                    status,
                    availability_ratio,
                    variation_coeff,
                    signal_summary,
                    why_helpful,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["algorithm_key"],
                    row["metric_key"],
                    row["status"],
                    float(row["availability_ratio"]),
                    float(row["variation_coeff"]),
                    row["signal_summary"],
                    row["why_helpful"],
                    now,
                ),
            )
        conn.commit()


def sort_key_for_result(row: Dict[str, object]) -> Tuple[int, str]:
    pot_number = int(row.get("pot_number", 0) or 0)
    return (pot_number, str(row.get("pot_id", "")))


def short_growth_text(growth_delta: Optional[float]) -> str:
    if growth_delta is None:
        return "n/a"
    return f"{growth_delta * 100:.1f}%"


def write_markdown_report(
    report_path: Path,
    run_id: str,
    run_date: str,
    mapping_csv: Path,
    labeled_csv: Path,
    images_dir: Path,
    db_path: Path,
    output_dir: Path,
    row_results: Sequence[Dict[str, object]],
    algorithm_assessments: Sequence[Dict[str, object]],
) -> None:
    sorted_rows = sorted(row_results, key=sort_key_for_result)
    status_counts = Counter(str(row.get("survival_hypothesis", "")) for row in sorted_rows)
    action_counts = Counter(str(row.get("action_code", "")) for row in sorted_rows)

    lines: List[str] = []
    lines.append("# V1.4 Computer Vision Research")
    lines.append("")
    lines.append(f"Generated at: {iso_now()}")
    lines.append(f"Run ID: `{run_id}`")
    lines.append(f"Run date (photo set): `{run_date}`")
    lines.append("")
    lines.append("## Scope and Constraints")
    lines.append("")
    lines.append("- Production tracker pages and production data pipeline remain unchanged.")
    lines.append("- All v1.4 outputs are isolated to:")
    lines.append(f"  - local research DB: `{db_path}`")
    lines.append(f"  - research output folder: `{output_dir}`")
    lines.append("- Dataset: the 32-pot tomato mapping photo run.")
    lines.append(f"- Mapping CSV: `{mapping_csv}`")
    lines.append(f"- Baseline CSV (for growth deltas): `{labeled_csv}`")
    lines.append(f"- Local image cache: `{images_dir}`")
    lines.append("")
    lines.append("## Algorithms Evaluated")
    lines.append("")
    lines.append("| Algorithm | Status | Availability | Variation | Why it matters |")
    lines.append("|---|---:|---:|---:|---|")
    for algo in algorithm_assessments:
        lines.append(
            "| "
            f"`{algo['algorithm_key']}` | "
            f"{algo['status']} | "
            f"{float(algo['availability_ratio']) * 100:.1f}% | "
            f"{float(algo['variation_coeff']):.3f} | "
            f"{algo['why_helpful']} |"
        )
    lines.append("")
    lines.append("## High-Level Findings")
    lines.append("")
    lines.append(f"- Pots analyzed: `{len(sorted_rows)}`")
    lines.append(
        "- Survival hypothesis distribution: "
        f"high={status_counts.get('high', 0)}, "
        f"moderate={status_counts.get('moderate', 0)}, "
        f"low={status_counts.get('low', 0)}"
    )
    lines.append(
        "- Most common next-action tags: "
        + ", ".join(f"{key}={value}" for key, value in action_counts.most_common(5))
    )
    lines.append("")
    lines.append("## Pot-Level Suggestions (All 32)")
    lines.append("")
    lines.append(
        "| Pot | Plant Count Est. | Coverage | Chlorosis | Growth vs Baseline | Health | Survival | Action |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")
    for row in sorted_rows:
        growth_delta = safe_float(row.get("growth_delta"))
        lines.append(
            "| "
            f"{row['pot_id']} | "
            f"{int(row['plant_count_estimate'])} | "
            f"{float(row['vegetation_coverage']) * 100:.1f}% | "
            f"{float(row['chlorosis_ratio']) * 100:.1f}% | "
            f"{short_growth_text(growth_delta)} | "
            f"{float(row['health_score']):.1f} | "
            f"{row['survival_hypothesis']} | "
            f"{row['action_code']} |"
        )
    lines.append("")
    lines.append("## Project-Advancement Hypotheses")
    lines.append("")
    lines.append(
        "- `vegetation_segmentation_exg_hsv` and `connected_components_counting` are immediately useful for "
        "automated weekly triage: they identify low-coverage pots and pots likely needing thinning."
    )
    lines.append(
        "- `chlorosis_detection_hsv` is a promising stress proxy; combine with manual checks to reduce false positives "
        "from warm sunlight and packet-color contamination."
    )
    lines.append(
        "- `temporal_growth_delta` is directionally useful for survival hypotheses, but should be strengthened by "
        "capturing baseline-style framing for all 32 pots."
    )
    lines.append(
        "- `image_quality_gate_laplacian` should be retained as a mandatory precondition for any fully automated "
        "decision support, to avoid acting on blurry photos."
    )
    lines.append("")
    lines.append("## Recommended Next Research Iterations")
    lines.append("")
    lines.append(
        "1. Add a pot detector/segmenter model (instance segmentation) to separate neighboring pots and improve count precision."
    )
    lines.append(
        "2. Add leaf-condition classes (curling/wilt/necrosis) using a small manually labeled set from this photo corpus."
    )
    lines.append(
        "3. Standardize image capture angle/distance for weekly runs so growth deltas become more reliable."
    )
    lines.append(
        "4. Join CV metrics with weather/advisory records to test whether stress spikes correlate with fog, temperature swings, or alerts."
    )
    lines.append("")
    calibration_summary_path = output_dir / "calibration_summary.json"
    calibration_subset_path = output_dir / "manual_calibration_subset.csv"
    if calibration_summary_path.exists():
        try:
            calibration_payload = json.loads(
                calibration_summary_path.read_text(encoding="utf-8")
            )
            lines.append("## Manual Calibration Check")
            lines.append("")
            lines.append(
                "- Manual subset rows: "
                f"`{int(calibration_payload.get('manual_rows', 0))}`"
            )
            lines.append(
                "- Survival accuracy: "
                f"`{float(calibration_payload.get('survival_accuracy', 0.0)) * 100:.1f}%`"
            )
            lines.append(
                "- Action accuracy: "
                f"`{float(calibration_payload.get('action_accuracy', 0.0)) * 100:.1f}%`"
            )
            lines.append(
                "- Joint accuracy: "
                f"`{float(calibration_payload.get('joint_accuracy', 0.0)) * 100:.1f}%`"
            )
            mismatch_count = len(calibration_payload.get("mismatches", []))
            lines.append(f"- Remaining mismatch rows: `{mismatch_count}`")
            lines.append("")
        except Exception:
            pass

    lines.append("## Calibration Assets")
    lines.append("")
    lines.append(
        "- Manual subset CSV: "
        f"`{calibration_subset_path if calibration_subset_path.exists() else output_dir / 'manual_calibration_subset.csv'}`"
    )
    lines.append(
        "- Calibration report: "
        f"`{output_dir / 'calibration_report.md'}`"
    )
    lines.append(
        "- Calibration summary JSON: "
        f"`{output_dir / 'calibration_summary.json'}`"
    )
    lines.append("")
    lines.append("## Output Artifacts")
    lines.append("")
    lines.append(f"- `{output_dir / 'cv_experiment_results.csv'}`")
    lines.append(f"- `{output_dir / 'pot_recommendations.csv'}`")
    lines.append(f"- `{output_dir / 'algorithm_assessment.csv'}`")
    lines.append(f"- `{output_dir / 'research_summary.json'}`")
    lines.append(f"- `{db_path}`")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    mapping_csv: Path,
    labeled_csv: Path,
    images_dir: Path,
    db_path: Path,
    output_dir: Path,
    report_path: Path,
    run_id: Optional[str] = None,
) -> Dict[str, object]:
    mapping_rows = read_csv_rows(mapping_csv)
    labeled_rows = read_csv_rows(labeled_csv)
    image_lookup = build_image_lookup(images_dir)
    baseline_lookup = build_baseline_lookup(labeled_rows)

    run_date = max(
        ((row.get("capture_date", "") or "").strip() for row in mapping_rows),
        default="",
    )
    if not run_date:
        raise ValueError(f"No capture_date values found in {mapping_csv}")

    actual_run_id = run_id or f"v1_4_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    row_results: List[Dict[str, object]] = []
    missing_images: List[str] = []

    for row in mapping_rows:
        if (row.get("classification_label", "") or "").strip().lower() != "tomato":
            continue
        pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
        if not pot_id:
            continue
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue

        image_path = image_lookup.get(source_asset_id)
        if image_path is None or not image_path.exists():
            missing_images.append(source_asset_id)
            continue

        image = parse_image(image_path)
        metrics = compute_cv_metrics(image)

        pot_number = pot_number_from_id(pot_id)
        baseline_entry = baseline_lookup.get(pot_number)
        baseline_coverage: Optional[float] = None
        baseline_asset_id = ""
        baseline_capture_date = ""
        if baseline_entry is not None:
            baseline_asset_id = baseline_entry.source_asset_id
            baseline_capture_date = baseline_entry.capture_date
            baseline_path = image_lookup.get(baseline_entry.source_asset_id)
            if baseline_path is not None and baseline_path.exists():
                baseline_image = parse_image(baseline_path)
                baseline_metrics = compute_cv_metrics(baseline_image)
                baseline_coverage = baseline_metrics["vegetation_coverage"]

        growth_delta = compute_growth_delta(
            latest_coverage=metrics["vegetation_coverage"],
            baseline_coverage=baseline_coverage,
        )
        health_score = score_health(metrics, growth_delta)
        survival = derive_survival_hypothesis(
            health_score=health_score,
            growth_delta=growth_delta,
            vegetation_coverage=metrics["vegetation_coverage"],
        )
        action_code, action_text = derive_action_recommendation(metrics, growth_delta)
        quality_flag = derive_data_quality_flag(metrics)

        row_results.append(
            {
                "pot_id": pot_id,
                "pot_number": pot_number,
                "variety_name": (row.get("variety_name", "") or "").strip(),
                "capture_date": (row.get("capture_date", "") or "").strip(),
                "source_asset_id": source_asset_id,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "image_path": str(image_path),
                "baseline_source_asset_id": baseline_asset_id,
                "baseline_capture_date": baseline_capture_date,
                "plant_count_estimate": int(metrics["plant_count_estimate"]),
                "canopy_components": int(metrics["canopy_components"]),
                "vegetation_coverage": round(metrics["vegetation_coverage"], 6),
                "chlorosis_ratio": round(metrics["chlorosis_ratio"], 6),
                "growth_delta": None if growth_delta is None else round(growth_delta, 6),
                "health_score": health_score,
                "survival_hypothesis": survival,
                "action_code": action_code,
                "action_recommendation": action_text,
                "data_quality_flag": quality_flag,
                "blur_score": round(metrics["blur_score"], 3),
                "brightness_mean": round(metrics["brightness_mean"], 3),
                "edge_density": round(metrics["edge_density"], 6),
            }
        )

    row_results = sorted(row_results, key=sort_key_for_result)
    algorithm_assessments = build_algorithm_assessments(row_results)

    write_outputs_csv(
        output_dir=output_dir,
        row_results=row_results,
        algorithm_assessments=algorithm_assessments,
    )

    summary_payload = {
        "run_id": actual_run_id,
        "run_date": run_date,
        "total_mapping_rows": len(mapping_rows),
        "analyzed_rows": len(row_results),
        "missing_image_assets": missing_images,
        "survival_counts": Counter(
            str(row.get("survival_hypothesis", "")) for row in row_results
        ),
        "action_counts": Counter(str(row.get("action_code", "")) for row in row_results),
        "algorithm_assessments": algorithm_assessments,
        "created_at": iso_now(),
    }
    write_summary_json(output_dir / "research_summary.json", summary_payload)

    persist_results(
        db_path=db_path,
        run_id=actual_run_id,
        run_date=run_date,
        mapping_csv=mapping_csv,
        labeled_csv=labeled_csv,
        images_dir=images_dir,
        output_dir=output_dir,
        total_rows=len(mapping_rows),
        row_results=row_results,
        algorithm_assessments=algorithm_assessments,
    )

    write_markdown_report(
        report_path=report_path,
        run_id=actual_run_id,
        run_date=run_date,
        mapping_csv=mapping_csv,
        labeled_csv=labeled_csv,
        images_dir=images_dir,
        db_path=db_path,
        output_dir=output_dir,
        row_results=row_results,
        algorithm_assessments=algorithm_assessments,
    )

    return {
        "run_id": actual_run_id,
        "run_date": run_date,
        "total_mapping_rows": len(mapping_rows),
        "analyzed_rows": len(row_results),
        "missing_images": len(missing_images),
        "db_path": str(db_path),
        "output_dir": str(output_dir),
        "report_path": str(report_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v1.4 CV experiments on 32 tomato pot photos into an isolated research DB."
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Tomato 32-pot mapping CSV input.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed CSV used for earliest baseline references.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Local image cache directory.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("local/cv_research/v1_4_cv_research.db"),
        help="Isolated research SQLite DB path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/v1_4"),
        help="Research CSV/JSON output folder.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("docs/V1.4-CV-RESEARCH.md"),
        help="Markdown research report path to generate/update.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional fixed run id. Default auto-generates with UTC timestamp.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = run_pipeline(
        mapping_csv=args.mapping_csv,
        labeled_csv=args.labeled_csv,
        images_dir=args.images_dir,
        db_path=args.db_path,
        output_dir=args.output_dir,
        report_path=args.report_path,
        run_id=args.run_id.strip() or None,
    )
    for key, value in results.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
