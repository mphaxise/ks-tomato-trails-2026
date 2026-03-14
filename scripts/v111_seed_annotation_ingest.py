#!/usr/bin/env python3
"""Normalize v1.10 seed-label exports into a v1.11 training-ingest dataset."""

from __future__ import annotations

import argparse
import csv
import json
import posixpath
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from stable_generated_output import (
    stabilize_json_timestamp,
    write_json_if_changed,
    write_text_if_changed,
)

KNOWN_LABELS = [
    "pot_region",
    "pot_interior",
    "plant_region",
    "pot_label",
    "neighbor_spill_region",
    "fruit_cluster",
    "leaf_health_issue",
    "background_number",
    "other",
]
KNOWN_LABEL_TO_ID = {label: index for index, label in enumerate(KNOWN_LABELS)}
REQUIRED_SEED_LABELS = ("pot_region", "pot_interior", "plant_region")

INGEST_STATUS_ORDER = {
    "ready_for_training": 0,
    "missing_required_labels": 1,
    "pot_id_mismatch": 2,
    "missing_local_image": 3,
    "missing_export": 4,
    "invalid_export": 5,
    "started_empty": 6,
    "pending_annotation": 7,
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv_rows(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def read_json_optional(path: Path) -> Optional[Dict[str, object]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def html_table_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|")


def bool_from_value(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def safe_float(value: object) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def rank_value(value: object) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 10_000


def normalize_repo_path(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("/"):
        return text
    normalized = posixpath.normpath(posixpath.join("tracker", text))
    return normalized


def path_exists(path_text: str) -> bool:
    if not path_text:
        return False
    if path_text.startswith("http://") or path_text.startswith("https://"):
        return False
    return Path(path_text).exists()


def export_path_from_row(row: Dict[str, str]) -> Optional[Path]:
    export_path = str(row.get("latest_export_json_path", "") or "").strip()
    return Path(export_path) if export_path else None


def pick_image_page_path(row: Dict[str, str]) -> str:
    for key in ("crop_path", "image_src", "overlay_path"):
        candidate = str(row.get(key, "") or "").strip()
        if candidate:
            return candidate
    return ""


def unique_labels(boxes: Sequence[Dict[str, object]]) -> List[str]:
    labels = sorted(
        {
            str(box.get("label", "") or "").strip()
            for box in boxes
            if isinstance(box, dict) and str(box.get("label", "") or "").strip()
        }
    )
    return labels


def normalized_geometry(
    box: Dict[str, object],
    image_width: Optional[float],
    image_height: Optional[float],
) -> Optional[Dict[str, float]]:
    x_norm = safe_float(box.get("x_norm"))
    y_norm = safe_float(box.get("y_norm"))
    w_norm = safe_float(box.get("w_norm"))
    h_norm = safe_float(box.get("h_norm"))

    if None in {x_norm, y_norm, w_norm, h_norm} and image_width and image_height:
        x = safe_float(box.get("x"))
        y = safe_float(box.get("y"))
        w = safe_float(box.get("w"))
        h = safe_float(box.get("h"))
        if None not in {x, y, w, h}:
            x_norm = x / image_width
            y_norm = y / image_height
            w_norm = w / image_width
            h_norm = h / image_height

    if None in {x_norm, y_norm, w_norm, h_norm}:
        return None

    x_center_norm = x_norm + (w_norm / 2.0)
    y_center_norm = y_norm + (h_norm / 2.0)
    return {
        "x_norm": x_norm,
        "y_norm": y_norm,
        "w_norm": w_norm,
        "h_norm": h_norm,
        "x_center_norm": x_center_norm,
        "y_center_norm": y_center_norm,
        "area_norm": w_norm * h_norm,
    }


def cleanup_yolo_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("*.txt"):
        path.unlink()


def task_sort_key(row: Dict[str, object]) -> Tuple[int, int, str]:
    return (
        INGEST_STATUS_ORDER.get(str(row.get("ingest_status", "") or "").strip(), 99),
        rank_value(row.get("seed_rank")),
        str(row.get("pot_id", "") or "").strip().upper(),
    )


def build_next_step(
    ingest_status: str,
    pot_id: str,
    missing_required_labels: Sequence[str],
    effective_pot_id: str,
) -> str:
    if ingest_status == "ready_for_training":
        return "Use this task in the first indoor pot/plant detector baseline."
    if ingest_status == "missing_required_labels":
        missing_text = ", ".join(missing_required_labels)
        return f"Re-open the task and add the missing required labels: {missing_text}."
    if ingest_status == "pot_id_mismatch":
        return f"Resolve the pot identity before training. Current effective pot is {effective_pot_id or pot_id}."
    if ingest_status == "missing_local_image":
        return "Restore the local crop image path before exporting training labels."
    if ingest_status == "missing_export":
        return "Rebuild the seed annotation status collector after restoring the export JSON path."
    if ingest_status == "invalid_export":
        return "Replace or repair the export JSON before using this task downstream."
    if ingest_status == "started_empty":
        return "Continue the task-aware labeler and add the first set of boxes."
    return "Open the task in the seed labeler and complete the first annotation pass."


def build_task_rows(
    manifest_rows: Sequence[Dict[str, str]],
    output_yolo_dir: Path,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Counter[str], Counter[str]]:
    task_rows: List[Dict[str, object]] = []
    box_rows: List[Dict[str, object]] = []
    label_counts: Counter[str] = Counter()
    required_label_task_counts: Counter[str] = Counter()

    cleanup_yolo_dir(output_yolo_dir)

    for manifest_row in manifest_rows:
        annotation_status = str(manifest_row.get("annotation_status", "") or "").strip() or "pending"
        pot_id = str(manifest_row.get("pot_id", "") or "").strip()
        task_key = str(manifest_row.get("task_key", "") or "").strip()
        export_path = export_path_from_row(manifest_row)
        export_payload = read_json_optional(export_path) if export_path is not None else None
        export_path_exists = export_path.exists() if export_path is not None else False
        pot_id_mismatch = bool_from_value(manifest_row.get("pot_id_mismatch", ""))
        image_page_path = pick_image_page_path(manifest_row)
        image_repo_path = normalize_repo_path(image_page_path)
        image_exists = path_exists(image_repo_path)
        reviewer = str(manifest_row.get("reviewer", "") or "").strip()
        boxes: List[Dict[str, object]] = []
        labels_present: List[str] = []
        missing_required_labels: List[str] = []
        yolo_lines: List[str] = []
        yolo_label_path = ""
        yolo_box_count = 0

        if export_payload is not None:
            raw_boxes = export_payload.get("boxes", [])
            if isinstance(raw_boxes, list):
                boxes = [box for box in raw_boxes if isinstance(box, dict)]
            labels_present = unique_labels(boxes)
            missing_required_labels = [
                label for label in REQUIRED_SEED_LABELS if label not in labels_present
            ]
            for label in labels_present:
                required_label_task_counts[label] += 1
        elif annotation_status in {"pending", "started_empty"}:
            missing_required_labels = list(REQUIRED_SEED_LABELS)

        if annotation_status == "pending":
            ingest_status = "pending_annotation"
        elif annotation_status == "started_empty":
            ingest_status = "started_empty"
        elif export_path is None or not export_path_exists:
            ingest_status = "missing_export"
        elif export_payload is None:
            ingest_status = "invalid_export"
        elif pot_id_mismatch:
            ingest_status = "pot_id_mismatch"
        elif missing_required_labels:
            ingest_status = "missing_required_labels"
        elif not image_exists:
            ingest_status = "missing_local_image"
        else:
            ingest_status = "ready_for_training"

        image_width = safe_float(export_payload.get("image_width")) if export_payload else None
        image_height = safe_float(export_payload.get("image_height")) if export_payload else None
        if ingest_status == "ready_for_training" and boxes:
            for box in boxes:
                label = str(box.get("label", "") or "").strip()
                class_id = KNOWN_LABEL_TO_ID.get(label)
                geometry = normalized_geometry(box, image_width, image_height)
                if class_id is None or geometry is None:
                    continue
                yolo_lines.append(
                    f"{class_id} "
                    f"{geometry['x_center_norm']:.6f} "
                    f"{geometry['y_center_norm']:.6f} "
                    f"{geometry['w_norm']:.6f} "
                    f"{geometry['h_norm']:.6f}"
                )
            yolo_box_count = len(yolo_lines)
            if yolo_box_count > 0:
                yolo_path = output_yolo_dir / f"{task_key or pot_id.lower()}.txt"
                yolo_path.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
                yolo_label_path = str(yolo_path)

        ready_for_training = ingest_status == "ready_for_training" and bool(yolo_label_path)
        if ingest_status == "ready_for_training" and not ready_for_training:
            ingest_status = "invalid_export"

        for box in boxes:
            label = str(box.get("label", "") or "").strip()
            geometry = normalized_geometry(box, image_width, image_height)
            if not label or geometry is None:
                continue
            label_counts[label] += 1
            box_rows.append(
                {
                    "task_key": task_key,
                    "pot_id": pot_id,
                    "variety_name": manifest_row.get("variety_name", ""),
                    "seed_rank": manifest_row.get("seed_rank", ""),
                    "queue_priority_rank": manifest_row.get("queue_priority_rank", ""),
                    "reviewer": reviewer,
                    "task_ingest_status": ingest_status,
                    "ready_for_training": "yes" if ready_for_training else "",
                    "label": label,
                    "class_id": KNOWN_LABEL_TO_ID.get(label, ""),
                    "box_id": box.get("id", ""),
                    "x": box.get("x", ""),
                    "y": box.get("y", ""),
                    "w": box.get("w", ""),
                    "h": box.get("h", ""),
                    "x_norm": f"{geometry['x_norm']:.6f}",
                    "y_norm": f"{geometry['y_norm']:.6f}",
                    "w_norm": f"{geometry['w_norm']:.6f}",
                    "h_norm": f"{geometry['h_norm']:.6f}",
                    "x_center_norm": f"{geometry['x_center_norm']:.6f}",
                    "y_center_norm": f"{geometry['y_center_norm']:.6f}",
                    "area_norm": f"{geometry['area_norm']:.6f}",
                    "image_page_path": image_page_path,
                    "image_repo_path": image_repo_path,
                    "export_json_path": str(export_path) if export_path is not None else "",
                }
            )

        task_rows.append(
            {
                "task_key": task_key,
                "pot_id": pot_id,
                "variety_name": manifest_row.get("variety_name", ""),
                "seed_rank": manifest_row.get("seed_rank", ""),
                "queue_priority_rank": manifest_row.get("queue_priority_rank", ""),
                "annotation_status": annotation_status,
                "ingest_status": ingest_status,
                "reviewer": reviewer,
                "export_json_path": str(export_path) if export_path is not None else "",
                "image_page_path": image_page_path,
                "image_repo_path": image_repo_path,
                "image_exists": "yes" if image_exists else "",
                "crop_path": manifest_row.get("crop_path", ""),
                "overlay_path": manifest_row.get("overlay_path", ""),
                "annotate_url": manifest_row.get("annotate_url", ""),
                "reference_url": manifest_row.get("reference_url", ""),
                "box_count": len(boxes),
                "labels_present": "|".join(labels_present),
                "required_labels_missing": "|".join(missing_required_labels),
                "yolo_label_path": yolo_label_path,
                "yolo_box_count": yolo_box_count,
                "ready_for_training": "yes" if ready_for_training else "",
                "expected_pot_id": manifest_row.get("expected_pot_id", ""),
                "effective_pot_id": manifest_row.get("effective_pot_id", ""),
                "pot_id_verdict": manifest_row.get("pot_id_verdict", ""),
                "pot_id_mismatch": "yes" if pot_id_mismatch else "",
                "next_step": build_next_step(
                    ingest_status=ingest_status,
                    pot_id=pot_id,
                    missing_required_labels=missing_required_labels,
                    effective_pot_id=str(manifest_row.get("effective_pot_id", "") or "").strip(),
                ),
            }
        )

    task_rows.sort(key=task_sort_key)
    box_rows.sort(
        key=lambda row: (
            rank_value(row.get("seed_rank")),
            str(row.get("pot_id", "") or "").strip().upper(),
            rank_value(row.get("box_id")),
        )
    )
    return task_rows, box_rows, label_counts, required_label_task_counts


def recommend_next_step(task_rows: Sequence[Dict[str, object]]) -> str:
    ready_rows = [row for row in task_rows if bool_from_value(row.get("ready_for_training", ""))]
    pending_rows = [
        row
        for row in task_rows
        if str(row.get("ingest_status", "") or "").strip() in {"pending_annotation", "started_empty"}
    ]

    if len(ready_rows) >= 8:
        return (
            "Use the ready-for-training rows to benchmark the first indoor pot/plant box detector, "
            "then compare detector crops against the v1.10 heuristic pot focus scores."
        )
    if len(ready_rows) >= 4:
        return (
            "Keep annotating until at least eight clean indoor tasks are ready, but the repo now has enough "
            "training-ready seed data to start a low-cost detector baseline on pot_region/pot_interior/plant_region."
        )
    if pending_rows:
        focus = ", ".join(str(row.get("pot_id", "") or "").strip() for row in pending_rows[:4])
        return (
            "Finish the first clean indoor seed annotations for "
            f"{focus}. Once four tasks are ready, rerun v1.11 ingest and start the first detector baseline."
        )
    return (
        "Resolve the remaining blocked tasks, then rerun v1.11 ingest and export the first training-ready seed batch."
    )


def build_summary(
    task_rows: Sequence[Dict[str, object]],
    box_rows: Sequence[Dict[str, object]],
    label_counts: Counter[str],
    required_label_task_counts: Counter[str],
    source_manifest_csv: Path,
    output_yolo_dir: Path,
) -> Dict[str, object]:
    status_counts = Counter(str(row.get("ingest_status", "") or "").strip() for row in task_rows)
    pending_pots = [
        str(row.get("pot_id", "") or "").strip()
        for row in task_rows
        if str(row.get("ingest_status", "") or "").strip() in {"pending_annotation", "started_empty"}
    ]
    ready_task_keys = [
        str(row.get("task_key", "") or "").strip()
        for row in task_rows
        if bool_from_value(row.get("ready_for_training", ""))
    ]
    return {
        "generated_at_utc": iso_now(),
        "source_status_manifest_csv": str(source_manifest_csv),
        "output_yolo_dir": str(output_yolo_dir),
        "total_tasks": len(task_rows),
        "completed_annotation_tasks": int(
            sum(1 for row in task_rows if str(row.get("annotation_status", "") or "").strip() == "completed")
        ),
        "pending_annotation_tasks": int(status_counts.get("pending_annotation", 0)),
        "started_empty_tasks": int(status_counts.get("started_empty", 0)),
        "ready_for_training_tasks": int(status_counts.get("ready_for_training", 0)),
        "missing_required_label_tasks": int(status_counts.get("missing_required_labels", 0)),
        "pot_id_mismatch_tasks": int(status_counts.get("pot_id_mismatch", 0)),
        "missing_local_image_tasks": int(status_counts.get("missing_local_image", 0)),
        "missing_export_tasks": int(status_counts.get("missing_export", 0)),
        "invalid_export_tasks": int(status_counts.get("invalid_export", 0)),
        "total_boxes_ingested": len(box_rows),
        "yolo_label_files_written": len(ready_task_keys),
        "yolo_box_rows_written": int(
            sum(rank_value(row.get("yolo_box_count")) for row in task_rows if bool_from_value(row.get("ready_for_training", "")))
        ),
        "label_counts": dict(sorted(label_counts.items())),
        "required_label_task_counts": {
            label: int(required_label_task_counts.get(label, 0)) for label in REQUIRED_SEED_LABELS
        },
        "pending_pots": pending_pots,
        "ready_task_keys": ready_task_keys,
        "recommended_next_step": recommend_next_step(task_rows),
    }


def render_markdown(
    summary: Dict[str, object],
    task_rows: Sequence[Dict[str, object]],
    source_manifest_csv: Path,
    output_task_csv: Path,
    output_box_csv: Path,
    output_summary_json: Path,
) -> str:
    lines = [
        "# V1.11 Seed Annotation Ingest",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        "",
        "## Landscape Assessment",
        "",
        "- `PlantCV`-style indoor masking and pot isolation are already represented in this repo by the v1.10 pot-anchored crops, focus scores, spill scoring, and seed queue.",
        "- `AgML`-style dataset/training readiness was the remaining gap: the repo had annotation tasks and a status board, but no normalized ingest layer for detector training.",
        "- The prior repo research still holds: there is no obvious off-the-shelf indoor tomato `pot identity` package to drop in, so a project-specific annotation ingest contract is the highest-value next bridge.",
        "",
        "## Inputs",
        "",
        f"- Source status manifest: `{source_manifest_csv}`",
        f"- Task ingest CSV: `{output_task_csv}`",
        f"- Box ingest CSV: `{output_box_csv}`",
        f"- Summary JSON: `{output_summary_json}`",
        f"- YOLO label dir: `{summary.get('output_yolo_dir', '')}`",
        "",
        "## Snapshot",
        "",
        f"- Total seed tasks: `{summary.get('total_tasks', 0)}`",
        f"- Completed annotation tasks: `{summary.get('completed_annotation_tasks', 0)}`",
        f"- Ready for training: `{summary.get('ready_for_training_tasks', 0)}`",
        f"- Missing required labels: `{summary.get('missing_required_label_tasks', 0)}`",
        f"- Pot-ID mismatches: `{summary.get('pot_id_mismatch_tasks', 0)}`",
        f"- Pending annotation tasks: `{summary.get('pending_annotation_tasks', 0)}`",
        f"- Started-empty tasks: `{summary.get('started_empty_tasks', 0)}`",
        f"- Total boxes ingested: `{summary.get('total_boxes_ingested', 0)}`",
        "",
        "## Required Label Coverage",
        "",
        "| Label | Tasks Containing Label |",
        "|---|---:|",
    ]
    required_counts = summary.get("required_label_task_counts", {})
    if isinstance(required_counts, dict):
        for label in REQUIRED_SEED_LABELS:
            lines.append(f"| `{label}` | {required_counts.get(label, 0)} |")

    lines.extend(
        [
            "",
            "## Task Routing",
            "",
            "| Pot | Ingest Status | Labels Present | Missing Required | Next Step |",
            "|---|---|---|---|---|",
        ]
    )
    for row in task_rows:
        labels_present = str(row.get("labels_present", "") or "").replace("|", ", ") or "n/a"
        missing = str(row.get("required_labels_missing", "") or "").replace("|", ", ") or "none"
        lines.append(
            "| `{pot}` | `{status}` | {labels} | {missing} | {next_step} |".format(
                pot=html_table_escape(row.get("pot_id", "")),
                status=html_table_escape(row.get("ingest_status", "")),
                labels=html_table_escape(labels_present),
                missing=html_table_escape(missing),
                next_step=html_table_escape(row.get("next_step", "")),
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Next Experiment",
            "",
            f"1. {summary.get('recommended_next_step', '')}",
            "2. Keep the indoor-first scope: use these seed tasks to bootstrap the first custom pot/plant detector before attempting outdoor generalization.",
            "3. Once the first detector exists, compare its crop isolation against the v1.10 heuristic spill metrics instead of replacing the heuristic path blindly.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status-manifest-csv",
        type=Path,
        default=Path("data/research/v1_10/seed_label_annotation_manifest.csv"),
        help="Status manifest built from v1.10 seed-label exports.",
    )
    parser.add_argument(
        "--output-task-csv",
        type=Path,
        default=Path("data/research/v1_11/seed_annotation_ingest_manifest.csv"),
        help="Output task-level ingest CSV path.",
    )
    parser.add_argument(
        "--output-box-csv",
        type=Path,
        default=Path("data/research/v1_11/seed_annotation_box_rows.csv"),
        help="Output box-level ingest CSV path.",
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("data/research/v1_11/seed_annotation_ingest_summary.json"),
        help="Output ingest summary JSON path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.11-SEED-ANNOTATION-INGEST.md"),
        help="Output markdown research note path.",
    )
    parser.add_argument(
        "--output-yolo-dir",
        type=Path,
        default=Path("data/research/v1_11/yolo_labels"),
        help="Directory for YOLO-format label files.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    manifest_rows = read_csv_rows(args.status_manifest_csv)
    task_rows, box_rows, label_counts, required_label_task_counts = build_task_rows(
        manifest_rows=manifest_rows,
        output_yolo_dir=args.output_yolo_dir,
    )
    summary = stabilize_json_timestamp(
        args.output_summary_json,
        build_summary(
            task_rows=task_rows,
            box_rows=box_rows,
            label_counts=label_counts,
            required_label_task_counts=required_label_task_counts,
            source_manifest_csv=args.status_manifest_csv,
            output_yolo_dir=args.output_yolo_dir,
        ),
    )

    task_fieldnames = [
        "task_key",
        "pot_id",
        "variety_name",
        "seed_rank",
        "queue_priority_rank",
        "annotation_status",
        "ingest_status",
        "reviewer",
        "export_json_path",
        "image_page_path",
        "image_repo_path",
        "image_exists",
        "crop_path",
        "overlay_path",
        "annotate_url",
        "reference_url",
        "box_count",
        "labels_present",
        "required_labels_missing",
        "yolo_label_path",
        "yolo_box_count",
        "ready_for_training",
        "expected_pot_id",
        "effective_pot_id",
        "pot_id_verdict",
        "pot_id_mismatch",
        "next_step",
    ]
    box_fieldnames = [
        "task_key",
        "pot_id",
        "variety_name",
        "seed_rank",
        "queue_priority_rank",
        "reviewer",
        "task_ingest_status",
        "ready_for_training",
        "label",
        "class_id",
        "box_id",
        "x",
        "y",
        "w",
        "h",
        "x_norm",
        "y_norm",
        "w_norm",
        "h_norm",
        "x_center_norm",
        "y_center_norm",
        "area_norm",
        "image_page_path",
        "image_repo_path",
        "export_json_path",
    ]
    write_csv_rows(args.output_task_csv, task_fieldnames, task_rows)
    write_csv_rows(args.output_box_csv, box_fieldnames, box_rows)
    write_json_if_changed(args.output_summary_json, summary)
    write_text_if_changed(
        args.output_md,
        render_markdown(
            summary=summary,
            task_rows=task_rows,
            source_manifest_csv=args.status_manifest_csv,
            output_task_csv=args.output_task_csv,
            output_box_csv=args.output_box_csv,
            output_summary_json=args.output_summary_json,
        ),
    )

    print(f"status_manifest_csv={args.status_manifest_csv}")
    print(f"total_tasks={summary['total_tasks']}")
    print(f"ready_for_training_tasks={summary['ready_for_training_tasks']}")
    print(f"output_task_csv={args.output_task_csv}")
    print(f"output_box_csv={args.output_box_csv}")
    print(f"output_summary_json={args.output_summary_json}")
    print(f"output_md={args.output_md}")
    print(f"output_yolo_dir={args.output_yolo_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
