#!/usr/bin/env python3
"""Build a v1.11 seed-annotation ingest tracker page."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

STATUS_ORDER = {
    "ready_for_training": 0,
    "missing_required_labels": 1,
    "pot_id_mismatch": 2,
    "missing_local_image": 3,
    "missing_export": 4,
    "invalid_export": 5,
    "started_empty": 6,
    "pending_annotation": 7,
}

STATUS_LABELS = {
    "ready_for_training": "Ready For Training",
    "missing_required_labels": "Missing Required Labels",
    "pot_id_mismatch": "Pot-ID Mismatch",
    "missing_local_image": "Missing Local Image",
    "missing_export": "Missing Export",
    "invalid_export": "Invalid Export",
    "started_empty": "Started, Empty",
    "pending_annotation": "Pending Annotation",
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def read_json_optional(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def html_escape(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def attr_escape(value: str) -> str:
    return html_escape(value).replace("'", "&#39;")


def path_for_page(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("./") or text.startswith("../"):
        return text
    if text.startswith("assets/"):
        return f"./{text}"
    if text.startswith("/"):
        return text
    return text


def rank_value(value: str) -> int:
    cleaned = (value or "").strip()
    return int(cleaned) if cleaned.isdigit() else 10_000


def group_rows(task_rows: Sequence[Dict[str, str]]) -> List[Tuple[str, List[Dict[str, str]]]]:
    sorted_rows = sorted(
        task_rows,
        key=lambda row: (
            STATUS_ORDER.get(str(row.get("ingest_status", "") or "").strip(), 99),
            rank_value(str(row.get("seed_rank", "") or "")),
            str(row.get("pot_id", "") or "").strip().upper(),
        ),
    )
    groups: List[Tuple[str, List[Dict[str, str]]]] = []
    for status in (
        "ready_for_training",
        "missing_required_labels",
        "pot_id_mismatch",
        "missing_local_image",
        "invalid_export",
        "started_empty",
        "pending_annotation",
        "missing_export",
    ):
        rows = [
            row
            for row in sorted_rows
            if str(row.get("ingest_status", "") or "").strip() == status
        ]
        groups.append((status, rows))
    return groups


def build_card(row: Dict[str, str]) -> str:
    status = str(row.get("ingest_status", "") or "").strip() or "pending_annotation"
    status_label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    pot_id = str(row.get("pot_id", "") or "").strip()
    variety = str(row.get("variety_name", "") or "").strip()
    seed_rank = str(row.get("seed_rank", "") or "").strip() or "n/a"
    queue_rank = str(row.get("queue_priority_rank", "") or "").strip() or "n/a"
    labels_present = str(row.get("labels_present", "") or "").strip()
    required_missing = str(row.get("required_labels_missing", "") or "").strip()
    reviewer = str(row.get("reviewer", "") or "").strip() or "n/a"
    box_count = str(row.get("box_count", "") or "").strip() or "0"
    yolo_box_count = str(row.get("yolo_box_count", "") or "").strip() or "0"
    ready_for_training = str(row.get("ready_for_training", "") or "").strip().lower() in {"yes", "true", "1"}
    next_step = str(row.get("next_step", "") or "").strip()
    image_path = path_for_page(str(row.get("image_page_path", "") or "").strip())
    crop_path = path_for_page(str(row.get("crop_path", "") or "").strip())
    overlay_path = path_for_page(str(row.get("overlay_path", "") or "").strip())
    annotate_url = path_for_page(str(row.get("annotate_url", "") or "").strip())
    reference_url = path_for_page(str(row.get("reference_url", "") or "").strip())
    yolo_label_path = str(row.get("yolo_label_path", "") or "").strip()
    expected_pot_id = str(row.get("expected_pot_id", "") or "").strip() or pot_id
    effective_pot_id = str(row.get("effective_pot_id", "") or "").strip() or expected_pot_id

    label_badges = (
        "".join(
            f"<li>{html_escape(label)}</li>"
            for label in labels_present.split("|")
            if label.strip()
        )
        if labels_present
        else "<li>none yet</li>"
    )
    missing_html = (
        ", ".join(html_escape(label) for label in required_missing.split("|") if label.strip())
        if required_missing
        else "none"
    )
    preview_html = (
        f"<img src='{attr_escape(image_path)}' alt='Preview for {attr_escape(pot_id)}' loading='lazy' />"
        if image_path
        else "<div class='missing'>No preview image</div>"
    )

    links: List[str] = []
    if annotate_url:
        links.append(f"<a href='{attr_escape(annotate_url)}'>Annotate</a>")
    if reference_url:
        links.append(f"<a href='{attr_escape(reference_url)}' target='_blank' rel='noreferrer'>Reference</a>")
    if crop_path:
        links.append(f"<a href='{attr_escape(crop_path)}' target='_blank' rel='noreferrer'>Crop</a>")
    if overlay_path:
        links.append(f"<a href='{attr_escape(overlay_path)}' target='_blank' rel='noreferrer'>Overlay</a>")
    link_html = " | ".join(links) if links else "No page links available."

    return (
        f"<article class='card status-{attr_escape(status)}'>"
        "<header class='card-head'>"
        f"<p class='eyebrow'>Seed {html_escape(seed_rank)} <span>Queue {html_escape(queue_rank)}</span></p>"
        f"<div class='title-row'><h3>{html_escape(pot_id)} <span>{html_escape(variety)}</span></h3>"
        f"<span class='status-pill {attr_escape(status)}'>{html_escape(status_label)}</span></div>"
        "</header>"
        "<div class='card-grid'>"
        f"<figure class='preview'>{preview_html}</figure>"
        "<div class='details'>"
        "<dl class='stats'>"
        f"<div><dt>Boxes</dt><dd>{html_escape(box_count)}</dd></div>"
        f"<div><dt>YOLO Rows</dt><dd>{html_escape(yolo_box_count)}</dd></div>"
        f"<div><dt>Reviewer</dt><dd>{html_escape(reviewer)}</dd></div>"
        f"<div><dt>Ready</dt><dd>{'yes' if ready_for_training else 'no'}</dd></div>"
        f"<div><dt>Expected Pot</dt><dd>{html_escape(expected_pot_id)}</dd></div>"
        f"<div><dt>Effective Pot</dt><dd>{html_escape(effective_pot_id)}</dd></div>"
        "</dl>"
        "<div class='labels-block'>"
        "<p class='subhead'>Labels Present</p>"
        f"<ul class='labels'>{label_badges}</ul>"
        "</div>"
        "<div class='labels-block'>"
        "<p class='subhead'>Missing Required Labels</p>"
        f"<p class='missing-list'>{missing_html}</p>"
        "</div>"
        f"<p class='next-action'>{html_escape(next_step)}</p>"
        f"<p class='links'>{link_html}</p>"
        "<div class='export-block'>"
        "<p class='subhead'>YOLO Label File</p>"
        f"<code>{html_escape(yolo_label_path or 'none')}</code>"
        "</div>"
        "</div>"
        "</div>"
        "</article>"
    )


def build_page(
    task_rows: Sequence[Dict[str, str]],
    summary: Dict[str, object],
    source_task_csv: Path,
    source_summary_json: Path,
) -> str:
    generated_at = str(summary.get("generated_at_utc", "") or datetime.now(timezone.utc).isoformat())
    total_tasks = int(summary.get("total_tasks", 0) or 0)
    ready_for_training = int(summary.get("ready_for_training_tasks", 0) or 0)
    completed_tasks = int(summary.get("completed_annotation_tasks", 0) or 0)
    pending_tasks = int(summary.get("pending_annotation_tasks", 0) or 0)
    missing_required = int(summary.get("missing_required_label_tasks", 0) or 0)
    mismatch_tasks = int(summary.get("pot_id_mismatch_tasks", 0) or 0)
    total_boxes = int(summary.get("total_boxes_ingested", 0) or 0)
    recommended = str(summary.get("recommended_next_step", "") or "").strip()
    required_counts = summary.get("required_label_task_counts", {})
    if not isinstance(required_counts, dict):
        required_counts = {}

    sections: List[str] = []
    for status, rows in group_rows(task_rows):
        label = STATUS_LABELS.get(status, status.replace("_", " ").title())
        cards = "".join(build_card(row) for row in rows) if rows else "<p class='empty'>No tasks in this status.</p>"
        sections.append(
            "<section class='status-section'>"
            f"<div class='section-head'><h2>{html_escape(label)} ({len(rows)})</h2>"
            f"<p>{html_escape('Training-ready tasks can move into a first indoor detector baseline.' if status == 'ready_for_training' else 'These tasks still block or delay the training handoff.')}</p></div>"
            f"<div class='cards'>{cards}</div>"
            "</section>"
        )

    required_rows = "".join(
        f"<tr><td><code>{html_escape(label)}</code></td><td>{int(required_counts.get(label, 0) or 0)}</td></tr>"
        for label in ("pot_region", "pot_interior", "plant_region")
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1.11 Seed Annotation Ingest</title>
  <style>
    :root {{
      --bg: #efe8d7;
      --card: #fffdf8;
      --ink: #21312d;
      --line: #d8ccb8;
      --leaf: #2f6947;
      --amber: #8b5c23;
      --tomato: #8a2f2f;
      --sky: #35597f;
      --slate: #5d6e77;
      --muted: #5c6b66;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(900px 420px at 115% -10%, #dfd4bf 0%, transparent 62%),
        radial-gradient(900px 420px at -12% 110%, #e8dfcc 0%, transparent 62%),
        linear-gradient(145deg, #f2ebde, #e9dfcd);
    }}
    main {{
      max-width: 1260px;
      margin: 0 auto;
      padding: 28px 16px 56px;
    }}
    .hero, .status-section, .callout, .sources {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 30px rgba(53, 44, 20, 0.05);
    }}
    .hero {{
      margin-bottom: 16px;
    }}
    h1, h2, h3 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
    }}
    h1 {{
      font-size: clamp(1.7rem, 3.6vw, 2.5rem);
      margin-bottom: 10px;
    }}
    .hero p {{
      margin: 0 0 8px;
      color: var(--muted);
      max-width: 76ch;
      line-height: 1.45;
    }}
    .summary {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }}
    .summary div {{
      border: 1px solid #e8dece;
      border-radius: 14px;
      background: #faf6ed;
      padding: 12px;
    }}
    .summary dt {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #697974;
    }}
    .summary dd {{
      margin: 8px 0 0;
      font-size: 1.25rem;
      font-weight: 700;
    }}
    .callout {{
      margin-bottom: 16px;
    }}
    .callout h2 {{
      margin-bottom: 8px;
      font-size: 1.15rem;
    }}
    .callout p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .required-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 0.88rem;
    }}
    .required-table th, .required-table td {{
      border-bottom: 1px solid #ece4d4;
      text-align: left;
      padding: 8px 6px;
    }}
    .required-table th {{
      background: #f7f2e8;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #667772;
    }}
    .status-section {{
      margin-bottom: 16px;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      margin-bottom: 12px;
    }}
    .section-head p {{
      margin: 0;
      color: var(--muted);
      max-width: 48ch;
      text-align: right;
    }}
    .cards {{
      display: grid;
      gap: 12px;
    }}
    .card {{
      border: 1px solid #e9dfcf;
      border-radius: 16px;
      background: #fffefb;
      padding: 14px;
    }}
    .status-ready_for_training {{ border-left: 6px solid var(--leaf); }}
    .status-missing_required_labels {{ border-left: 6px solid var(--amber); }}
    .status-pot_id_mismatch {{ border-left: 6px solid var(--tomato); }}
    .status-missing_local_image, .status-invalid_export, .status-missing_export {{ border-left: 6px solid var(--slate); }}
    .status-started_empty, .status-pending_annotation {{ border-left: 6px solid var(--sky); }}
    .eyebrow {{
      margin: 0 0 6px;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #6a7b76;
    }}
    .eyebrow span {{
      margin-left: 8px;
      color: #8a5c23;
    }}
    .title-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}
    h3 {{
      font-size: 1.3rem;
    }}
    h3 span {{
      display: inline-block;
      margin-left: 8px;
      font-size: 0.95rem;
      color: #5c6c66;
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
      font-weight: 600;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: #edf2f5;
      color: #35597f;
    }}
    .status-pill.ready_for_training {{ background: #dcedde; color: #275b3e; }}
    .status-pill.missing_required_labels {{ background: #f5ead6; color: #7a531d; }}
    .status-pill.pot_id_mismatch {{ background: #f7dddd; color: #7b3030; }}
    .status-pill.pending_annotation, .status-pill.started_empty {{ background: #dce9f7; color: #2a5278; }}
    .card-grid {{
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 14px;
      align-items: start;
    }}
    .preview {{
      margin: 0;
      border: 1px solid #eadfce;
      border-radius: 14px;
      background: #f5efe2;
      min-height: 210px;
      overflow: hidden;
      display: grid;
      place-items: center;
    }}
    .preview img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .missing {{
      color: #6f7f79;
      font-size: 0.9rem;
      padding: 20px;
      text-align: center;
    }}
    .stats {{
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
      gap: 8px;
    }}
    .stats div {{
      border: 1px solid #efe5d5;
      border-radius: 12px;
      background: #faf7ef;
      padding: 10px;
    }}
    .stats dt {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #6c7b76;
    }}
    .stats dd {{
      margin: 6px 0 0;
      font-size: 0.95rem;
      font-weight: 700;
      word-break: break-word;
    }}
    .subhead {{
      margin: 12px 0 8px;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #6c7b76;
    }}
    .labels {{
      margin: 0;
      padding-left: 18px;
      color: #3f4f4a;
    }}
    .labels li {{
      margin-bottom: 4px;
    }}
    .missing-list, .next-action, .links {{
      margin: 0 0 8px;
      color: #4f5f5a;
      line-height: 1.45;
    }}
    .links a {{
      color: #35597f;
      text-decoration: none;
      font-weight: 700;
    }}
    .export-block code, .sources code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.8rem;
      word-break: break-word;
    }}
    .sources {{
      margin-top: 16px;
    }}
    .sources p {{
      margin: 8px 0;
      color: var(--muted);
    }}
    .empty {{
      margin: 0;
      color: var(--muted);
    }}
    @media (max-width: 860px) {{
      .section-head {{
        display: block;
      }}
      .section-head p {{
        margin-top: 6px;
        text-align: left;
      }}
      .card-grid {{
        grid-template-columns: 1fr;
      }}
      .title-row {{
        display: block;
      }}
      .status-pill {{
        margin-top: 8px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>V1.11 Seed Annotation Ingest</h1>
      <p>This page sits between the v1.10 seed annotation status board and the first custom indoor detector baseline. It normalizes completed exports into task-ready training rows, checks for required labels, and writes YOLO-format label files only when the annotations are complete enough to trust.</p>
      <p>Generated (UTC): <code>{html_escape(generated_at)}</code></p>
      <dl class="summary">
        <div><dt>Total Tasks</dt><dd>{total_tasks}</dd></div>
        <div><dt>Completed</dt><dd>{completed_tasks}</dd></div>
        <div><dt>Ready For Training</dt><dd>{ready_for_training}</dd></div>
        <div><dt>Pending</dt><dd>{pending_tasks}</dd></div>
        <div><dt>Missing Required Labels</dt><dd>{missing_required}</dd></div>
        <div><dt>Pot-ID Mismatches</dt><dd>{mismatch_tasks}</dd></div>
        <div><dt>Total Boxes</dt><dd>{total_boxes}</dd></div>
      </dl>
    </section>

    <section class="callout">
      <h2>Recommended Next Step</h2>
      <p>{html_escape(recommended)}</p>
      <table class="required-table">
        <thead>
          <tr><th>Required Label</th><th>Tasks Present</th></tr>
        </thead>
        <tbody>
          {required_rows}
        </tbody>
      </table>
    </section>

    {''.join(sections)}

    <section class="sources">
      <h2>Refresh Inputs</h2>
      <p>Task ingest source: <code>{html_escape(str(source_task_csv))}</code></p>
      <p>Summary source: <code>{html_escape(str(source_summary_json))}</code></p>
      <p>Status collector: <code>python3 scripts/v110_seed_label_annotation_status.py</code></p>
      <p>Status page: <code>python3 scripts/build_v110_seed_annotation_status_page.py</code></p>
      <p>Ingest collector: <code>python3 scripts/v111_seed_annotation_ingest.py</code></p>
      <p>Ingest page: <code>python3 scripts/build_v111_seed_annotation_ingest_page.py</code></p>
    </section>
  </main>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task-manifest-csv",
        type=Path,
        default=Path("data/research/v1_11/seed_annotation_ingest_manifest.csv"),
        help="Task-level ingest manifest CSV.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/research/v1_11/seed_annotation_ingest_summary.json"),
        help="Ingest summary JSON.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/v1-11-seed-annotation-ingest.html"),
        help="Output tracker HTML page.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    task_rows = read_csv_rows(args.task_manifest_csv)
    summary = read_json_optional(args.summary_json)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(
        build_page(
            task_rows=task_rows,
            summary=summary,
            source_task_csv=args.task_manifest_csv,
            source_summary_json=args.summary_json,
        ),
        encoding="utf-8",
    )

    print(f"task_manifest_csv={args.task_manifest_csv}")
    print(f"summary_json={args.summary_json}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
