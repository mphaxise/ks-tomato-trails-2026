#!/usr/bin/env python3
"""Run v1.10 pot-anchored CV research experiments on indoor tomato-pot photos."""

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


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv_rows(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_summary_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


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


def normalize_pot_id(raw: str) -> str:
    cleaned = "".join(ch for ch in (raw or "").strip().upper() if ch.isalnum())
    if not cleaned:
        return ""
    if cleaned.endswith("T"):
        cleaned = cleaned[:-1]
    if not cleaned.isdigit():
        return ""
    as_int = int(cleaned)
    if as_int <= 0:
        return ""
    return f"{as_int}T"


def pot_number_from_id(pot_id: str) -> int:
    normalized = normalize_pot_id(pot_id)
    if not normalized:
        return 0
    return int(normalized[:-1])


def tomato_caption_id(caption: str) -> int:
    matched = TOMATO_CAPTION_ID_RE.search((caption or "").strip())
    if not matched:
        return 0
    return int(matched.group(1))


def coefficient_of_variation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = float(np.mean(values))
    if math.isclose(mean, 0.0, abs_tol=1e-9):
        return 0.0
    std = float(np.std(values))
    return std / abs(mean)


def clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


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
        pot_number = tomato_caption_id(row.get("caption", "") or "")
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


def select_latest_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    valid_rows = [row for row in rows if normalize_pot_id(row.get("pot_id", "") or "")]
    if not valid_rows:
        return []
    latest_capture_date = max((row.get("capture_date", "") or "").strip() for row in valid_rows)
    rows_for_date = [
        row
        for row in valid_rows
        if (row.get("capture_date", "") or "").strip() == latest_capture_date
    ]
    deduped: Dict[str, Dict[str, str]] = {}
    for row in rows_for_date:
        pot_id = normalize_pot_id(row.get("pot_id", "") or "")
        if not pot_id:
            continue
        existing = deduped.get(pot_id)
        if existing is None:
            deduped[pot_id] = row
            continue
        row_key = (
            (row.get("captured_at", "") or "").strip(),
            (row.get("row_index", "") or "").strip(),
            (row.get("source_asset_id", "") or "").strip(),
        )
        existing_key = (
            (existing.get("captured_at", "") or "").strip(),
            (existing.get("row_index", "") or "").strip(),
            (existing.get("source_asset_id", "") or "").strip(),
        )
        if row_key > existing_key:
            deduped[pot_id] = row
    return sorted(deduped.values(), key=lambda row: pot_number_from_id(row.get("pot_id", "") or ""))


def parse_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Unable to open image: {path}")
    return image


def compute_vegetation_mask(image_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    b, g, r = cv2.split(image_bgr.astype(np.float32))
    exg = (2.0 * g) - r - b
    exg_mask = (exg > 12.0) & (g > r)

    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    hsv_green = (h >= 22) & (h <= 100) & (s >= 35) & (v >= 35) & (g > r)

    merged = np.where(exg_mask | hsv_green, 255, 0).astype(np.uint8)
    merged = cv2.morphologyEx(merged, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    merged = cv2.morphologyEx(merged, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    return merged


def detect_primary_canopy(image_bgr: np.ndarray, vegetation_mask: np.ndarray) -> Optional[Dict[str, float]]:
    height, width = image_bgr.shape[:2]
    image_area = float(height * width)
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(vegetation_mask, 8)
    min_area = max(220, int(image_area * 0.002))
    best: Optional[Dict[str, float]] = None
    best_score = -1.0
    for label in range(1, num_labels):
        x, y, w, h, area = [int(stats[label, idx]) for idx in range(5)]
        if area < min_area:
            continue
        cx = float(centroids[label][0])
        cy = float(centroids[label][1])
        center_score = clamp01(1.0 - abs(cx - (width / 2.0)) / (width / 2.0))
        vertical_score = clamp01(1.0 - abs(cy - (height * 0.52)) / (height * 0.52))
        area_score = clamp01(area / (image_area * 0.08))
        score = (0.45 * center_score) + (0.20 * vertical_score) + (0.35 * area_score)
        if score <= best_score:
            continue
        best_score = score
        best = {
            "x": float(x),
            "y": float(y),
            "w": float(w),
            "h": float(h),
            "area": float(area),
            "cx": cx,
            "cy": cy,
            "confidence": round(clamp01(score), 3),
        }
    return best


def detect_label_anchor(
    image_bgr: np.ndarray,
    canopy_anchor: Optional[Dict[str, float]],
) -> Optional[Dict[str, float]]:
    height, width = image_bgr.shape[:2]
    image_area = float(height * width)

    max_channel = image_bgr.max(axis=2).astype(np.int16)
    min_channel = image_bgr.min(axis=2).astype(np.int16)
    bright_mask = ((max_channel > 150) & ((max_channel - min_channel) < 70)).astype(np.uint8) * 255
    bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best: Optional[Dict[str, float]] = None
    best_score = -1.0
    canopy_cx = canopy_anchor["cx"] if canopy_anchor is not None else width / 2.0
    canopy_cy = canopy_anchor["cy"] if canopy_anchor is not None else height * 0.52
    diagonal = math.hypot(width, height)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = float(w * h)
        if area < image_area * 0.0015 or area > image_area * 0.09:
            continue
        aspect = h / max(w, 1.0)
        fill_ratio = cv2.contourArea(contour) / max(area, 1.0)
        if aspect < 1.2 or aspect > 10.0 or fill_ratio < 0.35:
            continue
        cx = x + (w / 2.0)
        cy = y + (h / 2.0)
        canopy_proximity = clamp01(1.0 - (math.hypot(cx - canopy_cx, cy - canopy_cy) / diagonal) * 1.7)
        center_score = clamp01(1.0 - abs(cx - (width / 2.0)) / (width / 2.0))
        lower_score = clamp01(cy / max(height, 1.0))
        area_score = clamp01(area / (image_area * 0.018))
        score = (
            (0.45 * canopy_proximity)
            + (0.20 * center_score)
            + (0.15 * lower_score)
            + (0.20 * area_score)
        )
        if score <= best_score:
            continue
        best_score = score
        best = {
            "x": float(x),
            "y": float(y),
            "w": float(w),
            "h": float(h),
            "area": area,
            "cx": float(cx),
            "cy": float(cy),
            "confidence": round(clamp01(score), 3),
        }
    return best


def infer_pot_polygon(
    image_bgr: np.ndarray,
    canopy_anchor: Optional[Dict[str, float]],
    label_anchor: Optional[Dict[str, float]],
) -> Dict[str, object]:
    height, width = image_bgr.shape[:2]
    if canopy_anchor is not None:
        cx = canopy_anchor["cx"]
        x = canopy_anchor["x"]
        y = canopy_anchor["y"]
        w = canopy_anchor["w"]
        h = canopy_anchor["h"]
        top_y = int(y + (h * 0.55))
        if label_anchor is not None and abs(label_anchor["cx"] - cx) <= max(w * 1.25, width * 0.18):
            top_y = min(top_y, int(label_anchor["y"] + (label_anchor["h"] * 0.92)))
        pot_height = max(int(h * 2.7), int(height * 0.28))
        half_top = max(int(w * 0.95), int(width * 0.13))
        half_bottom = max(int(half_top * 1.20), int(width * 0.16))
        anchor_mode = "plant"
        confidence = float(canopy_anchor["confidence"])
    elif label_anchor is not None:
        cx = label_anchor["cx"]
        top_y = int(label_anchor["y"] + (label_anchor["h"] * 0.90))
        pot_height = max(int(label_anchor["h"] * 1.25), int(height * 0.24))
        half_top = max(int(label_anchor["w"] * 2.10), int(width * 0.12))
        half_bottom = max(int(half_top * 1.15), int(width * 0.15))
        anchor_mode = "label"
        confidence = float(label_anchor["confidence"]) * 0.85
    else:
        cx = width / 2.0
        top_y = int(height * 0.42)
        pot_height = int(height * 0.34)
        half_top = int(width * 0.22)
        half_bottom = int(width * 0.26)
        anchor_mode = "fallback"
        confidence = 0.18

    top_y = max(int(height * 0.18), min(height - 2, top_y))
    bottom_y = min(height - 1, top_y + pot_height)
    left_top = max(0, int(round(cx - half_top)))
    right_top = min(width - 1, int(round(cx + half_top)))
    left_bottom = max(0, int(round(cx - half_bottom)))
    right_bottom = min(width - 1, int(round(cx + half_bottom)))

    polygon = np.array(
        [
            [left_top, top_y],
            [right_top, top_y],
            [right_bottom, bottom_y],
            [left_bottom, bottom_y],
        ],
        dtype=np.int32,
    )
    return {
        "polygon": polygon,
        "anchor_mode": anchor_mode,
        "anchor_confidence": round(clamp01(confidence), 3),
        "center_x": float(cx),
        "top_y": float(top_y),
        "bottom_y": float(bottom_y),
    }


def polygon_mask(shape: Tuple[int, int], polygon: np.ndarray) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon.astype(np.int32)], 255)
    return mask


def expand_polygon(polygon: np.ndarray, image_shape: Tuple[int, int, int]) -> np.ndarray:
    height, width = image_shape[:2]
    points = polygon.astype(np.float32)
    center = points.mean(axis=0)
    expanded = points.copy()
    expanded[:, 0] = center[0] + ((points[:, 0] - center[0]) * 1.18)
    expanded[:, 1] = center[1] + ((points[:, 1] - center[1]) * 1.10)
    expanded[:, 0] = np.clip(expanded[:, 0], 0, width - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, height - 1)
    return expanded.astype(np.int32)


def build_component_records(mask: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, float]]]:
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    components: List[Dict[str, float]] = []
    for label in range(1, num_labels):
        x, y, w, h, area = [int(stats[label, idx]) for idx in range(5)]
        components.append(
            {
                "label": float(label),
                "x": float(x),
                "y": float(y),
                "w": float(w),
                "h": float(h),
                "area": float(area),
                "cx": float(centroids[label][0]),
                "cy": float(centroids[label][1]),
            }
        )
    return labels, components


