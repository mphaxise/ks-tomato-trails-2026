#!/usr/bin/env python3
"""Pair pot and varietal labels from a quick seed annotation JSON."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from v18_strategy_from_quick_seed import classify_description


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def parse_int(text: str) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def normalize_pot_id(raw: str) -> str:
    text = (raw or "").strip().upper()
    if not text:
        return ""
    if text.endswith("T"):
        number = parse_int(text[:-1])
        if number > 0:
            return f"{number}T"
    return ""


def load_series_map(path: Path) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    if not path.exists():
        return mapping
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            series_number = parse_int((row.get("series_number", "") or "").strip())
            variety_name = (row.get("variety_name", "") or "").strip()
            if series_number > 0 and variety_name:
                mapping[series_number] = variety_name
    return mapping


def load_pot_series_overrides(path: Path) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    if not path.exists():
        return mapping
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
            series_number = parse_int((row.get("series_number", "") or "").strip())
            if pot_id and series_number > 0:
                mapping[pot_id] = series_number
    return mapping


def load_baseline_pot_series(path: Path) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    if not path.exists():
        return mapping
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
            series_number = parse_int((row.get("packet_number", "") or "").strip())
            if pot_id and series_number > 0 and pot_id not in mapping:
                mapping[pot_id] = series_number
    return mapping


def load_pot_series_map(overrides_csv: Path, baseline_csv: Path) -> Dict[str, int]:
    baseline = load_baseline_pot_series(baseline_csv)
    overrides = load_pot_series_overrides(overrides_csv)
    merged = dict(baseline)
    merged.update(overrides)
    return merged


def to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def extract_typed_boxes(seed: Dict[str, object]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    raw_boxes = seed.get("boxes", [])
    if not isinstance(raw_boxes, list):
        raw_boxes = []

    pot_boxes: List[Dict[str, object]] = []
    varietal_boxes: List[Dict[str, object]] = []

    for i, box in enumerate(raw_boxes):
        if not isinstance(box, dict):
            continue
        box_id = box.get("id", i + 1)
        description = str(box.get("description", "") or "").strip()
        kind, value = classify_description(description)
        x_norm = to_float(box.get("x_norm"))
        y_norm = to_float(box.get("y_norm"))
        w_norm = to_float(box.get("w_norm"))
        h_norm = to_float(box.get("h_norm"))
        center_x = x_norm + (w_norm / 2.0)
        center_y = y_norm + (h_norm / 2.0)

        if kind == "pot_id" and value:
            pot_boxes.append(
                {
                    "id": box_id,
                    "order": i,
                    "description": description,
                    "pot_id": value,
                    "x_norm": x_norm,
                    "y_norm": y_norm,
                    "w_norm": w_norm,
                    "h_norm": h_norm,
                    "center_x": center_x,
                    "center_y": center_y,
                }
            )
        elif kind == "varietal_number" and value:
            varietal_boxes.append(
                {
                    "id": box_id,
                    "order": i,
                    "description": description,
                    "varietal_number": parse_int(value),
                    "x_norm": x_norm,
                    "y_norm": y_norm,
                    "w_norm": w_norm,
                    "h_norm": h_norm,
                    "center_x": center_x,
                    "center_y": center_y,
                }
            )

    return pot_boxes, varietal_boxes


def box_distance(a: Dict[str, object], b: Dict[str, object]) -> float:
    ax = float(a.get("center_x", 0.0))
    ay = float(a.get("center_y", 0.0))
    bx = float(b.get("center_x", 0.0))
    by = float(b.get("center_y", 0.0))
    return math.sqrt(((ax - bx) ** 2) + ((ay - by) ** 2))


def box_area(box: Dict[str, object]) -> float:
    w = float(box.get("w_norm", 0.0))
    h = float(box.get("h_norm", 0.0))
    return w * h


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def box_iou(a: Dict[str, object], b: Dict[str, object]) -> float:
    ax1 = clamp01(float(a.get("x_norm", 0.0)))
    ay1 = clamp01(float(a.get("y_norm", 0.0)))
    ax2 = clamp01(ax1 + float(a.get("w_norm", 0.0)))
    ay2 = clamp01(ay1 + float(a.get("h_norm", 0.0)))

    bx1 = clamp01(float(b.get("x_norm", 0.0)))
    by1 = clamp01(float(b.get("y_norm", 0.0)))
    bx2 = clamp01(bx1 + float(b.get("w_norm", 0.0)))
    by2 = clamp01(by1 + float(b.get("h_norm", 0.0)))

    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0

    area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def collapse_pot_duplicates(
    pot_boxes: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], int]:
    by_pot: Dict[str, List[Dict[str, object]]] = {}
    for box in pot_boxes:
        pot_id = str(box.get("pot_id", "") or "")
        if not pot_id:
            continue
        by_pot.setdefault(pot_id, []).append(box)

    kept: List[Dict[str, object]] = []
    dropped = 0
    for _, group in sorted(by_pot.items(), key=lambda kv: min(int(x.get("order", 0)) for x in kv[1])):
        if len(group) == 1:
            kept.append(group[0])
            continue
        # Pot IDs are globally unique in the run. Keep one representative box.
        chosen = max(group, key=lambda box: (box_area(box), -int(box.get("order", 0))))
        kept.append(chosen)
        dropped += len(group) - 1

    kept.sort(key=lambda box: int(box.get("order", 0)))
    return kept, dropped


def collapse_varietal_duplicates(
    varietal_boxes: List[Dict[str, object]],
    center_threshold: float = 0.04,
    iou_threshold: float = 0.5,
) -> Tuple[List[Dict[str, object]], int]:
    by_varietal: Dict[int, List[Dict[str, object]]] = {}
    for box in varietal_boxes:
        varietal_number = int(box.get("varietal_number", 0) or 0)
        if varietal_number <= 0:
            continue
        by_varietal.setdefault(varietal_number, []).append(box)

    kept: List[Dict[str, object]] = []
    dropped = 0
    for _, group in sorted(by_varietal.items(), key=lambda kv: min(int(x.get("order", 0)) for x in kv[1])):
        ordered = sorted(
            group,
            key=lambda box: (int(box.get("order", 0)), -box_area(box)),
        )
        local_kept: List[Dict[str, object]] = []
        for candidate in ordered:
            is_duplicate = False
            for existing in local_kept:
                if box_distance(candidate, existing) <= center_threshold:
                    is_duplicate = True
                    break
                if box_iou(candidate, existing) >= iou_threshold:
                    is_duplicate = True
                    break
            if is_duplicate:
                dropped += 1
            else:
                local_kept.append(candidate)
        kept.extend(local_kept)

    kept.sort(key=lambda box: int(box.get("order", 0)))
    return kept, dropped


def choose_edges(
    edges: List[Tuple[float, int, int]],
    matched_pots: set[int],
    matched_varietals: set[int],
) -> List[Tuple[int, int, float]]:
    chosen: List[Tuple[int, int, float]] = []
    for distance, pot_idx, varietal_idx in edges:
        if pot_idx in matched_pots or varietal_idx in matched_varietals:
            continue
        matched_pots.add(pot_idx)
        matched_varietals.add(varietal_idx)
        chosen.append((pot_idx, varietal_idx, distance))
    return chosen


def pair_nearest(
    pot_boxes: List[Dict[str, object]],
    varietal_boxes: List[Dict[str, object]],
    pot_series_map: Dict[str, int],
) -> Tuple[
    List[Tuple[Dict[str, object], Optional[Dict[str, object]], Optional[float], str]],
    List[Dict[str, object]],
]:
    matched_pots: set[int] = set()
    matched_varietals: set[int] = set()
    matches: Dict[int, Tuple[int, float, str]] = {}

    expected_edges: List[Tuple[float, int, int]] = []
    for pot_idx, pot in enumerate(pot_boxes):
        pot_id = str(pot.get("pot_id", "") or "")
        expected_series = int(pot_series_map.get(pot_id, 0) or 0)
        if expected_series <= 0:
            continue
        for var_idx, varietal in enumerate(varietal_boxes):
            varietal_number = int(varietal.get("varietal_number", 0) or 0)
            if varietal_number != expected_series:
                continue
            expected_edges.append((box_distance(pot, varietal), pot_idx, var_idx))
    expected_edges.sort(key=lambda edge: edge[0])

    for pot_idx, var_idx, distance in choose_edges(
        expected_edges, matched_pots, matched_varietals
    ):
        matches[pot_idx] = (var_idx, distance, "expected_series_nearest")

    fallback_edges: List[Tuple[float, int, int]] = []
    for pot_idx, pot in enumerate(pot_boxes):
        if pot_idx in matched_pots:
            continue
        for var_idx, varietal in enumerate(varietal_boxes):
            if var_idx in matched_varietals:
                continue
            fallback_edges.append((box_distance(pot, varietal), pot_idx, var_idx))
    fallback_edges.sort(key=lambda edge: edge[0])

    for pot_idx, var_idx, distance in choose_edges(
        fallback_edges, matched_pots, matched_varietals
    ):
        matches[pot_idx] = (var_idx, distance, "nearest_fallback")

    pairings: List[Tuple[Dict[str, object], Optional[Dict[str, object]], Optional[float], str]] = []
    for pot_idx, pot in enumerate(pot_boxes):
        matched = matches.get(pot_idx)
        if matched is None:
            pairings.append((pot, None, None, "unpaired"))
            continue
        varietal_idx, distance, strategy = matched
        pairings.append((pot, varietal_boxes[varietal_idx], distance, strategy))

    orphan_varietals = [
        varietal_boxes[idx]
        for idx in range(len(varietal_boxes))
        if idx not in matched_varietals
    ]
    orphan_varietals.sort(key=lambda box: int(box.get("order", 0)))
    return pairings, orphan_varietals


def resolve_pair_row(
    pair_index: int,
    pot_box: Dict[str, object],
    varietal_box: Optional[Dict[str, object]],
    distance: Optional[float],
    matching_strategy: str,
    pot_series_map: Dict[str, int],
    series_map: Dict[int, str],
) -> Dict[str, object]:
    pot_id = str(pot_box.get("pot_id", "") or "")
    expected_series_number = pot_series_map.get(pot_id, 0)
    expected_variety_name = series_map.get(expected_series_number, "")

    varietal_number = (
        int(varietal_box.get("varietal_number", 0))
        if varietal_box is not None
        else 0
    )
    varietal_name_from_annotation = series_map.get(varietal_number, "")

    needs_review = False
    review_reason = ""
    evidence_type = "pot_only"

    if varietal_box is None:
        needs_review = True
        review_reason = "missing_varietal_pair"
    elif expected_series_number <= 0:
        needs_review = True
        review_reason = "unknown_pot_series"
        evidence_type = "pot_plus_varietal_unvalidated"
    elif varietal_number != expected_series_number:
        needs_review = True
        review_reason = "pot_varietal_conflict"
        evidence_type = "pot_plus_varietal_conflict"
    else:
        evidence_type = "pot_plus_varietal_match"

    return {
        "pair_index": pair_index,
        "matching_strategy": matching_strategy,
        "pot_box_id": pot_box.get("id"),
        "pot_id": pot_id,
        "varietal_box_id": varietal_box.get("id") if varietal_box else "",
        "varietal_number": varietal_number if varietal_number > 0 else "",
        "expected_series_number": expected_series_number if expected_series_number > 0 else "",
        "expected_variety_name": expected_variety_name,
        "varietal_name_from_annotation": varietal_name_from_annotation,
        "center_distance": round(distance, 6) if distance is not None else "",
        "needs_review": needs_review,
        "review_reason": review_reason,
        "evidence_type": evidence_type,
    }


def resolve_orphan_varietal_row(
    pair_index: int,
    varietal_box: Dict[str, object],
    series_map: Dict[int, str],
) -> Dict[str, object]:
    varietal_number = int(varietal_box.get("varietal_number", 0))
    return {
        "pair_index": pair_index,
        "pot_box_id": "",
        "pot_id": "",
        "varietal_box_id": varietal_box.get("id"),
        "varietal_number": varietal_number if varietal_number > 0 else "",
        "expected_series_number": "",
        "expected_variety_name": "",
        "varietal_name_from_annotation": series_map.get(varietal_number, ""),
        "center_distance": "",
        "needs_review": True,
        "review_reason": "orphan_varietal_without_pot",
        "evidence_type": "varietal_only",
    }


def resolve_seed(
    seed: Dict[str, object],
    pot_series_map: Dict[str, int],
    series_map: Dict[int, str],
) -> Dict[str, object]:
    pot_boxes_raw, varietal_boxes_raw = extract_typed_boxes(seed)
    pot_boxes, dropped_pot_duplicates = collapse_pot_duplicates(pot_boxes_raw)
    varietal_boxes, dropped_varietal_duplicates = collapse_varietal_duplicates(
        varietal_boxes_raw
    )
    pairings, orphan_varietals = pair_nearest(
        pot_boxes, varietal_boxes, pot_series_map=pot_series_map
    )

    rows: List[Dict[str, object]] = []
    review_reason_counts: Counter[str] = Counter()
    evidence_type_counts: Counter[str] = Counter()
    matching_strategy_counts: Counter[str] = Counter()
    needs_review_count = 0

    pair_index = 1
    for pot_box, varietal_box, distance, matching_strategy in pairings:
        row = resolve_pair_row(
            pair_index=pair_index,
            pot_box=pot_box,
            varietal_box=varietal_box,
            distance=distance,
            matching_strategy=matching_strategy,
            pot_series_map=pot_series_map,
            series_map=series_map,
        )
        rows.append(row)
        evidence_type_counts[str(row["evidence_type"])] += 1
        matching_strategy_counts[str(row["matching_strategy"])] += 1
        if bool(row["needs_review"]):
            needs_review_count += 1
            review_reason_counts[str(row["review_reason"])] += 1
        pair_index += 1

    for varietal_box in orphan_varietals:
        row = resolve_orphan_varietal_row(
            pair_index=pair_index,
            varietal_box=varietal_box,
            series_map=series_map,
        )
        rows.append(row)
        evidence_type_counts[str(row["evidence_type"])] += 1
        matching_strategy_counts["orphan_varietal"] += 1
        needs_review_count += 1
        review_reason_counts[str(row["review_reason"])] += 1
        pair_index += 1

    total_rows = len(rows)
    auto_resolved_count = total_rows - needs_review_count

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture_date": seed.get("capture_date", ""),
        "row_index": seed.get("row_index", ""),
        "source_asset_id": seed.get("source_asset_id", ""),
        "photo_url": seed.get("photo_url", ""),
        "total_rows": total_rows,
        "pot_boxes_raw": len(pot_boxes_raw),
        "varietal_boxes_raw": len(varietal_boxes_raw),
        "pot_boxes": len(pot_boxes),
        "varietal_boxes": len(varietal_boxes),
        "duplicate_tag_counts": {
            "pot_id_collapsed": dropped_pot_duplicates,
            "varietal_collapsed": dropped_varietal_duplicates,
        },
        "needs_review_count": needs_review_count,
        "auto_resolved_count": auto_resolved_count,
        "review_reason_counts": dict(review_reason_counts),
        "evidence_type_counts": dict(evidence_type_counts),
        "matching_strategy_counts": dict(matching_strategy_counts),
        "rows": rows,
    }


def build_markdown(
    resolution: Dict[str, object], input_json: Path, output_json: Path
) -> str:
    rows = resolution.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    review_reason_counts = resolution.get("review_reason_counts", {})
    if not isinstance(review_reason_counts, dict):
        review_reason_counts = {}
    evidence_type_counts = resolution.get("evidence_type_counts", {})
    if not isinstance(evidence_type_counts, dict):
        evidence_type_counts = {}
    matching_strategy_counts = resolution.get("matching_strategy_counts", {})
    if not isinstance(matching_strategy_counts, dict):
        matching_strategy_counts = {}
    duplicate_tag_counts = resolution.get("duplicate_tag_counts", {})
    if not isinstance(duplicate_tag_counts, dict):
        duplicate_tag_counts = {}

    lines = [
        "# V1.8 Quick Seed Pair Resolution",
        "",
        f"Generated: `{resolution.get('generated_at_utc', '')}`",
        "",
        "## Inputs",
        "",
        f"- Seed JSON: `{input_json}`",
        f"- Output JSON: `{output_json}`",
        f"- capture_date: `{resolution.get('capture_date', '')}`",
        f"- source_asset_id: `{resolution.get('source_asset_id', '')}`",
        "",
        "## Summary",
        "",
        f"- pot boxes: `{resolution.get('pot_boxes', 0)}` (raw: `{resolution.get('pot_boxes_raw', 0)}`)",
        f"- varietal boxes: `{resolution.get('varietal_boxes', 0)}` (raw: `{resolution.get('varietal_boxes_raw', 0)}`)",
        f"- pot duplicates collapsed: `{duplicate_tag_counts.get('pot_id_collapsed', 0)}`",
        f"- varietal duplicates collapsed: `{duplicate_tag_counts.get('varietal_collapsed', 0)}`",
        f"- resolved rows: `{resolution.get('total_rows', 0)}`",
        f"- auto resolved: `{resolution.get('auto_resolved_count', 0)}`",
        f"- needs review: `{resolution.get('needs_review_count', 0)}`",
        "",
        "## Review Reasons",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]

    if review_reason_counts:
        for reason, count in sorted(review_reason_counts.items()):
            lines.append(f"| `{reason}` | {count} |")
    else:
        lines.append("| _(none)_ | 0 |")

    lines.extend(["", "## Evidence Types", "", "| Evidence Type | Count |", "|---|---:|"])
    for evidence_type, count in sorted(evidence_type_counts.items()):
        lines.append(f"| `{evidence_type}` | {count} |")

    lines.extend(["", "## Matching Strategies", "", "| Strategy | Count |", "|---|---:|"])
    for strategy, count in sorted(matching_strategy_counts.items()):
        lines.append(f"| `{strategy}` | {count} |")

    lines.extend(
        [
            "",
            "## Pair Results",
            "",
            "| Pair | Strategy | Pot ID | Varietal # | Expected # | Expected Variety | Needs Review | Reason | Distance |",
            "|---:|---|---|---:|---:|---|---|---|---:|",
        ]
    )

    for row in rows:
        pot_id = row.get("pot_id", "")
        varietal_number = row.get("varietal_number", "")
        expected_series = row.get("expected_series_number", "")
        expected_variety = row.get("expected_variety_name", "")
        needs_review = row.get("needs_review", False)
        reason = row.get("review_reason", "")
        distance = row.get("center_distance", "")
        lines.append(
            "| {pair} | `{strategy}` | `{pot}` | `{varietal}` | `{expected}` | {variety} | `{review}` | `{reason}` | `{dist}` |".format(
                pair=row.get("pair_index", ""),
                strategy=row.get("matching_strategy", ""),
                pot=pot_id,
                varietal=varietal_number,
                expected=expected_series,
                variety=expected_variety,
                review=needs_review,
                reason=reason,
                dist=distance,
            )
        )

    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pair quick-seed pot + varietal boxes and flag conflicts."
    )
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
    )
    parser.add_argument(
        "--pot-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
    )
    parser.add_argument(
        "--baseline-mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_8/quick_seed_pair_resolution.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.8-QUICK-SEED-PAIR-RESOLUTION.md"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    seed = read_json(args.input_json)
    series_map = load_series_map(args.series_map_csv)
    pot_series_map = load_pot_series_map(args.pot_overrides_csv, args.baseline_mapping_csv)
    resolution = resolve_seed(seed, pot_series_map=pot_series_map, series_map=series_map)

    write_json(args.output_json, resolution)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        build_markdown(resolution, args.input_json, args.output_json), encoding="utf-8"
    )

    print(f"input_json={args.input_json}")
    print(f"rows={resolution['total_rows']}")
    print(f"needs_review={resolution['needs_review_count']}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
