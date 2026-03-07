#!/usr/bin/env python3
"""Summarize v1.10 seed-labeler exports into a manifest and status report."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import build_v110_mask_seed_page as seed_page


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


def parse_saved_at(value: object, fallback_path: Path) -> Tuple[datetime, str]:
    text = str(value or "").strip()
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc), text
        except ValueError:
            pass
    fallback_dt = datetime.fromtimestamp(fallback_path.stat().st_mtime, tz=timezone.utc)
    return fallback_dt, fallback_dt.isoformat()


def collect_exports(
    exports_dir: Path,
) -> Tuple[Dict[str, Dict[str, object]], Counter[str], List[str]]:
    latest_by_task: Dict[str, Dict[str, object]] = {}
    export_counts: Counter[str] = Counter()
    unassigned_files: List[str] = []
    if not exports_dir.exists():
        return latest_by_task, export_counts, unassigned_files

    for path in sorted(exports_dir.rglob("*.json")):
        payload = read_json_optional(path)
        if payload is None:
            unassigned_files.append(str(path))
            continue
        task_key = str(payload.get("task_key", "") or "").strip()
        if not task_key:
            task_meta = payload.get("task_metadata")
            if isinstance(task_meta, dict):
                task_key = str(task_meta.get("task_key", "") or "").strip()
        if not task_key:
            unassigned_files.append(str(path))
            continue

        export_counts[task_key] += 1
        saved_dt, saved_at_text = parse_saved_at(payload.get("saved_at_utc"), path)
        candidate = {
            "payload": payload,
            "path": str(path),
            "saved_at_dt": saved_dt,
            "saved_at_utc": saved_at_text,
        }
        existing = latest_by_task.get(task_key)
        if existing is None or candidate["saved_at_dt"] > existing["saved_at_dt"]:
            latest_by_task[task_key] = candidate

    return latest_by_task, export_counts, unassigned_files


def labels_present(payload: Dict[str, object]) -> List[str]:
    boxes = payload.get("boxes", [])
    if not isinstance(boxes, list):
        return []
    labels = sorted(
        {
            str(box.get("label", "") or "").strip()
            for box in boxes
            if isinstance(box, dict) and str(box.get("label", "") or "").strip()
        }
    )
    return labels


def box_count(payload: Dict[str, object]) -> int:
    boxes = payload.get("boxes", [])
    if not isinstance(boxes, list):
        return 0
    return len([box for box in boxes if isinstance(box, dict)])


def build_manifest(
    seed_rows: Sequence[Dict[str, str]],
    latest_by_task: Dict[str, Dict[str, object]],
    export_counts: Counter[str],
) -> List[Dict[str, object]]:
    manifest_rows: List[Dict[str, object]] = []
    for row in seed_rows:
        task_key = seed_page.task_key_for_row(row)
        latest = latest_by_task.get(task_key)
        export_count = int(export_counts.get(task_key, 0))
        crop_path = seed_page.path_for_page(row.get("crop_path", "") or "")
        overlay_path = seed_page.path_for_page(row.get("overlay_path", "") or "")
        annotate_url = seed_page.build_labeler_link(row)

        status = "pending"
        latest_export_json_path = ""
        latest_saved_at_utc = ""
        reviewer = ""
        export_box_count = 0
        export_labels: List[str] = []
        image_src = crop_path or overlay_path
        reference_url = seed_page.path_for_page(row.get("photo_url", "") or "")
        if latest is not None:
            payload = latest["payload"]
            latest_export_json_path = str(latest["path"])
            latest_saved_at_utc = str(latest["saved_at_utc"])
            reviewer = str(payload.get("reviewer", "") or "").strip()
            export_box_count = box_count(payload)
            export_labels = labels_present(payload)
            image_src = seed_page.path_for_page(str(payload.get("image_src", "") or "").strip()) or image_src
            status = "completed" if export_box_count > 0 else "started_empty"

        next_action = (
            "Review the latest export and decide whether this task is ready for polygon mask follow-up."
            if status == "completed"
            else (
                "Continue labeling this task in the task-aware seed labeler."
                if status == "started_empty"
                else "Open the seed pack and start the first annotation pass for this crop."
            )
        )

        manifest_rows.append(
            {
                "task_key": task_key,
                "pot_id": row.get("pot_id", ""),
                "variety_name": row.get("variety_name", ""),
                "seed_rank": row.get("seed_rank", ""),
                "queue_priority_rank": row.get("queue_priority_rank", ""),
                "source_asset_id": row.get("source_asset_id", ""),
                "annotation_status": status,
                "export_count": export_count,
                "latest_export_json_path": latest_export_json_path,
                "latest_saved_at_utc": latest_saved_at_utc,
                "reviewer": reviewer,
                "box_count": export_box_count,
                "labels_present": "|".join(export_labels),
                "image_src": image_src,
                "crop_path": crop_path,
                "overlay_path": overlay_path,
                "annotate_url": annotate_url,
                "reference_url": reference_url,
                "next_action": next_action,
            }
        )
    return manifest_rows


def build_summary(
    manifest_rows: Sequence[Dict[str, object]],
    unassigned_files: Sequence[str],
) -> Dict[str, object]:
    status_counts = Counter(str(row.get("annotation_status", "") or "").strip() for row in manifest_rows)
    reviewer_counts = Counter(
        str(row.get("reviewer", "") or "").strip()
        for row in manifest_rows
        if str(row.get("reviewer", "") or "").strip()
    )
    label_counts: Counter[str] = Counter()
    for row in manifest_rows:
        for label in str(row.get("labels_present", "") or "").split("|"):
            cleaned = label.strip()
            if cleaned:
                label_counts[cleaned] += 1
    pending_pots = [
        str(row.get("pot_id", "") or "").strip()
        for row in manifest_rows
        if str(row.get("annotation_status", "") or "").strip() == "pending"
    ]
    return {
        "generated_at_utc": iso_now(),
        "expected_tasks": len(manifest_rows),
        "completed_tasks": int(status_counts.get("completed", 0)),
        "started_empty_tasks": int(status_counts.get("started_empty", 0)),
        "pending_tasks": int(status_counts.get("pending", 0)),
        "reviewer_counts": dict(reviewer_counts),
        "labels_present_counts": dict(label_counts),
        "pending_pots": pending_pots,
        "unassigned_export_files": list(unassigned_files),
    }


def render_markdown(
    seed_csv: Path,
    exports_dir: Path,
    manifest_csv: Path,
    summary_json: Path,
    summary: Dict[str, object],
) -> str:
    lines = [
        "# V1.10 Seed Annotation Status",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        "",
        "## Inputs",
        "",
        f"- Seed CSV: `{seed_csv}`",
        f"- Exports dir: `{exports_dir}`",
        f"- Manifest CSV: `{manifest_csv}`",
        f"- Summary JSON: `{summary_json}`",
        "- Tracker page: `tracker/v1-10-seed-annotation-status.html`",
        "",
        "## Snapshot",
        "",
        f"- Expected tasks: `{summary.get('expected_tasks', 0)}`",
        f"- Completed tasks: `{summary.get('completed_tasks', 0)}`",
        f"- Started-but-empty tasks: `{summary.get('started_empty_tasks', 0)}`",
        f"- Pending tasks: `{summary.get('pending_tasks', 0)}`",
        f"- Unassigned export files: `{len(summary.get('unassigned_export_files', []))}`",
        "",
        "## Pending Pots",
        "",
    ]
    pending_pots = summary.get("pending_pots", [])
    if isinstance(pending_pots, list) and pending_pots:
        for pot_id in pending_pots:
            lines.append(f"- `{pot_id}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Label Coverage",
            "",
            "| Label | Tasks Present |",
            "|---|---:|",
        ]
    )
    label_counts = summary.get("labels_present_counts", {})
    if isinstance(label_counts, dict) and label_counts:
        for label, count in sorted(label_counts.items()):
            lines.append(f"| `{label}` | {count} |")
    else:
        lines.append("| `n/a` | 0 |")

    lines.extend(
        [
            "",
            "## Reviewer Coverage",
            "",
            "| Reviewer | Tasks |",
            "|---|---:|",
        ]
    )
    reviewer_counts = summary.get("reviewer_counts", {})
    if isinstance(reviewer_counts, dict) and reviewer_counts:
        for reviewer, count in sorted(reviewer_counts.items()):
            lines.append(f"| `{reviewer}` | {count} |")
    else:
        lines.append("| `n/a` | 0 |")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "1. Drop exported JSON files from `tracker/single-photo-seed-labeler.html` into the exports directory.",
            "2. Re-run this script to refresh the manifest and summary.",
            "3. Promote the completed box tasks into a later polygon-mask or segmentation training workflow.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-csv",
        type=Path,
        default=Path("data/research/v1_10/mask_label_seed_set.csv"),
        help="Seed set CSV built from the v1.10 queue.",
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=Path("data/research/v1_10/labeler_exports"),
        help="Directory containing exported JSON files from the task-aware labeler.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/v1_10/seed_label_annotation_manifest.csv"),
        help="Output manifest CSV path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_10/seed_label_annotation_summary.json"),
        help="Output summary JSON path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.10-SEED-LABEL-ANNOTATION-STATUS.md"),
        help="Output markdown status report path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    seed_rows = read_csv_rows(args.seed_csv)
    latest_by_task, export_counts, unassigned_files = collect_exports(args.exports_dir)
    manifest_rows = build_manifest(seed_rows, latest_by_task, export_counts)
    summary = build_summary(manifest_rows, unassigned_files)

    fieldnames = [
        "task_key",
        "pot_id",
        "variety_name",
        "seed_rank",
        "queue_priority_rank",
        "source_asset_id",
        "annotation_status",
        "export_count",
        "latest_export_json_path",
        "latest_saved_at_utc",
        "reviewer",
        "box_count",
        "labels_present",
        "image_src",
        "crop_path",
        "overlay_path",
        "annotate_url",
        "reference_url",
        "next_action",
    ]
    write_csv_rows(args.output_csv, fieldnames, manifest_rows)
    write_json(args.output_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_markdown(args.seed_csv, args.exports_dir, args.output_csv, args.output_json, summary),
        encoding="utf-8",
    )

    print(f"seed_csv={args.seed_csv}")
    print(f"exports_dir={args.exports_dir}")
    print(f"expected_tasks={summary['expected_tasks']}")
    print(f"completed_tasks={summary['completed_tasks']}")
    print(f"pending_tasks={summary['pending_tasks']}")
    print(f"output_csv={args.output_csv}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