def component_label_for_anchor(
    labels: np.ndarray,
    components: Sequence[Dict[str, float]],
    anchor: Optional[Dict[str, float]],
) -> int:
    if anchor is None or labels.size == 0:
        return 0
    height, width = labels.shape[:2]
    cx = int(np.clip(round(anchor["cx"]), 0, width - 1))
    cy = int(np.clip(round(anchor["cy"]), 0, height - 1))
    direct_label = int(labels[cy, cx])
    if direct_label > 0:
        return direct_label

    x0 = int(max(0, math.floor(anchor["x"])))
    y0 = int(max(0, math.floor(anchor["y"])))
    x1 = int(min(width, math.ceil(anchor["x"] + anchor["w"])))
    y1 = int(min(height, math.ceil(anchor["y"] + anchor["h"])))
    if x1 > x0 and y1 > y0:
        crop = labels[y0:y1, x0:x1]
        values = crop[crop > 0]
        if values.size > 0:
            counts = np.bincount(values.astype(np.int32))
            return int(np.argmax(counts))

    best_label = 0
    best_distance = float("inf")
    for component in components:
        distance = math.hypot(component["cx"] - anchor["cx"], component["cy"] - anchor["cy"])
        if distance < best_distance:
            best_distance = distance
            best_label = int(component["label"])
    return best_label


def build_owned_canopy_mask(
    vegetation_mask: np.ndarray,
    primary_canopy: Optional[Dict[str, float]],
    pot_mask: np.ndarray,
    expanded_mask: np.ndarray,
) -> np.ndarray:
    labels, components = build_component_records(vegetation_mask)
    primary_label = component_label_for_anchor(labels, components, primary_canopy)
    if primary_label <= 0:
        return np.zeros_like(vegetation_mask)

    component_lookup = {int(component["label"]): component for component in components}
    primary_component = component_lookup.get(primary_label)
    if primary_component is None:
        return np.zeros_like(vegetation_mask)

    primary_mask = np.where(labels == primary_label, 255, 0).astype(np.uint8)
    distance_to_primary = cv2.distanceTransform((primary_mask == 0).astype(np.uint8), cv2.DIST_L2, 3)
    height, width = vegetation_mask.shape[:2]
    pot_binary = pot_mask > 0
    expanded_binary = expanded_mask > 0
    distance_threshold = max(
        18.0,
        min(height, width) * 0.05,
        math.sqrt(max(primary_component["area"], 1.0)) * 0.55,
    )

    owned_labels = {primary_label}
    for component in components:
        label = int(component["label"])
        if label == primary_label or component["area"] < 60.0:
            continue
        component_pixels = labels == label
        area = float(component["area"])
        overlap_pot = float(np.count_nonzero(component_pixels & pot_binary)) / area
        overlap_expanded = float(np.count_nonzero(component_pixels & expanded_binary)) / area
        if overlap_expanded <= 0.0:
            continue
        min_distance = float(distance_to_primary[component_pixels].min())
        horizontal_gap = abs(component["cx"] - primary_component["cx"])
        include = False
        if overlap_pot >= 0.55 and min_distance <= distance_threshold:
            include = True
        elif overlap_pot >= 0.70 and min_distance <= distance_threshold * 1.5:
            include = True
        elif (
            overlap_pot >= 0.35
            and horizontal_gap <= max(primary_component["w"] * 0.95, width * 0.10)
            and min_distance <= distance_threshold * 0.8
        ):
            include = True
        if include:
            owned_labels.add(label)

    return np.where(np.isin(labels, list(owned_labels)), 255, 0).astype(np.uint8)


