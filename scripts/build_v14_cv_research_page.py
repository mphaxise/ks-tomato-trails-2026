#!/usr/bin/env python3
"""Build a visual HTML page for v1.4 CV research outputs."""

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


def safe_int(value: object) -> int:
    maybe_float = safe_float(value)
    if maybe_float is None:
        return 0
    return int(round(maybe_float))


def pot_sort_key(row: Dict[str, str]) -> Tuple[int, str]:
    pot_id = (row.get("pot_id", "") or "").strip().upper()
    if pot_id.endswith("T") and pot_id[:-1].isdigit():
        return (int(pot_id[:-1]), pot_id)
    return (10_000, pot_id)


def normalize_survival(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned in {"high", "moderate", "low"}:
        return cleaned
    return "unknown"


def image_url_for_page(row: Dict[str, str]) -> str:
    photo_url = (row.get("photo_url", "") or "").strip()
    if photo_url:
        return photo_url
    local_path = (row.get("image_path", "") or "").strip()
    if not local_path:
        return ""
    if local_path.startswith("http://") or local_path.startswith("https://"):
        return local_path
    if local_path.startswith("/"):
        return local_path
    return f"../{local_path}"


def build_summary_cards(summary: Dict[str, object], rows: Sequence[Dict[str, str]]) -> str:
    survival = summary.get("survival_counts")
    action = summary.get("action_counts")
    if not isinstance(survival, dict):
        survival = {}
    if not isinstance(action, dict):
        action = {}

    rows_count = len(rows)
    high = int(survival.get("high", 0))
    moderate = int(survival.get("moderate", 0))
    low = int(survival.get("low", 0))
    top_action = ""
    if action:
        top_action = sorted(action.items(), key=lambda item: (-int(item[1]), item[0]))[0][0]

    run_id = str(summary.get("run_id", "")).strip()
    run_date = str(summary.get("run_date", "")).strip()
    created = str(summary.get("created_at", "")).strip()
    generated = created or datetime.now(timezone.utc).isoformat()

    cards = [
        ("Pots Analyzed", str(rows_count), "all"),
        ("High Survival", str(high), "high"),
        ("Moderate Survival", str(moderate), "moderate"),
        ("Low Survival", str(low), "low"),
        ("Top Suggested Action", top_action or "n/a", "action"),
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

    return (
        "<section class='hero'>"
        "<div>"
        "<p class='eyebrow'>Version 1.4 Research</p>"
        "<h1>Computer Vision Research Output</h1>"
        "<p class='sub'>Visual summary of 32-pot experiment metrics, algorithm findings, and per-pot recommendations.</p>"
        "</div>"
        "<div class='hero-meta'>"
        f"<p><strong>Run ID:</strong> {html_escape(run_id or 'n/a')}</p>"
        f"<p><strong>Run Date:</strong> {html_escape(run_date or 'n/a')}</p>"
        f"<p><strong>Generated (UTC):</strong> {html_escape(generated)}</p>"
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
        status_class = attr_escape(status or "unknown")
        availability = safe_float(row.get("availability_ratio"))
        variation = safe_float(row.get("variation_coeff"))
        lines.append(
            "<tr>"
            f"<td><code>{html_escape((row.get('algorithm_key', '') or '').strip())}</code></td>"
            f"<td>{html_escape((row.get('metric_key', '') or '').strip())}</td>"
            f"<td><span class='status {status_class}'>{html_escape(status or 'unknown')}</span></td>"
            f"<td>{'' if availability is None else f'{availability * 100:.1f}%'}"
            "</td>"
            f"<td>{'' if variation is None else f'{variation:.3f}'}</td>"
            f"<td>{html_escape((row.get('signal_summary', '') or '').strip())}</td>"
            f"<td>{html_escape((row.get('why_helpful', '') or '').strip())}</td>"
            "</tr>"
        )
    if not lines:
        return "<tr><td colspan='7'>No algorithm rows.</td></tr>"
    return "\n".join(lines)


def build_calibration_block(calibration: Dict[str, object]) -> str:
    if not calibration:
        return (
            "<section class='panel'>"
            "<h2>Calibration Check</h2>"
            "<p class='muted'>No calibration summary file found.</p>"
            "</section>"
        )

    rows_count = int(calibration.get("manual_rows", 0) or 0)
    survival_acc = float(calibration.get("survival_accuracy", 0.0) or 0.0) * 100.0
    action_acc = float(calibration.get("action_accuracy", 0.0) or 0.0) * 100.0
    joint_acc = float(calibration.get("joint_accuracy", 0.0) or 0.0) * 100.0
    mismatches = calibration.get("mismatches")
    mismatch_count = len(mismatches) if isinstance(mismatches, list) else 0

    return (
        "<section class='panel'>"
        "<h2>Calibration Check</h2>"
        "<div class='cal-grid'>"
        f"<div><p class='cal-label'>Manual Rows</p><p class='cal-value'>{rows_count}</p></div>"
        f"<div><p class='cal-label'>Survival Accuracy</p><p class='cal-value'>{survival_acc:.1f}%</p></div>"
        f"<div><p class='cal-label'>Action Accuracy</p><p class='cal-value'>{action_acc:.1f}%</p></div>"
        f"<div><p class='cal-label'>Joint Accuracy</p><p class='cal-value'>{joint_acc:.1f}%</p></div>"
        f"<div><p class='cal-label'>Mismatch Rows</p><p class='cal-value'>{mismatch_count}</p></div>"
        "</div>"
        "<p class='muted'>Manual subset alignment for current threshold calibration.</p>"
        "</section>"
    )


def build_card_html(rows: Sequence[Dict[str, str]]) -> str:
    cards: List[str] = []
    for row_index, row in enumerate(rows):
        pot_id = (row.get("pot_id", "") or "").strip()
        variety = (row.get("variety_name", "") or "").strip() or "Unknown variety"
        survival = normalize_survival((row.get("survival_hypothesis", "") or "").strip())
        action_code = (row.get("action_code", "") or "").strip() or "n/a"
        action_text = (row.get("action_recommendation", "") or "").strip()
        image_url = image_url_for_page(row)

        coverage = safe_float(row.get("vegetation_coverage")) or 0.0
        chlorosis = safe_float(row.get("chlorosis_ratio")) or 0.0
        health = safe_float(row.get("health_score")) or 0.0
        growth = safe_float(row.get("growth_delta"))
        plant_count = safe_int(row.get("plant_count_estimate"))
        canopy_components = safe_int(row.get("canopy_components"))
        blur = safe_float(row.get("blur_score")) or 0.0

        growth_text = "n/a" if growth is None else f"{growth * 100:.1f}%"
        growth_attr = "na" if growth is None else ("up" if growth >= 0 else "down")
        coverage_pct = coverage * 100.0
        chlorosis_pct = chlorosis * 100.0

        if coverage_pct < 2.0:
            coverage_hint = "very sparse canopy"
        elif coverage_pct < 5.0:
            coverage_hint = "early but present canopy"
        else:
            coverage_hint = "stronger canopy fill"

        if chlorosis_pct < 5.0:
            chlorosis_hint = "little visible yellowing"
        elif chlorosis_pct < 20.0:
            chlorosis_hint = "some yellowing to monitor"
        else:
            chlorosis_hint = "elevated yellowing signal"

        if growth is None:
            growth_hint = "baseline not available"
        elif growth < -0.2:
            growth_hint = "coverage decline vs baseline"
        elif growth < 0.15:
            growth_hint = "roughly stable vs baseline"
        else:
            growth_hint = "coverage gain vs baseline"

        if survival == "high":
            survival_help = "High: stronger canopy and stable/improving growth."
        elif survival == "moderate":
            survival_help = "Moderate: viable but still needs routine monitoring."
        elif survival == "low":
            survival_help = "Low: weak canopy or stress indicators need attention."
        else:
            survival_help = "Unknown: not enough signal for a clear category."

        card = (
            f"<article class='pot-card' data-pot-id='{attr_escape(pot_id)}' "
            f"data-row-index='{row_index}' "
            f"data-survival='{attr_escape(survival)}' data-action='{attr_escape(action_code)}' "
            f"data-search='{attr_escape((pot_id + ' ' + variety + ' ' + action_code).lower())}'>"
            "<div class='card-front'>"
            "<div class='photo-wrap'>"
            + (
                f"<img src='{attr_escape(image_url)}' alt='Pot {attr_escape(pot_id)}' loading='lazy' data-open='1' />"
                if image_url
                else "<div class='photo-missing'>No image</div>"
            )
            + "</div>"
            "<div class='card-body'>"
            "<div class='card-top'>"
            f"<span class='pot'>{html_escape(pot_id)}</span>"
            "<div class='top-right'>"
            f"<span class='survival {attr_escape(survival)}'>{html_escape(survival)}</span>"
            "<button type='button' class='flip-btn' data-flip='1' aria-label='Flip card to see metric meanings'>?</button>"
            "</div>"
            "</div>"
            f"<h3>{html_escape(variety)}</h3>"
            f"<p class='action-code'>{html_escape(action_code)}</p>"
            "<div class='bars'>"
            "<div class='bar-row'><span>Health</span>"
            f"<div class='bar health'><div style='width:{max(0.0, min(health, 100.0)):.1f}%'></div></div>"
            f"<em>{health:.1f}</em></div>"
            "<div class='bar-row'><span>Coverage</span>"
            f"<div class='bar coverage'><div style='width:{max(0.0, min(coverage_pct, 100.0)):.1f}%'></div></div>"
            f"<em>{coverage_pct:.1f}%</em></div>"
            "<div class='bar-row'><span>Chlorosis</span>"
            f"<div class='bar chlorosis'><div style='width:{max(0.0, min(chlorosis_pct, 100.0)):.1f}%'></div></div>"
            f"<em>{chlorosis_pct:.1f}%</em></div>"
            "</div>"
            "<dl class='stats'>"
            f"<div><dt>Growth</dt><dd class='{growth_attr}'>{html_escape(growth_text)}</dd></div>"
            f"<div><dt>Plants</dt><dd>{plant_count}</dd></div>"
            f"<div><dt>Components</dt><dd>{canopy_components}</dd></div>"
            f"<div><dt>Blur</dt><dd>{blur:.0f}</dd></div>"
            "</dl>"
            f"<p class='action-text'>{html_escape(action_text or 'No recommendation available.')}</p>"
            "<button type='button' class='flip-link' data-flip='1'>Flip for metric meaning</button>"
            "</div>"
            "</div>"
            "<div class='card-back'>"
            "<div class='card-back-head'>"
            f"<span class='pot'>{html_escape(pot_id)} Guide</span>"
            "<button type='button' class='flip-btn back' data-flip='1' aria-label='Back to metrics'>&larr;</button>"
            "</div>"
            "<p class='back-intro'>How to read these terms:</p>"
            "<ul class='back-list'>"
            f"<li><strong>High/Moderate/Low:</strong> {html_escape(survival_help)}</li>"
            "<li><strong>Coverage:</strong> green canopy area inside the pot crop; higher means fuller foliage.</li>"
            "<li><strong>Chlorosis:</strong> yellowing inside canopy; higher can signal stress/nutrient issues.</li>"
            "<li><strong>Growth:</strong> canopy coverage change vs earliest baseline photo for this pot.</li>"
            "<li><strong>Components:</strong> separate green blobs detected; often approximates distinct seedling clumps.</li>"
            "<li><strong>Blur:</strong> focus score; higher means sharper image and more reliable measurements.</li>"
            "</ul>"
            "<p class='back-signal'>"
            f"This pot currently shows <strong>{coverage_pct:.1f}% coverage</strong> "
            f"({html_escape(coverage_hint)}), <strong>{chlorosis_pct:.1f}% chlorosis</strong> "
            f"({html_escape(chlorosis_hint)}), and <strong>{html_escape(growth_text)} growth</strong> "
            f"({html_escape(growth_hint)})."
            "</p>"
            "</div>"
            "</article>"
        )
        cards.append(card)
    return "\n".join(cards) if cards else "<p class='muted'>No pot rows found.</p>"


def build_page(
    metrics_rows: Sequence[Dict[str, str]],
    algorithm_rows: Sequence[Dict[str, str]],
    summary: Dict[str, object],
    calibration: Dict[str, object],
    source_metrics_csv: Path,
    source_algorithm_csv: Path,
) -> str:
    sorted_rows = sorted(metrics_rows, key=pot_sort_key)
    for row in sorted_rows:
        row["survival_hypothesis"] = normalize_survival((row.get("survival_hypothesis", "") or "").strip())

    action_options = sorted(
        {
            (row.get("action_code", "") or "").strip()
            for row in sorted_rows
            if (row.get("action_code", "") or "").strip()
        }
    )
    rows_json = json.dumps(sorted_rows, ensure_ascii=True)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1.4 CV Research Viewer</title>
  <style>
    :root {{
      --bg: #f4f0e7;
      --paper: #fffdf8;
      --ink: #1d2b29;
      --muted: #596a67;
      --line: #d6cebe;
      --high: #1f6b44;
      --moderate: #7d5d1f;
      --low: #8d2f2f;
      --accent: #2f5f7f;
      --health: #2f6f56;
      --coverage: #3e75a3;
      --chlorosis: #b87926;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 420px at 104% -6%, #e4dcca 0%, transparent 64%),
        radial-gradient(900px 420px at -6% 108%, #e7dcc8 0%, transparent 64%),
        linear-gradient(140deg, #f5f1e7, #ece4d2);
    }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 20px 14px 34px; }}
    .hero {{
      background: linear-gradient(120deg, rgba(62, 117, 163, 0.10), rgba(47, 111, 86, 0.12));
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
      color: #48605a;
    }}
    h1 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.35rem, 3vw, 2.15rem);
    }}
    .sub {{ margin: 8px 0 0; color: var(--muted); max-width: 66ch; }}
    .hero-meta p {{ margin: 0 0 6px; color: #3f504d; font-size: 0.9rem; }}

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
      color: #617370;
      text-transform: uppercase;
    }}
    .metric-value {{
      margin: 4px 0 0;
      font-size: 1.38rem;
      font-weight: 700;
      color: var(--accent);
      line-height: 1.1;
    }}
    .metric-value.high {{ color: var(--high); }}
    .metric-value.moderate {{ color: var(--moderate); }}
    .metric-value.low {{ color: var(--low); }}
    .metric-value.action {{ font-size: 1.05rem; }}

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
    .muted {{ color: #61726e; font-size: 0.86rem; }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      display: block;
      overflow-x: auto;
      white-space: nowrap;
    }}
    th, td {{
      border-bottom: 1px solid #ede7d8;
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
      z-index: 1;
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

    .cal-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(120px, 1fr));
      gap: 8px;
    }}
    .cal-label {{
      margin: 0;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #60716d;
    }}
    .cal-value {{
      margin: 3px 0 0;
      font-size: 1.2rem;
      font-weight: 700;
      color: #2c3f3b;
    }}

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
      border: 1px solid #cfc7b8;
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
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 11px;
    }}
    .pot-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
    }}
    .card-front {{
      display: flex;
      flex-direction: column;
      height: 100%;
    }}
    .card-back {{
      display: none;
      height: 100%;
      padding: 10px;
      background: #fcf9f1;
      border-top: 1px solid #e7decb;
    }}
    .pot-card.is-flipped .card-front {{
      display: none;
    }}
    .pot-card.is-flipped .card-back {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .photo-wrap {{
      aspect-ratio: 4 / 3;
      background: #e8e1d1;
      overflow: hidden;
      cursor: zoom-in;
    }}
    .photo-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transition: transform 160ms ease;
    }}
    .pot-card:hover .photo-wrap img {{ transform: scale(1.02); }}
    .photo-missing {{
      height: 100%;
      display: grid;
      place-items: center;
      color: #71827d;
      font-size: 0.84rem;
    }}
    .card-body {{ padding: 10px; display: grid; gap: 8px; }}
    .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
    .top-right {{ display: flex; align-items: center; gap: 6px; }}
    .pot {{
      font-weight: 700;
      letter-spacing: 0.04em;
      color: #243533;
    }}
    .flip-btn {{
      width: 23px;
      height: 23px;
      border: 1px solid #cfc5b1;
      border-radius: 999px;
      background: #f7f3ea;
      color: #334b46;
      font-size: 0.82rem;
      font-weight: 700;
      line-height: 1;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    .flip-btn.back {{
      width: auto;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 0.78rem;
    }}
    .survival {{
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border: 1px solid transparent;
    }}
    .survival.high {{ color: #155438; background: #e2f1e6; border-color: #c1e0cc; }}
    .survival.moderate {{ color: #6e4f17; background: #faefd9; border-color: #eacf9b; }}
    .survival.low {{ color: #7d2b2b; background: #f8e3e3; border-color: #e9c2c2; }}
    .survival.unknown {{ color: #5f6664; background: #edf0ef; border-color: #d3dbd8; }}
    h3 {{
      margin: 0;
      font-size: 0.98rem;
      line-height: 1.2;
      color: #233431;
    }}
    .action-code {{
      margin: 0;
      color: #36566b;
      font-weight: 700;
      font-size: 0.82rem;
    }}
    .bars {{ display: grid; gap: 5px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 62px 1fr auto;
      gap: 6px;
      align-items: center;
      font-size: 0.78rem;
      color: #4d615d;
    }}
    .bar {{
      height: 7px;
      border-radius: 999px;
      background: #ede7d8;
      overflow: hidden;
    }}
    .bar > div {{ height: 100%; }}
    .bar.health > div {{ background: linear-gradient(90deg, #2b6b53, #4d8a73); }}
    .bar.coverage > div {{ background: linear-gradient(90deg, #3c6f9a, #5d90b8); }}
    .bar.chlorosis > div {{ background: linear-gradient(90deg, #ab6f20, #cb933f); }}
    .stats {{
      margin: 0;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
    }}
    .stats div {{
      background: #f5f0e3;
      border: 1px solid #e2dac8;
      border-radius: 8px;
      padding: 5px 6px;
    }}
    .stats dt {{
      margin: 0;
      font-size: 0.67rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #697b77;
    }}
    .stats dd {{
      margin: 2px 0 0;
      font-size: 0.8rem;
      font-weight: 700;
      color: #2a3a37;
    }}
    .stats dd.up {{ color: #1d6a42; }}
    .stats dd.down {{ color: #8b2e2e; }}
    .action-text {{
      margin: 0;
      font-size: 0.82rem;
      color: #4f605d;
      min-height: 2.3em;
    }}
    .flip-link {{
      justify-self: start;
      border: 1px dashed #c6bda8;
      background: #f8f4ea;
      border-radius: 999px;
      color: #38584f;
      font-size: 0.74rem;
      padding: 4px 9px;
      cursor: pointer;
    }}
    .card-back-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }}
    .back-intro {{
      margin: 0;
      font-size: 0.82rem;
      color: #516662;
      font-weight: 700;
    }}
    .back-list {{
      margin: 0;
      padding-left: 16px;
      display: grid;
      gap: 5px;
      color: #4d605c;
      font-size: 0.79rem;
      line-height: 1.35;
    }}
    .back-signal {{
      margin: 0;
      font-size: 0.8rem;
      line-height: 1.35;
      color: #40534f;
      background: #f2ede0;
      border: 1px solid #e0d7c5;
      border-radius: 8px;
      padding: 7px;
    }}

    .sources {{
      margin-top: 12px;
      font-size: 0.82rem;
      color: #5f716d;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
    }}
    .sources code {{ background: #efe8d9; }}

    .lightbox {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 10px;
      background: rgba(10, 14, 13, 0.88);
      z-index: 40;
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-shell {{
      width: min(96vw, 1260px);
      height: min(92vh, 920px);
      max-height: 92vh;
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
      gap: 10px;
      align-items: stretch;
    }}
    .lightbox-media {{
      background: #131715;
      border-radius: 10px;
      border: 1px solid #2f3a36;
      display: flex;
      flex-direction: column;
      min-height: 0;
      overflow: hidden;
    }}
    .lightbox-canvas {{
      position: relative;
      flex: 1 1 auto;
      min-height: 0;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #121413;
    }}
    .lightbox img {{
      width: auto;
      height: auto;
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
      transform-origin: center center;
      transform: translate(0px, 0px) scale(1);
      transition: transform 120ms ease-out;
      cursor: zoom-in;
      user-select: none;
      -webkit-user-drag: none;
      touch-action: none;
    }}
    .lightbox img.zoomed {{ cursor: grab; }}
    .lightbox img.dragging {{
      cursor: grabbing;
      transition: none;
    }}
    .lightbox-nav {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      padding: 8px 10px;
      border-top: 1px solid #25302c;
      background: #17201d;
      color: #d8e2df;
      font-size: 0.83rem;
    }}
    .lightbox-nav-main {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .lightbox-zoom {{
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .zoom-level {{
      min-width: 56px;
      text-align: center;
      color: #d8e2df;
      font-size: 0.78rem;
      font-variant-numeric: tabular-nums;
    }}
    #lightboxCount {{
      min-width: 74px;
      text-align: center;
      font-variant-numeric: tabular-nums;
    }}
    .lightbox-nav button {{
      border: 1px solid #4d5c56;
      border-radius: 999px;
      background: #243732;
      color: #f7fbfa;
      font-size: 0.8rem;
      line-height: 1;
      padding: 5px 10px;
      cursor: pointer;
    }}
    .lightbox-nav button:disabled {{
      opacity: 0.45;
      cursor: default;
    }}
    .lightbox-details {{
      background: #fffdf8;
      border-radius: 10px;
      border: 1px solid #dbd3c2;
      padding: 12px;
      overflow: auto;
      color: #2a3a37;
      display: grid;
      gap: 9px;
      align-content: start;
    }}
    .lightbox-details h3 {{
      margin: 0;
      color: #223330;
      font-size: 1rem;
    }}
    .lightbox-details .meta {{
      margin: 0;
      font-size: 0.82rem;
      color: #536662;
    }}
    .lightbox-details .survival-pill {{
      display: inline-flex;
      margin-left: 6px;
      padding: 2px 7px;
      border-radius: 999px;
      border: 1px solid transparent;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .lightbox-details .survival-pill.high {{ color: #155438; background: #e2f1e6; border-color: #c1e0cc; }}
    .lightbox-details .survival-pill.moderate {{ color: #6e4f17; background: #faefd9; border-color: #eacf9b; }}
    .lightbox-details .survival-pill.low {{ color: #7d2b2b; background: #f8e3e3; border-color: #e9c2c2; }}
    .lightbox-details .survival-pill.unknown {{ color: #5f6664; background: #edf0ef; border-color: #d3dbd8; }}
    .lightbox-details dl {{
      margin: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 8px;
    }}
    .lightbox-details dt {{
      margin: 0;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #6a7d78;
    }}
    .lightbox-details dd {{
      margin: 2px 0 0;
      font-size: 0.82rem;
      font-weight: 700;
      color: #2c3b38;
    }}
    .lightbox-details .action-full {{
      margin: 0;
      font-size: 0.82rem;
      color: #415451;
      line-height: 1.35;
    }}
    .lightbox-details ul {{
      margin: 0;
      padding-left: 16px;
      display: grid;
      gap: 4px;
      color: #4f615d;
      font-size: 0.79rem;
      line-height: 1.35;
    }}
    .close {{
      position: fixed;
      top: 10px;
      right: 10px;
      width: 34px;
      height: 34px;
      border: 1px solid #ecdfca;
      border-radius: 999px;
      background: #1f3f38;
      color: #fff;
      font-size: 1.18rem;
      cursor: pointer;
    }}

    @media (max-width: 980px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .toolbar {{ position: static; }}
      .lightbox-shell {{
        grid-template-columns: 1fr;
        width: min(96vw, 720px);
      }}
      .lightbox-canvas {{ max-height: min(56vh, 520px); }}
      .lightbox-zoom {{
        margin-left: 0;
        width: 100%;
        justify-content: center;
      }}
      .lightbox-nav {{
        justify-content: center;
      }}
    }}
  </style>
</head>
<body>
  <main>
    {build_summary_cards(summary, sorted_rows)}
    <div class="layout">
      <section class="panel">
        <h2>Algorithm Assessment</h2>
        <table>
          <thead>
            <tr>
              <th>Algorithm</th>
              <th>Metric</th>
              <th>Status</th>
              <th>Availability</th>
              <th>Variation</th>
              <th>Signal Summary</th>
              <th>Why Helpful</th>
            </tr>
          </thead>
          <tbody>
            {build_algorithm_rows(algorithm_rows)}
          </tbody>
        </table>
      </section>
      {build_calibration_block(calibration)}
    </div>

    <section class="toolbar">
      <input id="search" type="search" placeholder="Search pot, variety, action..." />
      <select id="survivalFilter">
        <option value="all">All survival states</option>
        <option value="high">High</option>
        <option value="moderate">Moderate</option>
        <option value="low">Low</option>
      </select>
      <select id="actionFilter">
        <option value="all">All actions</option>
        {"".join(f"<option value='{attr_escape(action)}'>{html_escape(action)}</option>" for action in action_options)}
      </select>
      <div class="shown">Shown: <strong id="shownCount">{len(sorted_rows)}</strong></div>
    </section>
    <p class="muted" style="margin:8px 2px 0;">Tip: use <strong>Flip for metric meaning</strong> on any card for plain-language definitions.</p>

    <section class="pot-grid" id="potGrid">
      {build_card_html(sorted_rows)}
    </section>

    <div class="sources">
      <span>Metrics CSV: <code>{html_escape(str(source_metrics_csv))}</code></span>
      <span>Algorithm CSV: <code>{html_escape(str(source_algorithm_csv))}</code></span>
    </div>
  </main>

  <div id="lightbox" class="lightbox" aria-hidden="true">
    <button id="closeLightbox" class="close" type="button" aria-label="Close image">&times;</button>
    <div class="lightbox-shell">
      <section class="lightbox-media">
        <div id="lightboxCanvas" class="lightbox-canvas">
          <img id="lightboxImg" src="" alt="" />
        </div>
        <div class="lightbox-nav">
          <div class="lightbox-nav-main">
            <button id="prevLightbox" type="button" aria-label="Previous pot">Previous</button>
            <span id="lightboxCount">0 / 0</span>
            <button id="nextLightbox" type="button" aria-label="Next pot">Next</button>
          </div>
          <div class="lightbox-zoom" aria-label="Image zoom controls">
            <button id="zoomOutLightbox" type="button" aria-label="Zoom out">-</button>
            <button id="zoomResetLightbox" type="button" aria-label="Reset zoom">Reset</button>
            <button id="zoomInLightbox" type="button" aria-label="Zoom in">+</button>
            <span id="zoomLevelLightbox" class="zoom-level">100%</span>
          </div>
        </div>
      </section>
      <aside id="lightboxDetails" class="lightbox-details" aria-live="polite">
        <h3>Pot Detail</h3>
        <p class="meta">Select any photo card to load full notes.</p>
      </aside>
    </div>
  </div>

  <script>
    (() => {{
      const rows = {rows_json};
      const search = document.getElementById("search");
      const survivalFilter = document.getElementById("survivalFilter");
      const actionFilter = document.getElementById("actionFilter");
      const shownCount = document.getElementById("shownCount");
      const cards = Array.from(document.querySelectorAll(".pot-card"));
      const lightbox = document.getElementById("lightbox");
      const lightboxCanvas = document.getElementById("lightboxCanvas");
      const lightboxImg = document.getElementById("lightboxImg");
      const closeLightbox = document.getElementById("closeLightbox");
      const prevLightbox = document.getElementById("prevLightbox");
      const nextLightbox = document.getElementById("nextLightbox");
      const lightboxCount = document.getElementById("lightboxCount");
      const zoomOutLightbox = document.getElementById("zoomOutLightbox");
      const zoomResetLightbox = document.getElementById("zoomResetLightbox");
      const zoomInLightbox = document.getElementById("zoomInLightbox");
      const zoomLevelLightbox = document.getElementById("zoomLevelLightbox");
      const lightboxDetails = document.getElementById("lightboxDetails");
      const survivalHelp = {{
        high: "High means stronger canopy with stable or improving growth signal.",
        moderate: "Moderate means viable but still needs regular monitoring.",
        low: "Low means weak canopy or stress signals need intervention.",
        unknown: "Unknown means there is not enough signal for confidence yet.",
      }};
      const metricHelp = [
        "Coverage: green canopy area in the pot crop; higher means fuller foliage.",
        "Chlorosis: yellowing inside canopy; higher can indicate stress or nutrient issues.",
        "Growth: canopy coverage change versus the earliest baseline photo for this pot.",
        "Components: separate green blobs; often approximates distinct seedling clumps.",
        "Blur: focus score; higher means sharper images and stronger measurement reliability.",
      ];
      let lightboxVisibleCards = [];
      let lightboxIndex = -1;
      const ZOOM_MIN = 1;
      const ZOOM_MAX = 4;
      let zoomScale = ZOOM_MIN;
      let zoomX = 0;
      let zoomY = 0;
      let draggingPointerId = null;
      let dragLastX = 0;
      let dragLastY = 0;

      const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

      const clampPan = () => {{
        if (zoomScale <= ZOOM_MIN + 0.001) {{
          zoomX = 0;
          zoomY = 0;
          return;
        }}
        const canvasWidth = lightboxCanvas.clientWidth;
        const canvasHeight = lightboxCanvas.clientHeight;
        const baseWidth = lightboxImg.clientWidth;
        const baseHeight = lightboxImg.clientHeight;
        if (!canvasWidth || !canvasHeight || !baseWidth || !baseHeight) return;
        const maxX = Math.max(0, ((baseWidth * zoomScale) - canvasWidth) / 2);
        const maxY = Math.max(0, ((baseHeight * zoomScale) - canvasHeight) / 2);
        zoomX = clamp(zoomX, -maxX, maxX);
        zoomY = clamp(zoomY, -maxY, maxY);
      }};

      const updateZoomState = () => {{
        clampPan();
        lightboxImg.style.transform = `translate(${{zoomX.toFixed(1)}}px, ${{zoomY.toFixed(1)}}px) scale(${{zoomScale.toFixed(3)}})`;
        lightboxImg.classList.toggle("zoomed", zoomScale > ZOOM_MIN + 0.001);
        lightboxImg.classList.toggle("dragging", draggingPointerId !== null);
        zoomLevelLightbox.textContent = `${{Math.round(zoomScale * 100)}}%`;
        zoomOutLightbox.disabled = zoomScale <= ZOOM_MIN + 0.001;
        zoomInLightbox.disabled = zoomScale >= ZOOM_MAX - 0.001;
        zoomResetLightbox.disabled = zoomScale <= ZOOM_MIN + 0.001 && Math.abs(zoomX) < 0.5 && Math.abs(zoomY) < 0.5;
      }};

      const resetZoom = () => {{
        zoomScale = ZOOM_MIN;
        zoomX = 0;
        zoomY = 0;
        draggingPointerId = null;
        updateZoomState();
      }};

      const applyZoom = (nextScale, anchorClientX = null, anchorClientY = null) => {{
        const previousScale = zoomScale;
        zoomScale = clamp(nextScale, ZOOM_MIN, ZOOM_MAX);
        if (Math.abs(zoomScale - previousScale) < 0.001) {{
          updateZoomState();
          return;
        }}
        if (anchorClientX !== null && anchorClientY !== null && previousScale > 0) {{
          const canvasRect = lightboxCanvas.getBoundingClientRect();
          const deltaX = anchorClientX - (canvasRect.left + (canvasRect.width / 2));
          const deltaY = anchorClientY - (canvasRect.top + (canvasRect.height / 2));
          const ratio = zoomScale / previousScale;
          zoomX = (zoomX * ratio) + (deltaX * (ratio - 1));
          zoomY = (zoomY * ratio) + (deltaY * (ratio - 1));
        }}
        updateZoomState();
      }};

      const applyFilters = () => {{
        const q = (search.value || "").trim().toLowerCase();
        const survival = survivalFilter.value;
        const action = actionFilter.value;
        let shown = 0;
        for (const card of cards) {{
          const matchSearch = !q || (card.dataset.search || "").includes(q);
          const matchSurvival = survival === "all" || (card.dataset.survival === survival);
          const matchAction = action === "all" || (card.dataset.action === action);
          const visible = matchSearch && matchSurvival && matchAction;
          card.style.display = visible ? "" : "none";
          if (visible) shown += 1;
        }}
        shownCount.textContent = String(shown);
        if (lightbox.classList.contains("open")) {{
          const activeCard = lightboxVisibleCards[lightboxIndex];
          const visibleCards = cards.filter((card) => card.style.display !== "none");
          const nextIndex = activeCard ? visibleCards.indexOf(activeCard) : -1;
          if (!visibleCards.length || nextIndex < 0) {{
            close();
          }} else {{
            lightboxVisibleCards = visibleCards;
            lightboxIndex = nextIndex;
            renderLightbox();
          }}
        }}
      }};

      const escapeHtml = (value) =>
        String(value || "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");

      const toNum = (value) => {{
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
      }};

      const normalizeSurvival = (value) => {{
        const s = String(value || "").trim().toLowerCase();
        if (s === "high" || s === "moderate" || s === "low") return s;
        return "unknown";
      }};

      const pctText = (value, digits = 1) => {{
        const n = toNum(value);
        return n === null ? "n/a" : `${{(n * 100).toFixed(digits)}}%`;
      }};

      const growthText = (value) => {{
        const n = toNum(value);
        return n === null ? "n/a" : `${{(n * 100).toFixed(1)}}%`;
      }};

      const renderDetails = (card, row) => {{
        const potId = (row && row.pot_id) || card.dataset.potId || "n/a";
        const variety = (row && row.variety_name) || card.querySelector("h3")?.textContent || "Unknown variety";
        const survival = normalizeSurvival((row && row.survival_hypothesis) || card.dataset.survival || "");
        const actionCode = (row && row.action_code) || card.dataset.action || "n/a";
        const actionText = (row && row.action_recommendation) || card.querySelector(".action-text")?.textContent || "No recommendation available.";
        const health = toNum(row && row.health_score);
        const coverage = pctText(row && row.vegetation_coverage);
        const chlorosis = pctText(row && row.chlorosis_ratio);
        const growth = growthText(row && row.growth_delta);
        const plants = row && row.plant_count_estimate ? String(row.plant_count_estimate) : "n/a";
        const components = row && row.canopy_components ? String(row.canopy_components) : "n/a";
        const blurValue = toNum(row && row.blur_score);
        const blur = blurValue === null ? "n/a" : `${{Math.round(blurValue)}}`;
        const captureDate = row && row.capture_date ? String(row.capture_date) : "n/a";
        const survivalLabel = survival.charAt(0).toUpperCase() + survival.slice(1);

        lightboxDetails.innerHTML =
          `<h3>Pot ${{escapeHtml(potId)}}: ${{escapeHtml(variety)}}</h3>` +
          `<p class='meta'>Captured: <strong>${{escapeHtml(captureDate)}}</strong> ` +
          `Survival: <span class='survival-pill ${{escapeHtml(survival)}}'>${{escapeHtml(survivalLabel)}}</span></p>` +
          `<dl>` +
            `<div><dt>Pot ID</dt><dd>${{escapeHtml(potId)}}</dd></div>` +
            `<div><dt>Health</dt><dd>${{health === null ? "n/a" : health.toFixed(1)}}</dd></div>` +
            `<div><dt>Coverage</dt><dd>${{coverage}}</dd></div>` +
            `<div><dt>Chlorosis</dt><dd>${{chlorosis}}</dd></div>` +
            `<div><dt>Growth</dt><dd>${{escapeHtml(growth)}}</dd></div>` +
            `<div><dt>Plants</dt><dd>${{escapeHtml(plants)}}</dd></div>` +
            `<div><dt>Components</dt><dd>${{escapeHtml(components)}}</dd></div>` +
            `<div><dt>Blur</dt><dd>${{escapeHtml(blur)}}</dd></div>` +
            `<div><dt>Action Code</dt><dd>${{escapeHtml(actionCode)}}</dd></div>` +
          `</dl>` +
          `<p class='action-full'><strong>Action recommendation:</strong> ${{escapeHtml(actionText)}}</p>` +
          `<p class='action-full'><strong>Category meaning:</strong> ${{escapeHtml(survivalHelp[survival])}}</p>` +
          `<ul>${{metricHelp.map((line) => `<li>${{escapeHtml(line)}}</li>`).join("")}}</ul>`;
      }};

      const renderLightbox = () => {{
        if (lightboxIndex < 0 || lightboxIndex >= lightboxVisibleCards.length) return;
        const card = lightboxVisibleCards[lightboxIndex];
        const img = card.querySelector("img[data-open='1']");
        if (!img) return;
        const nextSrc = img.getAttribute("src") || "";
        const changedImage = lightboxImg.getAttribute("src") !== nextSrc;
        lightboxImg.src = nextSrc;
        lightboxImg.alt = img.getAttribute("alt") || "Pot image";
        lightboxCount.textContent = `${{lightboxIndex + 1}} / ${{lightboxVisibleCards.length}}`;
        prevLightbox.disabled = lightboxIndex <= 0;
        nextLightbox.disabled = lightboxIndex >= lightboxVisibleCards.length - 1;
        if (changedImage) resetZoom();
        const rowIndex = Number(card.dataset.rowIndex);
        const row = Number.isInteger(rowIndex) && rowIndex >= 0 && rowIndex < rows.length
          ? rows[rowIndex]
          : undefined;
        renderDetails(card, row);
      }};

      const openLightboxForCard = (card) => {{
        const visibleCards = cards.filter((item) => item.style.display !== "none");
        const index = visibleCards.indexOf(card);
        if (index < 0) return;
        const img = card.querySelector("img[data-open='1']");
        if (!img) return;
        lightboxVisibleCards = visibleCards;
        lightboxIndex = index;
        renderLightbox();
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
      }};

      const close = () => {{
        lightbox.classList.remove("open");
        lightbox.setAttribute("aria-hidden", "true");
        resetZoom();
        lightboxImg.src = "";
        lightboxImg.alt = "";
        lightboxVisibleCards = [];
        lightboxIndex = -1;
        document.body.style.overflow = "";
      }};

      const stepLightbox = (delta) => {{
        if (!lightbox.classList.contains("open")) return;
        const nextIndex = lightboxIndex + delta;
        if (nextIndex < 0 || nextIndex >= lightboxVisibleCards.length) return;
        lightboxIndex = nextIndex;
        renderLightbox();
      }};

      document.getElementById("potGrid").addEventListener("click", (event) => {{
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const flipBtn = target.closest("[data-flip='1']");
        if (flipBtn) {{
          const card = target.closest(".pot-card");
          if (card) card.classList.toggle("is-flipped");
          return;
        }}
        const img = target.closest("img[data-open='1']");
        if (!img) return;
        const card = img.closest(".pot-card");
        if (!card) return;
        openLightboxForCard(card);
      }});

      search.addEventListener("input", applyFilters);
      survivalFilter.addEventListener("change", applyFilters);
      actionFilter.addEventListener("change", applyFilters);
      closeLightbox.addEventListener("click", close);
      prevLightbox.addEventListener("click", () => stepLightbox(-1));
      nextLightbox.addEventListener("click", () => stepLightbox(1));
      zoomInLightbox.addEventListener("click", () => applyZoom(zoomScale * 1.2));
      zoomOutLightbox.addEventListener("click", () => applyZoom(zoomScale / 1.2));
      zoomResetLightbox.addEventListener("click", () => resetZoom());
      lightboxImg.addEventListener("load", () => updateZoomState());
      lightboxCanvas.addEventListener(
        "wheel",
        (event) => {{
          if (!lightbox.classList.contains("open")) return;
          event.preventDefault();
          const factor = event.deltaY < 0 ? 1.14 : (1 / 1.14);
          applyZoom(zoomScale * factor, event.clientX, event.clientY);
        }},
        {{ passive: false }}
      );
      lightboxCanvas.addEventListener("dblclick", (event) => {{
        if (!lightbox.classList.contains("open")) return;
        if (zoomScale > ZOOM_MIN + 0.001) {{
          resetZoom();
          return;
        }}
        applyZoom(2.0, event.clientX, event.clientY);
      }});
      lightboxImg.addEventListener("pointerdown", (event) => {{
        if (zoomScale <= ZOOM_MIN + 0.001) return;
        draggingPointerId = event.pointerId;
        dragLastX = event.clientX;
        dragLastY = event.clientY;
        lightboxImg.setPointerCapture(event.pointerId);
        updateZoomState();
      }});
      lightboxImg.addEventListener("pointermove", (event) => {{
        if (draggingPointerId !== event.pointerId) return;
        zoomX += event.clientX - dragLastX;
        zoomY += event.clientY - dragLastY;
        dragLastX = event.clientX;
        dragLastY = event.clientY;
        updateZoomState();
      }});
      const stopDrag = (event) => {{
        if (draggingPointerId !== event.pointerId) return;
        draggingPointerId = null;
        if (lightboxImg.hasPointerCapture(event.pointerId)) {{
          lightboxImg.releasePointerCapture(event.pointerId);
        }}
        updateZoomState();
      }};
      lightboxImg.addEventListener("pointerup", stopDrag);
      lightboxImg.addEventListener("pointercancel", stopDrag);
      lightbox.addEventListener("click", (event) => {{
        if (event.target === lightbox) close();
      }});
      document.addEventListener("keydown", (event) => {{
        if (!lightbox.classList.contains("open")) return;
        if (event.key === "Escape") {{
          close();
          return;
        }}
        if (event.key === "ArrowLeft") {{
          stepLightbox(-1);
          return;
        }}
        if (event.key === "ArrowRight") {{
          stepLightbox(1);
          return;
        }}
        if (event.key === "+" || event.key === "=") {{
          event.preventDefault();
          applyZoom(zoomScale * 1.2);
          return;
        }}
        if (event.key === "-" || event.key === "_") {{
          event.preventDefault();
          applyZoom(zoomScale / 1.2);
          return;
        }}
        if (event.key === "0") {{
          event.preventDefault();
          resetZoom();
        }}
      }});

      resetZoom();
      applyFilters();
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a visual HTML page from v1.4 CV research outputs."
    )
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=Path("data/research/v1_4/cv_experiment_results.csv"),
        help="CSV containing per-pot CV metrics and recommendations.",
    )
    parser.add_argument(
        "--algorithm-csv",
        type=Path,
        default=Path("data/research/v1_4/algorithm_assessment.csv"),
        help="CSV containing algorithm-level assessments.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/research/v1_4/research_summary.json"),
        help="Research summary JSON.",
    )
    parser.add_argument(
        "--calibration-json",
        type=Path,
        default=Path("data/research/v1_4/calibration_summary.json"),
        help="Optional calibration summary JSON.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/v1-4-cv-research.html"),
        help="Output HTML page path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    metrics_rows = read_csv_rows(args.metrics_csv)
    algorithm_rows = read_csv_rows(args.algorithm_csv)
    summary = read_json_optional(args.summary_json)
    calibration = read_json_optional(args.calibration_json)

    page = build_page(
        metrics_rows=metrics_rows,
        algorithm_rows=algorithm_rows,
        summary=summary,
        calibration=calibration,
        source_metrics_csv=args.metrics_csv,
        source_algorithm_csv=args.algorithm_csv,
    )
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"metrics_rows={len(metrics_rows)}")
    print(f"algorithm_rows={len(algorithm_rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
