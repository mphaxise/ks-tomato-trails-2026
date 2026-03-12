#!/usr/bin/env python3
"""Build a v1.10 seed-annotation status HTML page from the manifest and summary."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


STATUS_ORDER = {
    "pending": 0,
    "started_empty": 1,
    "completed": 2,
}

STATUS_LABELS = {
    "pending": "Pending",
    "started_empty": "Started, Empty",
    "completed": "Completed",
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
    if text.startswith("./"):
        return text
    if text.startswith("assets/"):
        return f"./{text}"
    if text.startswith("/"):
        return text
    return text


def rank_value(value: str) -> int:
    cleaned = (value or "").strip()
    return int(cleaned) if cleaned.isdigit() else 10_000


def pot_sort_key(pot_id: str) -> Tuple[int, str]:
    cleaned = (pot_id or "").strip().upper()
    if cleaned.endswith("T") and cleaned[:-1].isdigit():
        return int(cleaned[:-1]), cleaned
    return 10_000, cleaned


def labels_for_row(row: Dict[str, str]) -> List[str]:
    return [label.strip() for label in str(row.get("labels_present", "") or "").split("|") if label.strip()]


def group_rows(manifest_rows: Sequence[Dict[str, str]]) -> List[Tuple[str, List[Dict[str, str]]]]:
    sorted_rows = sorted(
        manifest_rows,
        key=lambda row: (
            STATUS_ORDER.get(str(row.get("annotation_status", "") or "").strip(), 99),
            rank_value(str(row.get("seed_rank", "") or "")),
            pot_sort_key(str(row.get("pot_id", "") or "")),
        ),
    )
    groups: List[Tuple[str, List[Dict[str, str]]]] = []
    for status in ("pending", "started_empty", "completed"):
        rows = [
            row
            for row in sorted_rows
            if str(row.get("annotation_status", "") or "").strip() == status
        ]
        groups.append((status, rows))
    return groups


def build_card(row: Dict[str, str]) -> str:
    status = str(row.get("annotation_status", "") or "").strip() or "pending"
    status_label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    pot_id = str(row.get("pot_id", "") or "").strip()
    variety = str(row.get("variety_name", "") or "").strip()
    seed_rank = str(row.get("seed_rank", "") or "").strip() or "n/a"
    queue_rank = str(row.get("queue_priority_rank", "") or "").strip() or "n/a"
    export_count = str(row.get("export_count", "") or "").strip() or "0"
    box_count = str(row.get("box_count", "") or "").strip() or "0"
    reviewer = str(row.get("reviewer", "") or "").strip() or "n/a"
    latest_saved = str(row.get("latest_saved_at_utc", "") or "").strip() or "n/a"
    next_action = str(row.get("next_action", "") or "").strip()
    preview_image = path_for_page(str(row.get("image_src", "") or "").strip())
    crop_path = path_for_page(str(row.get("crop_path", "") or "").strip())
    overlay_path = path_for_page(str(row.get("overlay_path", "") or "").strip())
    annotate_url = path_for_page(str(row.get("annotate_url", "") or "").strip())
    reference_url = path_for_page(str(row.get("reference_url", "") or "").strip())
    latest_export_json_path = str(row.get("latest_export_json_path", "") or "").strip()
    expected_pot_id = str(row.get("expected_pot_id", "") or "").strip() or pot_id
    pot_id_verdict = str(row.get("pot_id_verdict", "") or "").strip() or "pending"
    corrected_pot_id = str(row.get("corrected_pot_id", "") or "").strip()
    effective_pot_id = str(row.get("effective_pot_id", "") or "").strip() or expected_pot_id
    pot_id_note = str(row.get("pot_id_note", "") or "").strip()
    pot_id_mismatch = str(row.get("pot_id_mismatch", "") or "").strip().lower() in {"yes", "true", "1"}
    labels = labels_for_row(row)

    preview_html = (
        f"<img src='{attr_escape(preview_image)}' alt='Preview for {attr_escape(pot_id)}' loading='lazy' />"
        if preview_image
        else "<div class='missing'>No crop preview yet</div>"
    )
    label_html = (
        "".join(f"<li>{html_escape(label)}</li>" for label in labels)
        if labels
        else "<li>none yet</li>"
    )

    links: List[str] = []
    if annotate_url:
        links.append(f"<a href='{attr_escape(annotate_url)}'>Annotate Crop</a>")
    if reference_url:
        links.append(
            f"<a href='{attr_escape(reference_url)}' target='_blank' rel='noreferrer'>Reference Photo</a>"
        )
    if crop_path:
        links.append(
            f"<a href='{attr_escape(crop_path)}' target='_blank' rel='noreferrer'>Crop</a>"
        )
    if overlay_path:
        links.append(
            f"<a href='{attr_escape(overlay_path)}' target='_blank' rel='noreferrer'>Overlay</a>"
        )
    link_html = "".join(links) if links else "<span class='empty-links'>No page links available.</span>"

    export_path_html = (
        f"<code class='mono'>{html_escape(latest_export_json_path)}</code>" if latest_export_json_path else "<span class='muted'>none</span>"
    )
    identity_html = (
        "<div class='identity-alert'>"
        f"<p><strong>Pot-ID mismatch:</strong> task expected <code>{html_escape(expected_pot_id)}</code> but annotator marked <code>{html_escape(corrected_pot_id or 'n/a')}</code>.</p>"
        f"<p>{html_escape(pot_id_note or 'Resolve identity before using this task for training or follow-up.')}</p>"
        "</div>"
        if pot_id_mismatch
        else ""
    )

    return (
        f"<article class='card status-{attr_escape(status)}{' identity-mismatch' if pot_id_mismatch else ''}'>"
        "<header class='card-head'>"
        f"<p class='eyebrow'>Seed {html_escape(seed_rank)} <span>Queue {html_escape(queue_rank)}</span></p>"
        f"<div class='title-row'><h3>{html_escape(pot_id)} <span>{html_escape(variety)}</span></h3>"
        f"<span class='status-pill {attr_escape(status)}'>{html_escape(status_label)}</span></div>"
        "</header>"
        "<div class='card-grid'>"
        f"<figure class='preview'>{preview_html}</figure>"
        "<div class='details'>"
        "<dl class='stats'>"
        f"<div><dt>Exports</dt><dd>{html_escape(export_count)}</dd></div>"
        f"<div><dt>Boxes</dt><dd>{html_escape(box_count)}</dd></div>"
        f"<div><dt>Reviewer</dt><dd>{html_escape(reviewer)}</dd></div>"
        f"<div><dt>Latest Save</dt><dd>{html_escape(latest_saved)}</dd></div>"
        f"<div><dt>Expected Pot</dt><dd>{html_escape(expected_pot_id or 'n/a')}</dd></div>"
        f"<div><dt>ID Verdict</dt><dd>{html_escape(pot_id_verdict.replace('_', ' ') or 'n/a')}</dd></div>"
        f"<div><dt>Effective Pot</dt><dd>{html_escape(effective_pot_id or 'n/a')}</dd></div>"
        "</dl>"
        f"{identity_html}"
        "<div class='labels-block'>"
        "<p class='subhead'>Labels Present</p>"
        f"<ul class='labels'>{label_html}</ul>"
        "</div>"
        f"<p class='next-action'>{html_escape(next_action)}</p>"
        f"<p class='links'>{link_html}</p>"
        "<div class='export-block'>"
        "<p class='subhead'>Latest Export JSON</p>"
        f"{export_path_html}"
        "</div>"
        "</div>"
        "</div>"
        "</article>"
    )


def build_page(
    manifest_rows: Sequence[Dict[str, str]],
    summary: Dict[str, object],
    source_manifest_csv: Path,
    source_summary_json: Path,
) -> str:
    generated_at = str(summary.get("generated_at_utc", "") or datetime.now(timezone.utc).isoformat())
    expected_tasks = int(summary.get("expected_tasks", 0) or 0)
    completed_tasks = int(summary.get("completed_tasks", 0) or 0)
    started_empty_tasks = int(summary.get("started_empty_tasks", 0) or 0)
    pending_tasks = int(summary.get("pending_tasks", 0) or 0)
    pot_id_mismatch_tasks = int(summary.get("pot_id_mismatch_tasks", 0) or 0)
    unassigned_files = summary.get("unassigned_export_files", [])
    if not isinstance(unassigned_files, list):
        unassigned_files = []
    mismatch_rows = summary.get("pot_id_mismatches", [])
    if not isinstance(mismatch_rows, list):
        mismatch_rows = []

    sections: List[str] = []
    for status, rows in group_rows(manifest_rows):
        label = STATUS_LABELS.get(status, status.replace("_", " ").title())
        cards = "".join(build_card(row) for row in rows) if rows else "<p class='empty'>No tasks in this status.</p>"
        sections.append(
            "<section class='status-section'>"
            f"<div class='section-head'><h2>{html_escape(label)} ({len(rows)})</h2>"
            f"<p>{html_escape('Tasks waiting for the next action.' if status != 'completed' else 'Tasks with usable box exports already captured.')}</p></div>"
            f"<div class='cards'>{cards}</div>"
            "</section>"
        )

    unassigned_html = (
        "<div class='callout warn'>"
        "<h2>Unassigned Export Files</h2>"
        "<p>These JSON files were found without a matching task key and need manual review.</p>"
        "<ul class='unassigned'>"
        + "".join(f"<li><code>{html_escape(str(path))}</code></li>" for path in unassigned_files)
        + "</ul></div>"
    ) if unassigned_files else ""
    mismatch_html = (
        "<div class='callout warn'>"
        "<h2>Pot-ID Mismatches</h2>"
        "<p>These tasks were annotated with a corrected pot ID and should be resolved before downstream training or metric updates.</p>"
        "<ul class='unassigned'>"
        + "".join(
            f"<li><code>{html_escape(str(row.get('task_key', '') or ''))}</code>: "
            f"{html_escape(str(row.get('expected_pot_id', '') or ''))} -> {html_escape(str(row.get('corrected_pot_id', '') or ''))}</li>"
            for row in mismatch_rows
            if isinstance(row, dict)
        )
        + "</ul></div>"
    ) if mismatch_rows else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1.10 Seed Annotation Status</title>
  <style>
    :root {{
      --bg: #efe7d8;
      --card: #fffdf8;
      --ink: #21312d;
      --line: #d7ccb8;
      --leaf: #2f6947;
      --amber: #8b5c23;
      --tomato: #8a2f2f;
      --sky: #35597f;
      --muted: #5c6b66;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(900px 420px at 115% -10%, #ded3bc 0%, transparent 62%),
        radial-gradient(900px 420px at -12% 110%, #e5dbc6 0%, transparent 62%),
        linear-gradient(145deg, #f1ebde, #ebe1cf);
    }}
    main {{
      max-width: 1240px;
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
      font-size: clamp(1.7rem, 3.6vw, 2.6rem);
      margin-bottom: 10px;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 78ch;
      line-height: 1.45;
    }}
    .small {{
      font-size: 0.84rem;
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
      font-size: 1.3rem;
      font-weight: 700;
    }}
    .callout {{
      margin-bottom: 16px;
    }}
    .callout.warn {{
      border-color: #e5c7b2;
      background: #fff7f0;
    }}
    .callout h2 {{
      margin-bottom: 8px;
      font-size: 1.15rem;
    }}
    .callout p {{
      margin: 0 0 8px;
      color: var(--muted);
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
    .status-pending {{
      border-left: 6px solid var(--amber);
    }}
    .status-started_empty {{
      border-left: 6px solid var(--sky);
    }}
    .status-completed {{
      border-left: 6px solid var(--leaf);
    }}
    .identity-mismatch {{
      border-right: 6px solid var(--tomato);
    }}
    .card-head {{
      margin-bottom: 10px;
    }}
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
    }}
    .status-pill.pending {{
      background: #f5ead6;
      color: #7a531d;
    }}
    .status-pill.started_empty {{
      background: #dce9f7;
      color: #2a5278;
    }}
    .status-pill.completed {{
      background: #dcedde;
      color: #275b3e;
    }}
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
    .identity-alert {{
      margin-top: 12px;
      padding: 10px;
      border: 1px solid #efc7c7;
      border-radius: 12px;
      background: #fff3f3;
    }}
    .identity-alert p {{
      margin: 0 0 6px;
      color: #6a3737;
      line-height: 1.45;
    }}
    .identity-alert p:last-child {{
      margin-bottom: 0;
    }}
    .labels, .unassigned {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    .next-action {{
      margin: 12px 0;
      font-size: 0.95rem;
      line-height: 1.45;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 12px;
    }}
    .links a, .empty-links {{
      text-decoration: none;
      border: 1px solid #dacfbf;
      background: #faf7ee;
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .mono {{
      display: inline-block;
      max-width: 100%;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.76rem;
      background: #f6f1e5;
      border-radius: 8px;
      padding: 7px 8px;
    }}
    .muted {{
      color: var(--muted);
    }}
    .sources {{
      margin-top: 16px;
    }}
    .sources p {{
      margin: 8px 0;
      color: var(--muted);
    }}
    .sources code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.82rem;
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
      <h1>V1.10 Seed Annotation Status</h1>
      <p>This page closes the loop between the v1.10 seed pack, the task-aware one-photo labeler, and the next mask-training queue. Drop exported JSON files into <code>data/research/v1_10/labeler_exports/</code>, refresh the collector, and use this page to see which seed tasks are still pending, started, or complete before handing them into the v1.11 ingest layer.</p>
      <p class="small"><a href="./v1-11-seed-annotation-ingest.html">Open the v1.11 seed annotation ingest board</a> once completed tasks exist.</p>
      <p class="small">Generated (UTC): <code>{html_escape(generated_at)}</code></p>
      <dl class="summary">
        <div><dt>Expected Tasks</dt><dd>{expected_tasks}</dd></div>
        <div><dt>Pending</dt><dd>{pending_tasks}</dd></div>
        <div><dt>Started, Empty</dt><dd>{started_empty_tasks}</dd></div>
        <div><dt>Completed</dt><dd>{completed_tasks}</dd></div>
        <div><dt>Pot-ID Mismatches</dt><dd>{pot_id_mismatch_tasks}</dd></div>
        <div><dt>Unassigned Exports</dt><dd>{len(unassigned_files)}</dd></div>
      </dl>
    </section>

    {mismatch_html}
    {unassigned_html}

    {''.join(sections)}

    <section class="sources">
      <h2>Refresh Inputs</h2>
      <p>Manifest source: <code>{html_escape(str(source_manifest_csv))}</code></p>
      <p>Summary source: <code>{html_escape(str(source_summary_json))}</code></p>
      <p>Collector: <code>python3 scripts/v110_seed_label_annotation_status.py</code></p>
      <p>Page builder: <code>python3 scripts/build_v110_seed_annotation_status_page.py</code></p>
      <p>Next stage collector: <code>python3 scripts/v111_seed_annotation_ingest.py</code></p>
      <p>Next stage page: <code>python3 scripts/build_v111_seed_annotation_ingest_page.py</code></p>
    </section>
  </main>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=Path("data/research/v1_10/seed_label_annotation_manifest.csv"),
        help="Manifest CSV built from task-aware seed-label exports.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/research/v1_10/seed_label_annotation_summary.json"),
        help="Summary JSON built from task-aware seed-label exports.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/v1-10-seed-annotation-status.html"),
        help="Output tracker HTML page.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    manifest_rows = read_csv_rows(args.manifest_csv)
    summary = read_json_optional(args.summary_json)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(
        build_page(
            manifest_rows=manifest_rows,
            summary=summary,
            source_manifest_csv=args.manifest_csv,
            source_summary_json=args.summary_json,
        ),
        encoding="utf-8",
    )

    print(f"manifest_csv={args.manifest_csv}")
    print(f"summary_json={args.summary_json}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