def compute_chlorosis_ratio(image_bgr: np.ndarray, canopy_mask: np.ndarray) -> float:
    canopy_count = int(np.count_nonzero(canopy_mask))
    if canopy_count <= 0:
        return 0.0

    core_mask = cv2.erode(canopy_mask, np.ones((3, 3), np.uint8), iterations=1)
    if int(np.count_nonzero(core_mask)) < max(80, int(canopy_count * 0.25)):
        core_mask = canopy_mask

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    b, g, r = cv2.split(image_bgr.astype(np.float32))
    exg = (2.0 * g) - r - b

    valid = core_mask > 0
    exg_values = exg[valid]
    if exg_values.size == 0:
        return 0.0

    exg_threshold = float(np.percentile(exg_values, 35)) if exg_values.size >= 40 else 10.0
    warm_hue = (h >= 12) & (h <= 40) & (s >= 25) & (v >= 45)
    yellow_balance = (g >= (r * 0.78)) & (g <= (r * 1.22)) & (b <= (g * 0.92))
    bright_leaf = (g >= 55.0) & (r >= 50.0)
    chlorotic = valid & warm_hue & yellow_balance & bright_leaf & (exg <= exg_threshold)
    return float(np.count_nonzero(chlorotic)) / float(np.count_nonzero(valid))


def estimate_plant_count(
    canopy_components: int,
    coverage: float,
    largest_component_ratio: float,
) -> int:
    if canopy_components <= 0:
        return 0 if coverage < 0.01 else 1
    estimate = min(canopy_components, 4)
    if coverage < 0.015:
        estimate = min(estimate, 1)
    elif coverage < 0.03:
        estimate = min(estimate, 2)
    elif coverage < 0.06:
        estimate = min(estimate, 3)
    if largest_component_ratio > 0.09 and estimate > 1:
        estimate -= 1
    return max(1, min(estimate, canopy_components, 4))


