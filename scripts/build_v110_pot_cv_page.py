#!/usr/bin/env python3
"""Build a visual HTML page for v1.10 pot-anchored CV research outputs."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


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
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def attr_escape(value: str) -> str:
    return html_escape(value).replace("'", "&#39;")


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


def pot_sort_key(row: Dict[str, str]) -> Tuple[int, str]:
    pot_id = (row.get("pot_id", "") or "").strip().upper()
    if pot_id.endswith("T") and pot_id[:-1].isdigit():
        return (int(pot_id[:-1]), pot_id)
    return (10_000, pot_id)


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


def normalize_readiness(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned in {"high", "moderate", "low"}:
        return cleaned
    return "unknown"


def build_summary_cards(summary: Dict[str, object]) -> str:
    readiness = summary.get("tracking_readiness_counts")
    next_steps = summary.get("next_step_counts")
    if not isinstance(readiness, dict):
        readiness = {}
    if not isinstance(next_steps, dict):
        next_steps = {}
    top_next = ""
    if next_steps:
        top_next = sorted(next_steps.items(), key=lambda item: (-int(item[1]), item[0]))[0][0]

    cards = [
        ("Pots Analyzed", str(int(summary.get("pots_analyzed", 0) or 0)), "accent"),
        ("Ready For Masks", str(int(summary.get("ready_for_mask_labels_count", 0) or 0)), "high"),
        (
            "Avg Focus Score",
            f"{float(summary.get('average_focus_score', 0.0) or 0.0):.2f}",
            "accent",
        ),
        (
            "Avg In-Pot Spill",
            f"{float(summary.get('average_spill_in_pot_ratio', summary.get('average_neighbor_spill_ratio', 0.0)) or 0.0) * 100:.1f}%",
            "low",
        ),
        (
            "Growth Baseline Coverage",
            f"{float(summary.get('growth_delta_availability_ratio', 0.0) or 0.0) * 100:.1f}%",
            "moderate",
        ),
        ("Top Next Step", top_next or "n/a", "action"),
    ]
    card_html = "\n".join(
        (
            "<article class='metric-card'>"
            f"<p class='metric-label'>{html_escape(label)}</p>"
            f"<p class='metric-value {css_class}'>{html_escape(value)}</p>"
            "</article>"
        )
        for label, value, css_class in cards
    )

    generated = str(summary.get("created_at", "") or datetime.now(timezone.utc).isoformat())
    run_id = str(summary.get("run_id", "") or "")
    run_date = str(summary.get("run_date", "") or "")
    high = int(readiness.get("high", 0) or 0)
    moderate = int(readiness.get("moderate", 0) or 0)
    low = int(readiness.get("low", 0) or 0)

    return (
        "<section class='hero'>"
        "<div>"
        "<p class='eyebrow'>Version 1.10 Research</p>"
        "<h1>Pot-Anchored Indoor CV Viewer</h1>"
        "<p class='sub'>Indoor multi-pot photos converted into target-pot overlays, in-pot coverage metrics, spill estimates, and growth-ready tracking signals.</p>"
        "</div>"
        "<div class='hero-meta'>"
        f"<p><strong>Run ID:</strong> {html_escape(run_id or 'n/a')}</p>"
        f"<p><strong>Run Date:</strong> {html_escape(run_date or 'n/a')}</p>"
        f"<p><strong>Generated (UTC):</strong> {html_escape(generated)}</p>"
        f"<p><strong>Readiness mix:</strong> high={high}, moderate={moderate}, low={low}</p>"
        "</div>"
        "</section>"
        "<section class='metric-grid'>"
        f"{card_html}"
        "</section>"
    )


def build_algorithm_rows(rows: Sequence[Dict[str, str]]) -> str:
    lines: List[str] = []
    for row in rows:
        status = (row.get("status", "") or "").strip()
        availability = safe_float(row.get("availability_ratio"))
        variation = safe_float(row.get("variation_coeff"))
        lines.append(
            "<tr>"
            f"<td><code>{html_escape((row.get('algorithm_key', '') or '').strip())}</code></td>"
            f"<td>{html_escape((row.get('metric_key', '') or '').strip())}</td>"
            f"<td><span class='status {attr_escape(status)}'>{html_escape(status or 'unknown')}</span></td>"
            f"<td>{'' if availability is None else f'{availability * 100:.1f}%'}</td>"
            f"<td>{'' if variation is None else f'{variation:.3f}'}</td>"
            f"<td>{html_escape((row.get('why_helpful', '') or '').strip())}</td>"
            "</tr>"
        )
    return "\n".join(lines) if lines else "<tr><td colspan='6'>No algorithm rows.</td></tr>"


def build_card_html(rows: Sequence[Dict[str, str]]) -> str:
    cards: List[str] = []
    for row in rows:
        pot_id = (row.get("pot_id", "") or "").strip()
        variety = (row.get("variety_name", "") or "").strip() or "Unknown variety"
        readiness = normalize_readiness(row.get("tracking_readiness", "") or "")
        next_step = (row.get("next_step_code", "") or "").strip() or "n/a"
        next_step_text = (row.get("next_step_text", "") or "").strip() or "No recommendation."
        overlay_path = path_for_page(row.get("overlay_path", "") or "")
        crop_path = path_for_page(row.get("crop_path", "") or "")
        photo_url = path_for_page(row.get("photo_url", "") or "")

        focus_score = safe_float(row.get("focus_score")) or 0.0
        pot_coverage = safe_float(row.get("pot_coverage")) or 0.0
        spill = safe_float(row.get("spill_in_pot_ratio"))
        if spill is None:
            spill = safe_float(row.get("neighbor_spill_ratio")) or 0.0
        chlorosis = safe_float(row.get("chlorosis_ratio")) or 0.0
        growth = safe_float(row.get("growth_delta"))
        plant_count = int(round(safe_float(row.get("plant_count_estimate")) or 0.0))
        blur = safe_float(row.get("blur_score")) or 0.0
        anchor_mode = (row.get("anchor_mode", "") or "").strip() or "n/a"
        growth_text = "n/a" if growth is None else f"{growth * 100:.1f}%"
        coverage_pct = pot_coverage * 100.0
        spill_pct = spill * 100.0
        chlorosis_pct = chlorosis * 100.0

        image_block = (
            f"<img src='{attr_escape(overlay_path)}' alt='Overlay for {attr_escape(pot_id)}' loading='lazy' />"
            if overlay_path
            else "<div class='photo-missing'>No overlay</div>"
        )
        crop_link = (
            f"<a href='{attr_escape(crop_path)}' target='_blank' rel='noreferrer'>Crop</a>"
            if crop_path
            else ""
        )
        photo_link = (
            f"<a href='{attr_escape(photo_url)}' target='_blank' rel='noreferrer'>Original</a>"
            if photo_url
            else ""
        )
        links = " | ".join(link for link in [crop_link, photo_link] if link)
        links_html = f"<p class='links'>{links}</p>" if links else ""

        cards.append(
            "<article class='pot-card' "
            f"data-readiness='{attr_escape(readiness)}' "
            f"data-action='{attr_escape(next_step)}' "
            f"data-search='{attr_escape((pot_id + ' ' + variety + ' ' + next_step).lower())}'>"
            "<div class='photo-wrap'>"
            f"{image_block}"
            "</div>"
            "<div class='card-body'>"
            "<div class='card-top'>"
            f"<span class='pot'>{html_escape(pot_id)}</span>"
            f"<span class='readiness {attr_escape(readiness)}'>{html_escape(readiness)}</span>"
            "</div>"
            f"<h3>{html_escape(variety)}</h3>"
            f"<p class='next-step'>{html_escape(next_step)}</p>"
            "<div class='bars'>"
            "<div class='bar-row'><span>Focus</span>"
            f"<div class='bar focus'><div style='width:{max(0.0, min(focus_score * 100.0, 100.0)):.1f}%'></div></div>"
            f"<em>{focus_score:.2f}</em></div>"
            "<div class='bar-row'><span>Coverage</span>"
            f"<div class='bar coverage'><div style='width:{max(0.0, min(coverage_pct, 100.0)):.1f}%'></div></div>"
            f"<em>{coverage_pct:.1f}%</em></div>"
            "<div class='bar-row'><span>Spill</span>"
            f"<div class='bar spill'><div style='width:{max(0.0, min(spill_pct, 100.0)):.1f}%'></div></div>"
            f"<em>{spill_pct:.1f}%</em></div>"
            "</div>"
            "<dl class='stats'>"
            f"<div><dt>Growth</dt><dd>{html_escape(growth_text)}</dd></div>"
            f"<div><dt>Plants</dt><dd>{plant_count}</dd></div>"
            f"<div><dt>Anchor</dt><dd>{html_escape(anchor_mode)}</dd></div>"
            f"<div><dt>Blur</dt><dd>{blur:.0f}</dd></div>"
            f"<div><dt>Chlorosis</dt><dd>{chlorosis_pct:.1f}%</dd></div>"
            "</dl>"
            f"<p class='detail'>{html_escape(next_step_text)}</p>"
            f"{links_html}"
            "</div>"
            "</article>"
        )
    return "\n".join(cards) if cards else "<p class='muted'>No pot rows found.</p>"


def build_page(
    metrics_rows: Sequence[Dict[str, str]],
    algorithm_rows: Sequence[Dict[str, str]],
    summary: Dict[str, object],
    source_metrics_csv: Path,
    source_algorithm_csv: Path,
    source_summary_json: Path,
) -> str:
    sorted_rows = sorted(metrics_rows, key=pot_sort_key)
    action_options = sorted(
        {
            (row.get("next_step_code", "") or "").strip()
            for row in sorted_rows
            if (row.get("next_step_code", "") or "").strip()
        }
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1.10 Pot-Anchored CV Research Viewer</title>
  <style>
    :root {{
      --bg: #f3efe5;
      --paper: #fffdf8;
      --ink: #1d2b29;
      --muted: #60706c;
      --line: #d7cdbc;
      --high: #1d6a43;
      --moderate: #7a5819;
      --low: #8c2b2b;
      --accent: #275d7f;
      --focus: #245f7d;
      --coverage: #2f7b57;
      --spill: #995322;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 420px at 110% -10%, #e1d8c4 0%, transparent 64%),
        radial-gradient(900px 420px at -10% 110%, #e8deca 0%, transparent 64%),
        linear-gradient(140deg, #f5f1e7, #ece4d3);
    }}
    main {{ max-width: 1340px; margin: 0 auto; padding: 18px 14px 34px; }}
    .hero {{
      background: linear-gradient(120deg, rgba(39, 93, 127, 0.12), rgba(47, 123, 87, 0.10));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      justify-content: space-between;
      align-items: start;
    }}
    .eyebrow {{
      margin: 0 0 4px;
      font-size: 0.76rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #49615b;
    }}
    h1 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.35rem, 3vw, 2.15rem);
    }}
    .sub {{ margin: 8px 0 0; color: var(--muted); max-width: 72ch; }}
    .hero-meta p {{ margin: 0 0 6px; color: #41524f; font-size: 0.9rem; }}
    .metric-grid {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .metric-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
    }}
    .metric-label {{
      margin: 0;
      font-size: 0.75rem;
      letter-spacing: 0.06em;
      color: #61736f;
      text-transform: uppercase;
    }}
    .metric-value {{
      margin: 4px 0 0;
      font-size: 1.30rem;
      font-weight: 700;
      color: var(--accent);
      line-height: 1.1;
    }}
    .metric-value.high {{ color: var(--high); }}
    .metric-value.moderate {{ color: var(--moderate); }}
    .metric-value.low {{ color: var(--low); }}
    .metric-value.action {{ font-size: 1rem; }}
    .layout {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 12px;
    }}
    .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }}
    .panel h2 {{
      margin: 0 0 10px;
      font-size: 0.95rem;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      color: #4f6460;
    }}
    .muted {{ color: var(--muted); font-size: 0.86rem; }}
    .source-list {{
      display: grid;
      gap: 6px;
      font-size: 0.88rem;
      color: #445552;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      display: block;
      overflow-x: auto;
      white-space: nowrap;
    }}
    th, td {{
      border-bottom: 1px solid #ede6d8;
      text-align: left;
      padding: 7px 6px;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #f6f1e6;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #566a66;
    }}
    code {{ font-size: 0.8rem; background: #f0eadb; padding: 2px 4px; border-radius: 5px; }}
    .status {{
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: lowercase;
      border: 1px solid transparent;
    }}
    .status.helpful {{ color: #155438; background: #e4f3e8; border-color: #c0e2cc; }}
    .status.promising_with_more_data {{ color: #7a5613; background: #fbf1dd; border-color: #ecd5a8; }}
    .status.limited_current_data {{ color: #7a2a2a; background: #f8e5e5; border-color: #ebc5c5; }}
    .toolbar {{
      margin-top: 12px;
      position: sticky;
      top: 8px;
      z-index: 4;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .toolbar input, .toolbar select {{
      border: 1px solid #cfc6b8;
      border-radius: 8px;
      background: #fffef9;
      font: inherit;
      color: var(--ink);
      padding: 8px 9px;
    }}
    .toolbar input {{ flex: 1; min-width: 240px; }}
    .shown {{ margin-left: auto; font-size: 0.84rem; color: #4d5f5b; }}
    .pot-grid {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(285px, 1fr));
      gap: 11px;
    }}
    .pot-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .photo-wrap {{
      aspect-ratio: 4 / 3;
      background: #e8e1d1;
      overflow: hidden;
    }}
    .photo-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .photo-missing {{
      height: 100%;
      display: grid;
      place-items: center;
      color: #71827d;
      font-size: 0.84rem;
    }}
    .card-body {{ padding: 10px; display: grid; gap: 8px; }}
    .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
    .pot {{
      font-weight: 700;
      letter-spacing: 0.04em;
      color: #243533;
    }}
    .readiness {{
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .readiness.high {{ background: #e5f3e8; color: var(--high); }}
    .readiness.moderate {{ background: #fbf0dd; color: var(--moderate); }}
    .readiness.low {{ background: #f8e3e3; color: var(--low); }}
    h3 {{ margin: 0; font-size: 1rem; }}
    .next-step {{
      margin: 0;
      font-size: 0.82rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #5b6b68;
    }}
    .bars {{ display: grid; gap: 6px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 60px 1fr auto;
      gap: 8px;
      align-items: center;
      font-size: 0.82rem;
    }}
    .bar {{
      background: #ebe4d6;
      border-radius: 999px;
      overflow: hidden;
      height: 10px;
    }}
    .bar div {{ height: 100%; }}
    .bar.focus div {{ background: var(--focus); }}
    .bar.coverage div {{ background: var(--coverage); }}
    .bar.spill div {{ background: var(--spill); }}
    .stats {{
      margin: 0;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .stats div {{
      background: #faf6ed;
      border: 1px solid #ece2d2;
      border-radius: 8px;
      padding: 7px;
    }}
    .stats dt {{
      font-size: 0.70rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #667873;
    }}
    .stats dd {{
      margin: 4px 0 0;
      font-size: 0.92rem;
      font-weight: 700;
      color: #243532;
    }}
    .detail {{ margin: 0; font-size: 0.88rem; color: #465955; }}
    .links {{ margin: 0; font-size: 0.85rem; }}
    .links a {{ color: #1d5778; }}
    .footer {{
      margin-top: 16px;
      color: #566864;
      font-size: 0.84rem;
    }}
    @media (max-width: 980px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    {build_summary_cards(summary)}
    <section class="layout">
      <section class="panel">
        <h2>Algorithm View</h2>
        <table>
          <thead>
            <tr>
              <th>Algorithm</th>
              <th>Metric</th>
              <th>Status</th>
              <th>Availability</th>
              <th>Variation</th>
              <th>Why It Matters</th>
            </tr>
          </thead>
          <tbody>
            {build_algorithm_rows(algorithm_rows)}
          </tbody>
        </table>
      </section>
      <aside class="panel">
        <h2>Method + Sources</h2>
        <p class="muted">This experiment uses a center-biased plant anchor, optional bright-label detection, and an inferred trapezoid pot mask to reduce neighbor contamination in indoor multi-pot frames.</p>
        <div class="source-list">
          <span>Metrics CSV: <code>{html_escape(str(source_metrics_csv))}</code></span>
          <span>Algorithm CSV: <code>{html_escape(str(source_algorithm_csv))}</code></span>
          <span>Summary JSON: <code>{html_escape(str(source_summary_json))}</code></span>
          <span>Tracker asset folder: <code>tracker/assets/v1-10-pot-cv</code></span>
        </div>
      </aside>
    </section>
    <section class="toolbar">
      <input id="search" type="search" placeholder="Search by pot, variety, or next step" />
      <select id="readiness">
        <option value="all">All readiness</option>
        <option value="high">High</option>
        <option value="moderate">Moderate</option>
        <option value="low">Low</option>
      </select>
      <select id="action">
        <option value="all">All next steps</option>
        {''.join(f"<option value='{attr_escape(value)}'>{html_escape(value)}</option>" for value in action_options)}
      </select>
      <span class="shown" id="shown">0 shown</span>
    </section>
    <section class="pot-grid" id="pot-grid">
      {build_card_html(sorted_rows)}
    </section>
    <p class="footer">Source artifacts are generated from the isolated v1.10 research track and can be rebuilt locally with <code>python3 scripts/v110_pot_cv_experiment.py</code> and <code>python3 scripts/build_v110_pot_cv_page.py</code>.</p>
  </main>
  <script>
    const cards = Array.from(document.querySelectorAll('.pot-card'));
    const search = document.getElementById('search');
    const readiness = document.getElementById('readiness');
    const action = document.getElementById('action');
    const shown = document.getElementById('shown');

    function applyFilters() {{
      const query = (search.value || '').trim().toLowerCase();
      const readinessValue = readiness.value;
      const actionValue = action.value;
      let visible = 0;
      cards.forEach((card) => {{
        const searchText = card.dataset.search || '';
        const readinessText = card.dataset.readiness || '';
        const actionText = card.dataset.action || '';
        const matchesQuery = !query || searchText.includes(query);
        const matchesReadiness = readinessValue === 'all' || readinessText === readinessValue;
        const matchesAction = actionValue === 'all' || actionText === actionValue;
        const show = matchesQuery && matchesReadiness && matchesAction;
        card.style.display = show ? '' : 'none';
        if (show) visible += 1;
      }});
      shown.textContent = `${{visible}} shown`;
    }}

    search.addEventListener('input', applyFilters);
    readiness.addEventListener('change', applyFilters);
    action.addEventListener('change', applyFilters);
    applyFilters();
  </script>
</body>
</html>
"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=Path("data/research/v1_10/pot_cv_metrics.csv"),
        help="CSV from the v1.10 pot CV experiment.",
    )
    parser.add_argument(
        "--algorithm-csv",
        type=Path,
        default=Path("data/research/v1_10/algorithm_assessment.csv"),
        help="Algorithm assessment CSV from the v1.10 pot CV experiment.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/research/v1_10/pot_cv_summary.json"),
        help="Summary JSON from the v1.10 pot CV experiment.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/v1-10-pot-cv-research.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    metrics_rows = read_csv_rows(args.metrics_csv)
    algorithm_rows = read_csv_rows(args.algorithm_csv)
    summary = read_json_optional(args.summary_json)
    html = build_page(
        metrics_rows=metrics_rows,
        algorithm_rows=algorithm_rows,
        summary=summary,
        source_metrics_csv=args.metrics_csv,
        source_algorithm_csv=args.algorithm_csv,
        source_summary_json=args.summary_json,
    )
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