def compute_pot_metrics(image_bgr: np.ndarray) -> Dict[str, object]:
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError("Expected a BGR image with shape HxWx3")

    height, width = image_bgr.shape[:2]
    vegetation_mask = compute_vegetation_mask(image_bgr)
    canopy_anchor = detect_primary_canopy(image_bgr, vegetation_mask)
    label_anchor = detect_label_anchor(image_bgr, canopy_anchor)
    pot_focus = infer_pot_polygon(image_bgr, canopy_anchor, label_anchor)
    pot_polygon = pot_focus["polygon"]
    pot_mask = polygon_mask((height, width), pot_polygon)
    expanded_polygon = expand_polygon(pot_polygon, image_bgr.shape)
    expanded_mask = polygon_mask((height, width), expanded_polygon)
    ring_mask = cv2.subtract(expanded_mask, pot_mask)
    owned_canopy_mask = build_owned_canopy_mask(
        vegetation_mask=vegetation_mask,
        primary_canopy=canopy_anchor,
        pot_mask=pot_mask,
        expanded_mask=expanded_mask,
    )
    in_pot_mask = cv2.bitwise_and(owned_canopy_mask, owned_canopy_mask, mask=pot_mask)
    owned_expanded_mask = cv2.bitwise_and(owned_canopy_mask, owned_canopy_mask, mask=expanded_mask)
    all_expanded_green_mask = cv2.bitwise_and(vegetation_mask, vegetation_mask, mask=expanded_mask)
    foreign_expanded_mask = cv2.subtract(all_expanded_green_mask, owned_expanded_mask)
    ring_green_mask = cv2.bitwise_and(foreign_expanded_mask, foreign_expanded_mask, mask=ring_mask)
    foreign_in_pot_mask = cv2.bitwise_and(foreign_expanded_mask, foreign_expanded_mask, mask=pot_mask)

    pot_area = float(np.count_nonzero(pot_mask))
    canopy_area = float(np.count_nonzero(in_pot_mask))
    ring_green_area = float(np.count_nonzero(ring_green_mask))
    foreign_in_pot_area = float(np.count_nonzero(foreign_in_pot_mask))
    owned_expanded_area = float(np.count_nonzero(owned_expanded_mask))
    foreign_expanded_area = float(np.count_nonzero(foreign_expanded_mask))
    pot_coverage = canopy_area / pot_area if pot_area > 0 else 0.0
    neighbor_spill_ratio = (
        foreign_expanded_area / (foreign_expanded_area + owned_expanded_area)
        if (foreign_expanded_area + owned_expanded_area) > 0
        else 0.0
    )

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(in_pot_mask, 8)
    min_component_area = max(120, int(pot_area * 0.003))
    valid_areas: List[int] = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_component_area:
            valid_areas.append(area)
    canopy_components = len(valid_areas)
    largest_component_ratio = (
        max(valid_areas) / pot_area if valid_areas and pot_area > 0 else 0.0
    )
    plant_count = estimate_plant_count(
        canopy_components=canopy_components,
        coverage=pot_coverage,
        largest_component_ratio=largest_component_ratio,
    )

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    chlorosis_ratio = compute_chlorosis_ratio(image_bgr, in_pot_mask)

    x0 = int(max(0, pot_polygon[:, 0].min()))
    x1 = int(min(width, pot_polygon[:, 0].max() + 1))
    y0 = int(max(0, pot_polygon[:, 1].min()))
    y1 = int(min(height, pot_polygon[:, 1].max() + 1))
    crop = image_bgr[y0:y1, x0:x1]
    crop_mask = pot_mask[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    v_crop = v[y0:y1, x0:x1]
    pot_pixels = v_crop[crop_mask > 0]
    brightness_mean = float(pot_pixels.mean()) if pot_pixels.size > 0 else float(v_crop.mean())

    polygon_center_x = float(pot_polygon[:, 0].mean())
    polygon_center_y = float(pot_polygon[:, 1].mean())
    if canopy_anchor is not None:
        distance = math.hypot(canopy_anchor["cx"] - polygon_center_x, canopy_anchor["cy"] - polygon_center_y)
        center_offset_ratio = distance / max(width * 0.25, 1.0)
    else:
        center_offset_ratio = 1.0

    label_confidence = float(label_anchor["confidence"]) if label_anchor is not None else 0.0
    anchor_confidence = float(pot_focus["anchor_confidence"])
    focus_score = clamp01(
        (0.50 * (1.0 - neighbor_spill_ratio))
        + (0.35 * anchor_confidence)
        + (0.10 * (1.0 - min(center_offset_ratio, 1.0)))
        + (0.05 if pot_focus["anchor_mode"] == "plant" else 0.0)
    )

    return {
        "anchor_mode": str(pot_focus["anchor_mode"]),
        "anchor_confidence": round(anchor_confidence, 3),
        "label_confidence": round(label_confidence, 3),
        "focus_score": round(focus_score, 3),
        "center_offset_ratio": round(center_offset_ratio, 3),
        "pot_coverage": round(float(pot_coverage), 6),
        "neighbor_spill_ratio": round(float(neighbor_spill_ratio), 6),
        "spill_in_pot_ratio": round(
            (foreign_in_pot_area / (foreign_in_pot_area + canopy_area))
            if (foreign_in_pot_area + canopy_area) > 0
            else 0.0,
            6,
        ),
        "plant_count_estimate": int(plant_count),
        "canopy_components": int(canopy_components),
        "largest_component_ratio": round(float(largest_component_ratio), 6),
        "chlorosis_ratio": round(float(chlorosis_ratio), 6),
        "blur_score": round(float(blur_score), 3),
        "brightness_mean": round(float(brightness_mean), 3),
        "pot_polygon": pot_polygon,
        "expanded_polygon": expanded_polygon,
        "pot_bbox": (x0, y0, x1, y1),
        "canopy_anchor": canopy_anchor,
        "label_anchor": label_anchor,
        "vegetation_mask": vegetation_mask,
        "owned_canopy_mask": owned_canopy_mask,
        "pot_mask": pot_mask,
        "crop_image": crop,
    }


def compute_growth_delta(
    latest_coverage: float,
    baseline_coverage: Optional[float],
) -> Optional[float]:
    if baseline_coverage is None or baseline_coverage <= 0.0:
        return None
    return (latest_coverage - baseline_coverage) / baseline_coverage


def score_health(metrics: Dict[str, object], growth_delta: Optional[float]) -> float:
    coverage_norm = min(float(metrics["pot_coverage"]) / 0.08, 1.0)
    growth_norm = 0.55 if growth_delta is None else clamp01((growth_delta + 0.30) / 1.10)
    chlorosis_confidence = clamp01(
        (float(metrics["focus_score"]) * 0.70)
        + ((1.0 - float(metrics["neighbor_spill_ratio"])) * 0.30)
    )
    effective_chlorosis = float(metrics["chlorosis_ratio"]) * chlorosis_confidence
    chlorosis_norm = 1.0 - min(effective_chlorosis / 0.28, 1.0)
    spill_signal = (
        (0.70 * float(metrics["spill_in_pot_ratio"]))
        + (0.30 * float(metrics["neighbor_spill_ratio"]))
    )
    spill_norm = 1.0 - min(spill_signal / 0.50, 1.0)
    focus_norm = float(metrics["focus_score"])
    count_norm = max(0.0, 1.0 - (abs(float(metrics["plant_count_estimate"]) - 1.8) / 3.0))

    score = (
        (32.0 * coverage_norm)
        + (18.0 * growth_norm)
        + (15.0 * chlorosis_norm)
        + (15.0 * spill_norm)
        + (12.0 * focus_norm)
        + (8.0 * count_norm)
    )
    return round(clamp01(score / 100.0) * 100.0, 2)


def derive_tracking_readiness(metrics: Dict[str, object], growth_delta: Optional[float]) -> str:
    focus_score = float(metrics["focus_score"])
    spill = float(metrics["spill_in_pot_ratio"])
    coverage = float(metrics["pot_coverage"])
    if focus_score >= 0.70 and spill <= 0.16 and coverage >= 0.012:
        return "high"
    if focus_score >= 0.46 and spill <= 0.38 and coverage >= 0.006:
        return "moderate"
    if growth_delta is not None and focus_score >= 0.36:
        return "moderate"
    return "low"


def derive_next_step(
    metrics: Dict[str, object],
    growth_delta: Optional[float],
) -> Tuple[str, str]:
    if metrics["anchor_mode"] == "fallback" or float(metrics["focus_score"]) < 0.35:
        return (
            "capture_tighter_frame",
            "Capture this pot more centrally and closer so the target pot is easier to isolate from neighbors.",
        )
    if (
        float(metrics["spill_in_pot_ratio"]) > 0.32
        or (
            float(metrics["neighbor_spill_ratio"]) > 0.60
            and float(metrics["focus_score"]) < 0.55
        )
    ):
        return (
            "needs_neighbor_disambiguation",
            "Foreign foliage is still entering the target crop or crowding it too closely; this pot is a good candidate for custom pot-mask labeling.",
        )
    if float(metrics["pot_coverage"]) < 0.012:
        return (
            "wait_for_more_leaf_area",
            "Plant signal is still sparse; revisit after more leaf growth to improve segmentation reliability.",
        )
    if (
        float(metrics["chlorosis_ratio"]) >= 0.22
        and float(metrics["focus_score"]) >= 0.62
        and float(metrics["spill_in_pot_ratio"]) <= 0.18
        and float(metrics["pot_coverage"]) >= 0.02
    ):
        return (
            "inspect_leaf_health",
            "Yellowing persists inside a relatively clean canopy crop; add close-up health photos before trusting growth trends.",
        )
    if int(metrics["plant_count_estimate"]) >= 3 and float(metrics["pot_coverage"]) > 0.040:
        return (
            "prepare_thinning_count",
            "Multiple seedling clumps are visible; this is a strong candidate for count-based thinning and growth tracking.",
        )
    if growth_delta is not None and growth_delta < -0.18:
        return (
            "review_growth_drop",
            "Coverage dropped versus the baseline frame; verify framing consistency and inspect this pot in the next capture.",
        )
    return (
        "ready_for_mask_labels",
        "Frame quality and pot isolation look good enough to start custom pot/plant mask labeling for indoor tracking.",
    )


def derive_data_quality_flag(metrics: Dict[str, object]) -> str:
    flags: List[str] = []
    if metrics["anchor_mode"] == "fallback":
        flags.append("fallback_anchor")
    if float(metrics["blur_score"]) < 45:
        flags.append("blur_low")
    if float(metrics["brightness_mean"]) < 40:
        flags.append("underexposed")
    if float(metrics["brightness_mean"]) > 225:
        flags.append("overexposed")
    if float(metrics["spill_in_pot_ratio"]) > 0.32:
        flags.append("neighbor_spill")
    if float(metrics["pot_coverage"]) < 0.01:
        flags.append("low_signal")
    return "|".join(flags) if flags else "ok"


def assess_algorithm_status(availability_ratio: float, variation_coeff: float) -> str:
    if availability_ratio >= 0.85 and variation_coeff >= 0.12:
        return "helpful"
    if availability_ratio >= 0.50:
        return "promising_with_more_data"
    return "limited_current_data"


def build_algorithm_assessments(row_results: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
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
        values = [value for value in metric_values(metric_key) if value_filter(value)]
        availability_ratio = len(values) / total
        variation_coeff = coefficient_of_variation(values)
        return {
            "algorithm_key": algorithm_key,
            "metric_key": metric_key,
            "status": assess_algorithm_status(availability_ratio, variation_coeff),
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
        if growth_availability >= 0.60 and growth_variation >= 0.15
        else "promising_with_more_data"
        if growth_availability >= 0.20
        else "limited_current_data"
    )

    return [
        build(
            algorithm_key="primary_canopy_anchor",
            metric_key="anchor_confidence",
            summary_note="Choose the dominant, center-biased green component as the likely target plant anchor.",
            helpful_note=(
                "Provides a stable starting point for indoor pot localization when multiple neighboring pots are visible."
            ),
            value_filter=lambda value: value > 0.0,
        ),
        build(
            algorithm_key="label_box_detection",
            metric_key="label_confidence",
            summary_note="Detect bright vertical label rectangles near the main canopy to support pot alignment.",
            helpful_note=(
                "Adds a second cue for indoor pot identity and helps diagnose cases where plant-only anchoring is ambiguous."
            ),
            value_filter=lambda value: value > 0.0,
        ),
        build(
            algorithm_key="pot_polygon_focus_crop",
            metric_key="focus_score",
            summary_note="Infer a pot-shaped trapezoid and score how isolated the target canopy is from neighboring spillover.",
            helpful_note=(
                "Turns multi-pot frames into a reproducible per-pot region so growth metrics are less contaminated by adjacent seedlings."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        build(
            algorithm_key="in_pot_vegetation_segmentation",
            metric_key="pot_coverage",
            summary_note="Measure canopy coverage only inside the inferred pot footprint.",
            helpful_note=(
                "Closer to the real indoor use case than whole-image vegetation coverage because it suppresses nearby-pot noise."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        build(
            algorithm_key="neighbor_spillover_estimation",
            metric_key="neighbor_spill_ratio",
            summary_note="Estimate how much green signal appears immediately outside the target pot region.",
            helpful_note=(
                "Flags frames that still need custom masking or tighter capture before they are trustworthy for longitudinal tracking."
            ),
            value_filter=lambda value: value >= 0.0,
        ),
        {
            "algorithm_key": "temporal_growth_delta",
            "metric_key": "growth_delta",
            "status": growth_status,
            "availability_ratio": round(growth_availability, 3),
            "variation_coeff": round(growth_variation, 3),
            "signal_summary": "Change in in-pot canopy coverage versus the earliest baseline image for the same pot.",
            "why_helpful": (
                "Gives a directional growth signal for pots that already have a baseline capture, even before a learned detector exists."
            ),
        },
    ]


def readiness_priority(value: object) -> int:
    cleaned = str(value or "").strip().lower()
    if cleaned == "high":
        return 0
    if cleaned == "moderate":
        return 1
    if cleaned == "low":
        return 2
    return 3


def build_mask_label_queue(row_results: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    ready_rows = [
        row
        for row in row_results
        if str(row.get("next_step_code", "") or "").strip() == "ready_for_mask_labels"
    ]
    sorted_rows = sorted(
        ready_rows,
        key=lambda row: (
            readiness_priority(row.get("tracking_readiness")),
            -(safe_float(row.get("focus_score")) or 0.0),
            (
                safe_float(row.get("spill_in_pot_ratio"))
                if safe_float(row.get("spill_in_pot_ratio")) is not None
                else safe_float(row.get("neighbor_spill_ratio")) or 1.0
            ),
            -(safe_float(row.get("pot_coverage")) or 0.0),
            pot_number_from_id(str(row.get("pot_id", "") or "")),
            str(row.get("pot_id", "") or ""),
        ),
    )

    queue_rows: List[Dict[str, object]] = []
    for index, row in enumerate(sorted_rows, start=1):
        focus_score = safe_float(row.get("focus_score")) or 0.0
        pot_coverage = safe_float(row.get("pot_coverage")) or 0.0
        spill_in_pot = safe_float(row.get("spill_in_pot_ratio"))
        neighbor_spill = safe_float(row.get("neighbor_spill_ratio")) or 0.0
        if spill_in_pot is None:
            spill_in_pot = neighbor_spill
        chlorosis_ratio = safe_float(row.get("chlorosis_ratio")) or 0.0
        growth_delta = safe_float(row.get("growth_delta"))
        readiness = str(row.get("tracking_readiness", "") or "").strip()

        if readiness == "high" and spill_in_pot <= 0.12:
            labeling_note = "Best starter mask candidate: high readiness with low in-pot spill."
        elif growth_delta is not None:
            labeling_note = "Label this pot to unlock a cleaner longitudinal growth baseline."
        else:
            labeling_note = "Usable for mask labeling, but confirm pot edges against nearby foliage."

        queue_rows.append(
            {
                "priority_rank": index,
                "pot_id": row.get("pot_id", ""),
                "variety_name": row.get("variety_name", ""),
                "tracking_readiness": readiness,
                "focus_score": round(focus_score, 6),
                "pot_coverage": round(pot_coverage, 6),
                "spill_in_pot_ratio": round(spill_in_pot, 6),
                "neighbor_spill_ratio": round(neighbor_spill, 6),
                "chlorosis_ratio": round(chlorosis_ratio, 6),
                "growth_delta": "" if growth_delta is None else round(growth_delta, 6),
                "capture_date": row.get("capture_date", ""),
                "source_asset_id": row.get("source_asset_id", ""),
                "photo_url": row.get("photo_url", ""),
                "overlay_path": row.get("overlay_path", ""),
                "crop_path": row.get("crop_path", ""),
                "labeling_note": labeling_note,
            }
        )
    return queue_rows


def write_visual_assets(
    assets_dir: Path,
    row: Dict[str, str],
    image_bgr: np.ndarray,
    metrics: Dict[str, object],
) -> Tuple[str, str]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    pot_id = normalize_pot_id(row.get("pot_id", "") or "") or "unknown"
    asset_id = (row.get("source_asset_id", "") or "asset")[:16]
    slug = f"{pot_id.lower()}_{asset_id.lower()}"

    overlay_path = assets_dir / f"{slug}_overlay.jpg"
    crop_path = assets_dir / f"{slug}_crop.jpg"

    overlay = image_bgr.copy()
    vegetation_mask = metrics["vegetation_mask"]
    owned_canopy_mask = metrics["owned_canopy_mask"]
    pot_mask = metrics["pot_mask"]
    owned_in_pot_mask = cv2.bitwise_and(owned_canopy_mask, owned_canopy_mask, mask=pot_mask)
    foreign_in_pot_mask = cv2.subtract(
        cv2.bitwise_and(vegetation_mask, vegetation_mask, mask=pot_mask),
        owned_in_pot_mask,
    )
    green_overlay = np.zeros_like(overlay)
    green_overlay[:, :, 1] = 255
    amber_overlay = np.zeros_like(overlay)
    amber_overlay[:, :, 1] = 180
    amber_overlay[:, :, 2] = 255
    overlay = np.where(
        (owned_in_pot_mask > 0)[:, :, None],
        cv2.addWeighted(overlay, 0.65, green_overlay, 0.35, 0.0),
        overlay,
    )
    overlay = np.where(
        (foreign_in_pot_mask > 0)[:, :, None],
        cv2.addWeighted(overlay, 0.70, amber_overlay, 0.30, 0.0),
        overlay,
    )

    pot_polygon = metrics["pot_polygon"].astype(np.int32)
    cv2.polylines(overlay, [pot_polygon], True, (255, 80, 30), 10)
    if metrics.get("canopy_anchor") is not None:
        canopy = metrics["canopy_anchor"]
        x = int(canopy["x"])
        y = int(canopy["y"])
        w = int(canopy["w"])
        h = int(canopy["h"])
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (40, 220, 80), 8)
    if metrics.get("label_anchor") is not None:
        label = metrics["label_anchor"]
        x = int(label["x"])
        y = int(label["y"])
        w = int(label["w"])
        h = int(label["h"])
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (20, 180, 255), 6)

    title = (
        f"{pot_id} | {metrics['anchor_mode']} | "
        f"focus {float(metrics['focus_score']):.2f} | spill {float(metrics['neighbor_spill_ratio']) * 100:.0f}%"
    )
    cv2.rectangle(overlay, (0, 0), (overlay.shape[1], 120), (18, 28, 34), thickness=-1)
    cv2.putText(overlay, title, (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (244, 244, 236), 3)

    x0, y0, x1, y1 = metrics["pot_bbox"]
    pad = 24
    crop_x0 = max(0, x0 - pad)
    crop_y0 = max(0, y0 - pad)
    crop_x1 = min(image_bgr.shape[1], x1 + pad)
    crop_y1 = min(image_bgr.shape[0], y1 + pad)
    crop = overlay[crop_y0:crop_y1, crop_x0:crop_x1]

    cv2.imwrite(str(overlay_path), overlay)
    cv2.imwrite(str(crop_path), crop)
    return (
        f"assets/v1-10-pot-cv/{overlay_path.name}",
        f"assets/v1-10-pot-cv/{crop_path.name}",
    )


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
            assets_dir TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            analyzed_rows INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pot_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            pot_id TEXT NOT NULL,
            pot_number INTEGER NOT NULL,
            variety_name TEXT,
            capture_date TEXT NOT NULL,
            source_asset_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            overlay_path TEXT NOT NULL,
            crop_path TEXT NOT NULL,
            baseline_source_asset_id TEXT,
            baseline_capture_date TEXT,
            anchor_mode TEXT NOT NULL,
            anchor_confidence REAL NOT NULL,
            label_confidence REAL NOT NULL,
            focus_score REAL NOT NULL,
            center_offset_ratio REAL NOT NULL,
            pot_coverage REAL NOT NULL,
            neighbor_spill_ratio REAL NOT NULL,
            plant_count_estimate INTEGER NOT NULL,
            canopy_components INTEGER NOT NULL,
            chlorosis_ratio REAL NOT NULL,
            growth_delta REAL,
            health_score REAL NOT NULL,
            tracking_readiness TEXT NOT NULL,
            next_step_code TEXT NOT NULL,
            next_step_text TEXT NOT NULL,
            data_quality_flag TEXT NOT NULL,
            blur_score REAL NOT NULL,
            brightness_mean REAL NOT NULL,
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
    assets_dir: Path,
    row_results: Sequence[Dict[str, object]],
    algorithm_assessments: Sequence[Dict[str, object]],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    created_at = iso_now()
    with sqlite3.connect(db_path) as conn:
        ensure_db_schema(conn)
        conn.execute("DELETE FROM pot_metrics WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM algorithm_assessments WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM experiment_runs WHERE run_id = ?", (run_id,))
        conn.execute(
            """
            INSERT INTO experiment_runs (
                run_id, run_date, mapping_csv, labeled_csv, images_dir, output_dir, assets_dir,
                total_rows, analyzed_rows, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_date,
                str(mapping_csv),
                str(labeled_csv),
                str(images_dir),
                str(output_dir),
                str(assets_dir),
                len(row_results),
                len(row_results),
                created_at,
            ),
        )
        for row in row_results:
            conn.execute(
                """
                INSERT INTO pot_metrics (
                    run_id, pot_id, pot_number, variety_name, capture_date, source_asset_id,
                    image_path, overlay_path, crop_path, baseline_source_asset_id, baseline_capture_date,
                    anchor_mode, anchor_confidence, label_confidence, focus_score, center_offset_ratio,
                    pot_coverage, neighbor_spill_ratio, plant_count_estimate, canopy_components,
                    chlorosis_ratio, growth_delta, health_score, tracking_readiness, next_step_code,
                    next_step_text, data_quality_flag, blur_score, brightness_mean, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["pot_id"],
                    int(row["pot_number"]),
                    row.get("variety_name", ""),
                    row["capture_date"],
                    row["source_asset_id"],
                    row["image_path"],
                    row["overlay_path"],
                    row["crop_path"],
                    row.get("baseline_source_asset_id", ""),
                    row.get("baseline_capture_date", ""),
                    row["anchor_mode"],
                    float(row["anchor_confidence"]),
                    float(row["label_confidence"]),
                    float(row["focus_score"]),
                    float(row["center_offset_ratio"]),
                    float(row["pot_coverage"]),
                    float(row["neighbor_spill_ratio"]),
                    int(row["plant_count_estimate"]),
                    int(row["canopy_components"]),
                    float(row["chlorosis_ratio"]),
                    safe_float(row.get("growth_delta")),
                    float(row["health_score"]),
                    row["tracking_readiness"],
                    row["next_step_code"],
                    row["next_step_text"],
                    row["data_quality_flag"],
                    float(row["blur_score"]),
                    float(row["brightness_mean"]),
                    created_at,
                ),
            )
        for row in algorithm_assessments:
            conn.execute(
                """
                INSERT INTO algorithm_assessments (
                    run_id, algorithm_key, metric_key, status, availability_ratio,
                    variation_coeff, signal_summary, why_helpful, created_at
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
                    created_at,
                ),
            )
        conn.commit()


def write_markdown_report(
    report_path: Path,
    row_results: Sequence[Dict[str, object]],
    algorithm_assessments: Sequence[Dict[str, object]],
    summary: Dict[str, object],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    next_step_counts = summary.get("next_step_counts", {})
    readiness_counts = summary.get("tracking_readiness_counts", {})
    top_next = ""
    if isinstance(next_step_counts, dict) and next_step_counts:
        top_next = sorted(next_step_counts.items(), key=lambda item: (-int(item[1]), item[0]))[0][0]

    lines = [
        "# V1.10 Pot-Anchored CV Experiment",
        "",
        f"Generated at: {summary.get('created_at', iso_now())}",
        f"Run ID: `{summary.get('run_id', '')}`",
        f"Run date (photo set): `{summary.get('run_date', '')}`",
        "",
        "## Scope",
        "",
        "- Focus: indoor tomato-pot images where multiple neighboring pots are visible in the same frame.",
        "- Goal: estimate target-pot coverage and growth with less contamination from adjacent pots.",
        "- Inputs:",
        f"  - mapping CSV: `{summary.get('mapping_csv', '')}`",
        f"  - baseline CSV: `{summary.get('labeled_csv', '')}`",
        f"  - image cache: `{summary.get('images_dir', '')}`",
        "",
        "## High-Level Findings",
        "",
        f"- Pots analyzed: `{summary.get('pots_analyzed', 0)}`",
        f"- Average focus score: `{summary.get('average_focus_score', 0.0):.3f}`",
        f"- Average in-pot coverage: `{summary.get('average_pot_coverage', 0.0) * 100:.1f}%`",
        f"- Average in-pot spill: `{summary.get('average_spill_in_pot_ratio', 0.0) * 100:.1f}%`",
        f"- Average neighbor spill: `{summary.get('average_neighbor_spill_ratio', 0.0) * 100:.1f}%`",
        f"- Growth delta availability: `{summary.get('growth_delta_availability_ratio', 0.0) * 100:.1f}%`",
        f"- Ready-for-mask-labels pots: `{summary.get('ready_for_mask_labels_count', 0)}`",
        f"- Mask-label queue rows: `{summary.get('mask_label_queue_count', 0)}`",
        f"- Most common next step: `{top_next or 'n/a'}`",
        "",
        "## Tracking Readiness",
        "",
        f"- high={int(readiness_counts.get('high', 0) if isinstance(readiness_counts, dict) else 0)}",
        f"- moderate={int(readiness_counts.get('moderate', 0) if isinstance(readiness_counts, dict) else 0)}",
        f"- low={int(readiness_counts.get('low', 0) if isinstance(readiness_counts, dict) else 0)}",
        "",
        "## Algorithm Assessment",
        "",
        "| Algorithm | Status | Availability | Variation | Why it matters |",
        "|---|---:|---:|---:|---|",
    ]
    for row in algorithm_assessments:
        lines.append(
            f"| `{row['algorithm_key']}` | {row['status']} | {float(row['availability_ratio']) * 100:.1f}% | "
            f"{float(row['variation_coeff']):.3f} | {row['why_helpful']} |"
        )

    lines.extend(
        [
            "",
            "## Pot-Level Output",
            "",
            "| Pot | Variety | Anchor | Focus | Coverage | Spill | Growth | Readiness | Next step |",
            "|---|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in row_results:
        growth = safe_float(row.get("growth_delta"))
        growth_text = "n/a" if growth is None else f"{growth * 100:.1f}%"
        lines.append(
            f"| {row['pot_id']} | {row.get('variety_name', '')} | {row['anchor_mode']} | "
            f"{float(row['focus_score']):.2f} | {float(row['pot_coverage']) * 100:.1f}% | "
            f"{float(row.get('spill_in_pot_ratio', row['neighbor_spill_ratio'])) * 100:.1f}% | {growth_text} | "
            f"{row['tracking_readiness']} | {row['next_step_code']} |"
        )

    lines.extend(
        [
            "",
            "## Recommended Next Research Iterations",
            "",
            "1. Label masks for the highest-focus indoor pots first to create a custom pot detector training set.",
            "2. Tighten the capture contract so each pot is more centered and includes less neighboring foliage.",
            "3. Add close-up leaf captures for pots with elevated chlorosis to separate disease/stress from framing noise.",
            "4. Re-run the same pot-anchored metrics after the outdoor move to measure how spillover worsens in more complex backgrounds.",
            "",
            "## Output Artifacts",
            "",
            f"- `{summary.get('output_dir', '')}/pot_cv_metrics.csv`",
            f"- `{summary.get('output_dir', '')}/pot_cv_recommendations.csv`",
            f"- `{summary.get('mask_label_queue_path', '')}`",
            f"- `{summary.get('mask_label_seed_set_path', '')}`",
            f"- `{summary.get('output_dir', '')}/algorithm_assessment.csv`",
            f"- `{summary.get('output_dir', '')}/pot_cv_summary.json`",
            f"- `{summary.get('assets_dir', '')}/`",
            f"- `{summary.get('tracker_page', '')}`",
            f"- `{summary.get('mask_label_seed_page', '')}`",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    *,
    mapping_csv: Path,
    labeled_csv: Path,
    images_dir: Path,
    db_path: Path,
    output_dir: Path,
    assets_dir: Path,
    report_path: Path,
    run_id: str,
) -> Dict[str, object]:
    mapping_rows = read_csv_rows(mapping_csv)
    labeled_rows = read_csv_rows(labeled_csv)
    latest_rows = select_latest_rows(mapping_rows)
    image_lookup = build_image_lookup(images_dir)
    baseline_lookup = build_baseline_lookup(labeled_rows)

    row_results: List[Dict[str, object]] = []
    baseline_coverages: Dict[str, float] = {}
    output_dir.mkdir(parents=True, exist_ok=True)

    for row in latest_rows:
        pot_id = normalize_pot_id(row.get("pot_id", "") or "")
        if not pot_id:
            continue
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        image_path = image_lookup.get(source_asset_id)
        if image_path is None:
            continue
        image = parse_image(image_path)
        metrics = compute_pot_metrics(image)

        pot_number = pot_number_from_id(pot_id)
        baseline_entry = baseline_lookup.get(pot_number)
        baseline_source_asset_id = ""
        baseline_capture_date = ""
        baseline_coverage: Optional[float] = None
        if baseline_entry is not None:
            baseline_source_asset_id = baseline_entry.source_asset_id
            baseline_capture_date = baseline_entry.capture_date
            cached_baseline = baseline_coverages.get(baseline_source_asset_id)
            if cached_baseline is None:
                baseline_path = image_lookup.get(baseline_source_asset_id)
                if baseline_path is not None:
                    baseline_image = parse_image(baseline_path)
                    baseline_metrics = compute_pot_metrics(baseline_image)
                    cached_baseline = float(baseline_metrics["pot_coverage"])
                    baseline_coverages[baseline_source_asset_id] = cached_baseline
            baseline_coverage = cached_baseline

        growth_delta = compute_growth_delta(float(metrics["pot_coverage"]), baseline_coverage)
        health_score = score_health(metrics, growth_delta)
        tracking_readiness = derive_tracking_readiness(metrics, growth_delta)
        next_step_code, next_step_text = derive_next_step(metrics, growth_delta)
        data_quality_flag = derive_data_quality_flag(metrics)
        overlay_path, crop_path = write_visual_assets(assets_dir, row, image, metrics)

        row_results.append(
            {
                "pot_id": pot_id,
                "pot_number": pot_number,
                "variety_name": (row.get("variety_name", "") or "").strip(),
                "capture_date": (row.get("capture_date", "") or "").strip(),
                "source_asset_id": source_asset_id,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "image_path": str(image_path),
                "overlay_path": overlay_path,
                "crop_path": crop_path,
                "baseline_source_asset_id": baseline_source_asset_id,
                "baseline_capture_date": baseline_capture_date,
                "anchor_mode": metrics["anchor_mode"],
                "anchor_confidence": metrics["anchor_confidence"],
                "label_confidence": metrics["label_confidence"],
                "focus_score": metrics["focus_score"],
                "center_offset_ratio": metrics["center_offset_ratio"],
                "pot_coverage": metrics["pot_coverage"],
                "neighbor_spill_ratio": metrics["neighbor_spill_ratio"],
                "spill_in_pot_ratio": metrics["spill_in_pot_ratio"],
                "plant_count_estimate": metrics["plant_count_estimate"],
                "canopy_components": metrics["canopy_components"],
                "chlorosis_ratio": metrics["chlorosis_ratio"],
                "growth_delta": "" if growth_delta is None else round(float(growth_delta), 6),
                "health_score": health_score,
                "tracking_readiness": tracking_readiness,
                "next_step_code": next_step_code,
                "next_step_text": next_step_text,
                "data_quality_flag": data_quality_flag,
                "blur_score": metrics["blur_score"],
                "brightness_mean": metrics["brightness_mean"],
            }
    )

    algorithm_assessments = build_algorithm_assessments(row_results)
    mask_label_queue = build_mask_label_queue(row_results)
    metrics_fields = [
        "pot_id",
        "pot_number",
        "variety_name",
        "capture_date",
        "source_asset_id",
        "photo_url",
        "image_path",
        "overlay_path",
        "crop_path",
        "baseline_source_asset_id",
        "baseline_capture_date",
        "anchor_mode",
        "anchor_confidence",
        "label_confidence",
        "focus_score",
        "center_offset_ratio",
        "pot_coverage",
        "neighbor_spill_ratio",
        "spill_in_pot_ratio",
        "plant_count_estimate",
        "canopy_components",
        "chlorosis_ratio",
        "growth_delta",
        "health_score",
        "tracking_readiness",
        "next_step_code",
        "next_step_text",
        "data_quality_flag",
        "blur_score",
        "brightness_mean",
    ]
    recommendation_fields = [
        "pot_id",
        "variety_name",
        "tracking_readiness",
        "next_step_code",
        "next_step_text",
        "focus_score",
        "pot_coverage",
        "neighbor_spill_ratio",
        "spill_in_pot_ratio",
    ]
    queue_fields = [
        "priority_rank",
        "pot_id",
        "variety_name",
        "tracking_readiness",
        "focus_score",
        "pot_coverage",
        "spill_in_pot_ratio",
        "neighbor_spill_ratio",
        "chlorosis_ratio",
        "growth_delta",
        "capture_date",
        "source_asset_id",
        "photo_url",
        "overlay_path",
        "crop_path",
        "labeling_note",
    ]
    algorithm_fields = [
        "algorithm_key",
        "metric_key",
        "status",
        "availability_ratio",
        "variation_coeff",
        "signal_summary",
        "why_helpful",
    ]

    write_csv_rows(output_dir / "pot_cv_metrics.csv", metrics_fields, row_results)
    write_csv_rows(output_dir / "pot_cv_recommendations.csv", recommendation_fields, row_results)
    write_csv_rows(output_dir / "mask_label_queue.csv", queue_fields, mask_label_queue)
    write_csv_rows(output_dir / "algorithm_assessment.csv", algorithm_fields, algorithm_assessments)

    next_step_counts = Counter(str(row.get("next_step_code", "") or "").strip() for row in row_results)
    readiness_counts = Counter(str(row.get("tracking_readiness", "") or "").strip() for row in row_results)
    growth_values = [safe_float(row.get("growth_delta")) for row in row_results]
    growth_available = [value for value in growth_values if value is not None]
    summary = {
        "run_id": run_id,
        "run_date": row_results[0]["capture_date"] if row_results else "",
        "created_at": iso_now(),
        "mapping_csv": str(mapping_csv),
        "labeled_csv": str(labeled_csv),
        "images_dir": str(images_dir),
        "output_dir": str(output_dir),
        "assets_dir": str(assets_dir),
        "tracker_page": "tracker/v1-10-pot-cv-research.html",
        "mask_label_seed_set_path": str(output_dir / "mask_label_seed_set.csv"),
        "mask_label_seed_page": "tracker/v1-10-mask-label-seed.html",
        "pots_analyzed": len(row_results),
        "average_focus_score": round(
            float(np.mean([float(row["focus_score"]) for row in row_results])) if row_results else 0.0,
            3,
        ),
        "average_pot_coverage": round(
            float(np.mean([float(row["pot_coverage"]) for row in row_results])) if row_results else 0.0,
            6,
        ),
        "average_spill_in_pot_ratio": round(
            float(np.mean([float(row["spill_in_pot_ratio"]) for row in row_results])) if row_results else 0.0,
            6,
        ),
        "average_neighbor_spill_ratio": round(
            float(np.mean([float(row["neighbor_spill_ratio"]) for row in row_results])) if row_results else 0.0,
            6,
        ),
        "growth_delta_availability_ratio": round(
            (len(growth_available) / float(len(row_results))) if row_results else 0.0,
            3,
        ),
        "ready_for_mask_labels_count": int(next_step_counts.get("ready_for_mask_labels", 0)),
        "mask_label_queue_count": len(mask_label_queue),
        "mask_label_queue_path": str(output_dir / "mask_label_queue.csv"),
        "tracking_readiness_counts": dict(readiness_counts),
        "next_step_counts": dict(next_step_counts),
    }
    write_summary_json(output_dir / "pot_cv_summary.json", summary)

    persist_results(
        db_path=db_path,
        run_id=run_id,
        run_date=summary["run_date"],
        mapping_csv=mapping_csv,
        labeled_csv=labeled_csv,
        images_dir=images_dir,
        output_dir=output_dir,
        assets_dir=assets_dir,
        row_results=row_results,
        algorithm_assessments=algorithm_assessments,
    )
    write_markdown_report(report_path, row_results, algorithm_assessments, summary)

    return {
        "run_id": run_id,
        "pots_analyzed": len(row_results),
        "output_dir": str(output_dir),
        "summary_path": str(output_dir / "pot_cv_summary.json"),
        "mask_label_queue_path": str(output_dir / "mask_label_queue.csv"),
        "mask_label_seed_set_path": str(output_dir / "mask_label_seed_set.csv"),
        "mask_label_seed_page": "tracker/v1-10-mask-label-seed.html",
        "report_path": str(report_path),
        "db_path": str(db_path),
        "assets_dir": str(assets_dir),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="CSV containing the latest tomato pot mapping rows.",
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Baseline labeled CSV used to find earliest tomato reference photos.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory containing downloaded JPGs keyed by source asset id.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("local/cv_research/v1_10_pot_cv.db"),
        help="SQLite path for isolated research outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/v1_10"),
        help="Directory for CSV/JSON artifacts.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("tracker/assets/v1-10-pot-cv"),
        help="Directory for generated tracker image assets.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("docs/V1.10-POT-CV-EXPERIMENT.md"),
        help="Markdown summary document path.",
    )
    parser.add_argument(
        "--run-id",
        default=f"v1_10_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        help="Optional stable run identifier.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_pipeline(
        mapping_csv=args.mapping_csv,
        labeled_csv=args.labeled_csv,
        images_dir=args.images_dir,
        db_path=args.db_path,
        output_dir=args.output_dir,
        assets_dir=args.assets_dir,
        report_path=args.report_path,
        run_id=args.run_id,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
