#!/usr/bin/env python3
"""Generate a view-only web page for experiment trails data."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from build_experiment_trails_label_editor_page import build_editor_rows


def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def attr_escape(value: str) -> str:
    return html_escape(value).replace("'", "&#39;")


def normalize_label(label: str) -> str:
    cleaned = (label or "").strip()
    return cleaned if cleaned in {"tomato", "non_tomato", "unknown"} else "unknown"


def label_title(label: str) -> str:
    if label == "non_tomato":
        return "Non-Tomato"
    if label == "tomato":
        return "Tomato"
    return "Needs Review"


def to_confidence_percent(conf: str) -> int:
    text = (conf or "").strip()
    if not text:
        return 0
    try:
        return max(0, min(100, int(round(float(text) * 100))))
    except ValueError:
        return 0


def row_id(index: int) -> str:
    return f"row-{index:03d}"


def build_gallery_cards(rows: List[Dict[str, str]]) -> str:
    cards: List[str] = []
    for idx, row in enumerate(rows, start=1):
        label = normalize_label((row.get("classification_label") or "").strip())
        status_label = (row.get("review_status_label") or "").strip()
        common_name = html_escape((row.get("species_common_name") or "unknown").strip())
        variety = html_escape((row.get("variety_name") or "").strip())
        scientific = html_escape((row.get("species_scientific_name") or "").strip())
        specific_note = html_escape((row.get("specific_note") or "").strip())
        weather = html_escape((row.get("weather_hypothesis") or "").strip())
        harvest = html_escape((row.get("expected_harvest_window") or "").strip())
        caption = html_escape((row.get("caption") or "").strip())
        date = html_escape((row.get("capture_date") or "").strip())
        photo_url = html_escape((row.get("photo_url") or "").strip())
        asset = html_escape((row.get("source_asset_id") or "").strip())
        species_attr = attr_escape((row.get("species_common_name") or "unknown").strip().lower())
        variety_attr = attr_escape((row.get("variety_name") or "").strip().lower())
        scientific_attr = attr_escape((row.get("species_scientific_name") or "").strip().lower())
        note_attr = attr_escape((row.get("specific_note") or "").strip().lower())
        weather_attr = attr_escape((row.get("weather_hypothesis") or "").strip().lower())
        harvest_attr = attr_escape((row.get("expected_harvest_window") or "").strip().lower())
        caption_attr = attr_escape((row.get("caption") or "").strip().lower())
        asset_attr = attr_escape((row.get("source_asset_id") or "").strip().lower())
        title = status_label or label_title(label)
        cards.append(
            f'<article class="photo-card" data-id="{row_id(idx)}" data-label="{label}" '
            f'data-species="{species_attr}" data-variety="{variety_attr}" data-scientific="{scientific_attr}" '
            f'data-note="{note_attr}" data-weather="{weather_attr}" data-harvest="{harvest_attr}" '
            f'data-caption="{caption_attr}" data-asset="{asset_attr}" data-row-index="{idx}">'
            f"<div class='photo-wrap' data-open-lightbox='true' role='button' tabindex='0' aria-label='Open full photo for row {idx}'>{f'<img src=\"{photo_url}\" alt=\"{common_name}\" loading=\"lazy\" />' if photo_url else '<div class=\"photo-missing\">No photo URL</div>'}</div>"
            "<div class='photo-meta'>"
            f"<span class='badge {label}'>{html_escape(title)}</span>"
            f"<h3>{variety or common_name}</h3>"
            f"<p class='sub'>{common_name} {f'| <em>{scientific}</em>' if scientific else ''}</p>"
            f"<p class='summary'>{specific_note or caption or 'No specific note'}</p>"
            f"<p class='weather'>{weather or 'No weather hypothesis'}</p>"
            "<div class='meta-row'>"
            f"<span>{harvest or 'Harvest n/a'}</span>"
            f"<span>{date or 'n/a'}</span>"
            f"<span>{asset[:10]}...</span>"
            "</div>"
            "</div>"
            "</article>"
        )
    return "\n".join(cards) if cards else "<p class='empty'>No rows found.</p>"


def build_table_rows(rows: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, row in enumerate(rows, start=1):
        label = normalize_label((row.get("classification_label") or "").strip())
        status_label = (row.get("review_status_label") or "").strip()
        label_text = html_escape(status_label or label_title(label))
        date = html_escape((row.get("capture_date") or "").strip())
        common_name = html_escape((row.get("species_common_name") or "").strip())
        variety = html_escape((row.get("variety_name") or "").strip())
        scientific = html_escape((row.get("species_scientific_name") or "").strip())
        specific_note = html_escape((row.get("specific_note") or "").strip())
        weather = html_escape((row.get("weather_hypothesis") or "").strip())
        harvest = html_escape((row.get("expected_harvest_window") or "").strip())
        caption = html_escape((row.get("caption") or "").strip())
        confidence = html_escape((row.get("confidence") or "").strip())
        confidence_pct = to_confidence_percent(confidence)
        asset = html_escape((row.get("source_asset_id") or "").strip())
        method = html_escape((row.get("labeling_method") or "").strip())
        photo_url = html_escape((row.get("photo_url") or "").strip())
        species_attr = attr_escape((row.get("species_common_name") or "").strip().lower())
        variety_attr = attr_escape((row.get("variety_name") or "").strip().lower())
        scientific_attr = attr_escape((row.get("species_scientific_name") or "").strip().lower())
        note_attr = attr_escape((row.get("specific_note") or "").strip().lower())
        weather_attr = attr_escape((row.get("weather_hypothesis") or "").strip().lower())
        harvest_attr = attr_escape((row.get("expected_harvest_window") or "").strip().lower())
        caption_attr = attr_escape((row.get("caption") or "").strip().lower())
        asset_attr = attr_escape((row.get("source_asset_id") or "").strip().lower())
        thumb = (
            f"<a href=\"{photo_url}\" class=\"thumb-link\" data-open-lightbox=\"true\" aria-label=\"Open full photo for row {idx}\">"
            f"<img src=\"{photo_url}\" alt=\"{common_name}\" loading=\"lazy\" class=\"thumb\" />"
            "</a>"
            if photo_url
            else ""
        )

        lines.append(
            f'<tr data-id="{row_id(idx)}" data-label="{label}" '
            f'data-species="{species_attr}" data-variety="{variety_attr}" data-scientific="{scientific_attr}" '
            f'data-note="{note_attr}" data-weather="{weather_attr}" data-harvest="{harvest_attr}" '
            f'data-caption="{caption_attr}" data-asset="{asset_attr}" data-row-index="{idx}">'
            f"<td><span class='badge {label}'>{label_text}</span></td>"
            f"<td>{thumb}</td>"
            f"<td>{date}</td>"
            f"<td>{common_name}</td>"
            f"<td>{variety}</td>"
            f"<td>{scientific}</td>"
            f"<td class='long'>{specific_note}</td>"
            f"<td class='long'>{weather}</td>"
            f"<td class='long'>{harvest}</td>"
            f"<td class='caption'>{caption}</td>"
            "<td>"
            f"<span class='conf-text'>{confidence}</span>"
            f"<div class='conf'><div style='width:{confidence_pct}%'></div></div>"
            "</td>"
            f"<td>{asset}</td>"
            f"<td>{method}</td>"
            "</tr>"
        )
    return "\n".join(lines) if lines else "<tr><td colspan='13'>No rows.</td></tr>"


def build_species_chips(counter: Counter[str]) -> str:
    chips: List[str] = []
    for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        chips.append(
            "<div class='chip'>"
            f"<span>{html_escape(name)}</span>"
            f"<strong>{count}</strong>"
            "</div>"
        )
    return "\n".join(chips) if chips else "<p class='empty'>No rows.</p>"


def build_page(rows: List[Dict[str, str]], source_csv: Path) -> str:
    rows = build_editor_rows(rows)
    now_iso = datetime.now(timezone.utc).isoformat()
    rows_json = json.dumps(rows, ensure_ascii=True)
    label_counts = Counter(normalize_label((row.get("classification_label") or "").strip()) for row in rows)
    non_tomato_species = Counter(
        (row.get("species_common_name") or "unknown").strip()
        for row in rows
        if normalize_label((row.get("classification_label") or "").strip()) == "non_tomato"
    )

    dates = sorted((row.get("capture_date") or "").strip() for row in rows if (row.get("capture_date") or "").strip())
    date_range = f"{dates[0]} to {dates[-1]}" if dates else "n/a"
    reviewed = label_counts.get("tomato", 0) + label_counts.get("non_tomato", 0)
    completion = round((reviewed / len(rows)) * 100) if rows else 0

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>K's Experiment Trails - View-Only Catalog</title>
  <style>
    :root {{
      --bg: #f4f0e3;
      --card: #fffdf7;
      --ink: #1f2b29;
      --muted: #5f6d68;
      --line: #d8d1c2;
      --tomato: #8a2d2b;
      --leaf: #2f6947;
      --amber: #8a5c23;
      --sky: #35597f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 400px at 110% -10%, #dfd8c4 0%, transparent 65%),
        radial-gradient(900px 400px at -10% 110%, #e7dcc5 0%, transparent 65%),
        linear-gradient(145deg, #f3f0e3, #ece5d4);
    }}
    .wrap {{ max-width: 1240px; margin: 0 auto; padding: 22px 14px 36px; }}
    .hero {{
      background: linear-gradient(120deg, rgba(47, 105, 71, 0.12), rgba(138, 45, 43, 0.08));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      font-size: clamp(1.35rem, 3vw, 2.2rem);
    }}
    .sub {{ margin: 0; color: var(--muted); }}
    .meta {{ margin-top: 8px; color: #465550; font-size: 0.9rem; display: flex; flex-wrap: wrap; gap: 8px 14px; }}

    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-bottom: 12px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; }}
    .label {{ text-transform: uppercase; font-size: 0.76rem; color: var(--muted); letter-spacing: 0.07em; }}
    .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; }}
    .value.tomato {{ color: var(--tomato); }}
    .value.non {{ color: var(--leaf); }}
    .value.rev {{ color: var(--amber); }}
    .value.all {{ color: var(--sky); }}

    .completion {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; margin-bottom: 12px; }}
    .meter {{ height: 12px; background: #ece7d8; border-radius: 999px; overflow: hidden; margin-top: 7px; }}
    .meter > div {{ height: 100%; width: {completion}%; background: linear-gradient(90deg, #2f6947, #4e8a66); }}

    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }}
    section {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
    h2 {{ margin: 0 0 10px; font-size: 0.98rem; color: #45544f; text-transform: uppercase; letter-spacing: 0.06em; }}

    .chips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }}
    .chip {{ border: 1px solid #dfd8c8; border-radius: 10px; padding: 8px; display: flex; justify-content: space-between; gap: 8px; }}
    .chip span {{ color: #465650; font-size: 0.85rem; }}

    .toolbar {{
      position: sticky;
      top: 8px;
      z-index: 5;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
    }}
    .toolbar input {{
      flex: 1;
      min-width: 220px;
      border: 1px solid #cfc7b7;
      border-radius: 8px;
      padding: 8px 10px;
      font: inherit;
      background: #fffef9;
      color: var(--ink);
    }}
    .filter {{ border: 1px solid #d2cab9; background: #fffef9; border-radius: 999px; padding: 6px 10px; font-size: 0.82rem; cursor: pointer; }}
    .filter.active {{ background: #385f56; color: #fff; border-color: #385f56; }}
    .shown {{ margin-left: auto; font-size: 0.84rem; color: #475752; }}

    .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-bottom: 12px; }}
    .photo-card {{ border: 1px solid var(--line); border-radius: 12px; background: var(--card); overflow: hidden; }}
    .photo-wrap {{ aspect-ratio: 4 / 3; background: #ece6d7; cursor: zoom-in; }}
    .photo-wrap img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .photo-missing {{ height: 100%; display: grid; place-items: center; color: #6b7873; font-size: 0.85rem; }}
    .photo-meta {{ padding: 8px 10px 10px; }}
    .photo-meta h3 {{ margin: 7px 0 4px; font-size: 0.95rem; }}
    .photo-meta p {{ margin: 0; color: #5a6964; font-size: 0.82rem; }}
    .photo-meta .sub {{ margin-top: 6px; color: #4a5d58; }}
    .photo-meta .summary {{ margin-top: 6px; min-height: 2.4em; }}
    .photo-meta .weather {{ margin-top: 6px; color: #485c57; min-height: 2.4em; }}
    .meta-row {{ margin-top: 7px; display: flex; flex-wrap: wrap; gap: 6px 10px; color: #667670; font-size: 0.76rem; }}

    .badge {{ border-radius: 999px; padding: 3px 7px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; display: inline-block; }}
    .badge.tomato {{ background: #f9e5e2; color: #7f2325; border: 1px solid #edc6bf; }}
    .badge.non_tomato {{ background: #e6f3e9; color: #1d5c37; border: 1px solid #c9e3d0; }}
    .badge.unknown {{ background: #faecd5; color: #764813; border: 1px solid #efce9b; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; display: block; overflow-x: auto; background: var(--card); border: 1px solid var(--line); border-radius: 12px; }}
    th, td {{ border-bottom: 1px solid #ece6d8; text-align: left; padding: 7px 7px; vertical-align: top; white-space: nowrap; }}
    th {{ position: sticky; top: 0; background: #f5f0e4; z-index: 2; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #55645f; }}
    .thumb {{ width: 62px; height: 46px; object-fit: cover; border-radius: 6px; border: 1px solid #d4cdbc; display: block; }}
    .thumb-link {{ cursor: zoom-in; display: inline-block; }}
    .caption {{ max-width: 240px; white-space: normal; }}
    .long {{ max-width: 320px; white-space: normal; }}
    .conf-text {{ display: block; font-size: 0.78rem; color: #556660; margin-bottom: 3px; }}
    .conf {{ width: 92px; height: 7px; background: #ece7d7; border-radius: 999px; overflow: hidden; }}
    .conf > div {{ height: 100%; background: linear-gradient(90deg, #40658f, #6c8eb2); }}

    .note {{ color: #5f6e69; font-size: 0.82rem; margin-top: 8px; }}
    .empty {{ color: #677670; font-style: italic; }}

    .lightbox {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 14px;
      background: rgba(9, 13, 12, 0.86);
      z-index: 40;
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-inner {{
      position: relative;
      width: min(96vw, 1680px);
      height: min(94vh, 940px);
      max-height: 94vh;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      gap: 10px;
    }}
    .lightbox-panel {{
      display: grid;
      grid-template-columns: minmax(420px, 60%) minmax(320px, 40%);
      background: var(--card);
      border: 1px solid #d8cfbb;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 20px 46px rgba(0, 0, 0, 0.44);
      min-height: 0;
      height: 100%;
    }}
    .lightbox-photo {{
      background: #111312;
      display: grid;
      place-items: center;
      min-height: 0;
      padding: 8px;
    }}
    .lightbox-img {{
      width: 100%;
      height: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
    }}
    .lightbox-meta {{
      max-height: none;
      min-height: 0;
      height: 100%;
      overflow: auto;
      padding: 12px;
      background: #fffdf7;
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .lightbox-meta h3 {{
      margin: 0;
      font-size: 1.05rem;
      color: #243634;
    }}
    .lightbox-meta .kv {{
      margin: 0;
      display: grid;
      gap: 5px;
    }}
    .lightbox-meta dt {{
      font-size: 0.7rem;
      color: #5e6c67;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .lightbox-meta dd {{
      margin: 0;
      color: #22302d;
      font-size: 0.88rem;
      line-height: 1.36;
      white-space: pre-wrap;
    }}
    .lightbox-nav {{
      margin-top: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }}
    .lightbox-nav-btn {{
      border: 1px solid #d7cfbe;
      border-radius: 999px;
      background: #f7f4ec;
      color: #1f2a28;
      font: inherit;
      font-size: 0.84rem;
      padding: 7px 12px;
      cursor: pointer;
    }}
    .lightbox-nav-btn:disabled {{
      opacity: 0.45;
      cursor: not-allowed;
    }}
    .lightbox-nav-status {{
      color: #f5f3ea;
      font-size: 0.86rem;
      min-width: 120px;
      text-align: center;
    }}
    .lightbox-close {{
      position: absolute;
      top: -10px;
      right: -10px;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      border: 1px solid #f0e9d7;
      background: #183b33;
      color: #ffffff;
      font-size: 1.2rem;
      line-height: 1;
      cursor: pointer;
    }}

    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ position: static; }}
      .lightbox {{ padding: 10px; }}
      .lightbox-inner {{ height: min(94vh, 760px); }}
      .lightbox-panel {{
        grid-template-columns: 1fr;
        grid-template-rows: minmax(0, 1fr) auto;
      }}
      .lightbox-photo {{ min-height: 0; }}
      .lightbox-img {{
        height: auto;
        max-height: min(50vh, 420px);
      }}
      .lightbox-meta {{
        height: auto;
        max-height: min(38vh, 320px);
      }}
      .lightbox-nav {{ margin-top: 8px; }}
      .lightbox-nav-btn {{ padding: 7px 10px; font-size: 0.8rem; }}
      .lightbox-nav-status {{ min-width: 100px; font-size: 0.82rem; }}
      .lightbox-close {{
        top: 8px;
        right: 8px;
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <header class="hero">
      <h1>K's Experiment Trails 2026: View-Only Catalog</h1>
      <p class="sub">Read-only photo catalog with canonical variety, taxonomy, weather hypothesis, and harvest window fields.</p>
      <div class="meta">
        <span>Capture window: <strong>{html_escape(date_range)}</strong></span>
        <span>Generated (UTC): <strong>{html_escape(now_iso)}</strong></span>
      </div>
    </header>

    <div class="cards">
      <div class="card"><div class="label">Total Photos</div><div class="value all">{len(rows)}</div></div>
      <div class="card"><div class="label">Tomato</div><div class="value tomato">{label_counts.get('tomato', 0)}</div></div>
      <div class="card"><div class="label">Non-Tomato</div><div class="value non">{label_counts.get('non_tomato', 0)}</div></div>
      <div class="card"><div class="label">Needs Review</div><div class="value rev">{label_counts.get('unknown', 0)}</div></div>
    </div>

    <div class="completion">
      <div class="label">Classification Completion</div>
      <div class="value non">{completion}%</div>
      <div class="meter"><div></div></div>
      <div class="note">{reviewed} of {len(rows)} rows classified.</div>
    </div>

    <div class="grid">
      <section>
        <h2>Non-Tomato Species Mix</h2>
        <div class="chips">{build_species_chips(non_tomato_species)}</div>
      </section>
      <section>
        <h2>Quick Tip</h2>
        <p class="note" style="margin-top:0">This page is view-only. Use the label editor page for corrections, then regenerate this page to review finalized values.</p>
      </section>
    </div>

    <div class="toolbar">
      <input id="search" type="search" placeholder="Search common name, variety, scientific name, note, weather, harvest, caption, asset..." />
      <button class="filter active" data-filter="all">All</button>
      <button class="filter" data-filter="tomato">Tomato</button>
      <button class="filter" data-filter="non_tomato">Non-Tomato</button>
      <button class="filter" data-filter="unknown">Needs Review</button>
      <div class="shown">Shown: <strong id="shown-count">{len(rows)}</strong></div>
    </div>

    <section>
      <h2>Photo Gallery (View Only)</h2>
      <div class="gallery" id="gallery">
        {build_gallery_cards(rows)}
      </div>
    </section>

    <section>
      <h2>Detailed Rows</h2>
      <table>
        <thead>
          <tr>
            <th>Label</th>
            <th>Photo</th>
            <th>Date</th>
            <th>Common Name</th>
            <th>Variety</th>
            <th>Scientific Name</th>
            <th>Specific Note</th>
            <th>Weather Hypothesis</th>
            <th>Expected Harvest Window</th>
            <th>Caption</th>
            <th>Confidence</th>
            <th>Asset ID</th>
            <th>Method</th>
          </tr>
        </thead>
        <tbody id="rows-table">
          {build_table_rows(rows)}
        </tbody>
      </table>
    </section>

    <p class="note">Source CSV: {html_escape(str(source_csv))}</p>
  </main>
  <div id="lightbox" class="lightbox" aria-hidden="true" role="dialog" aria-modal="true" aria-label="Full photo view">
    <div class="lightbox-inner">
      <button id="lightboxClose" class="lightbox-close" type="button" aria-label="Close full photo">&times;</button>
      <div class="lightbox-panel">
        <div class="lightbox-photo">
          <img id="lightboxImg" class="lightbox-img" src="" alt="" />
        </div>
        <div id="lightboxMeta" class="lightbox-meta"></div>
      </div>
      <div class="lightbox-nav" aria-label="Photo navigation">
        <button id="lightboxPrev" class="lightbox-nav-btn" type="button" aria-label="Previous photo">&larr; Previous</button>
        <div id="lightboxNavStatus" class="lightbox-nav-status"></div>
        <button id="lightboxNext" class="lightbox-nav-btn" type="button" aria-label="Next photo">Next &rarr;</button>
      </div>
    </div>
  </div>

  <script>
    (() => {{
      const ROWS = {rows_json};
      const search = document.getElementById("search");
      const filters = Array.from(document.querySelectorAll(".filter"));
      const tableRows = Array.from(document.querySelectorAll("#rows-table tr[data-label]"));
      const cards = Array.from(document.querySelectorAll("#gallery .photo-card[data-label]"));
      const lightbox = document.getElementById("lightbox");
      const lightboxClose = document.getElementById("lightboxClose");
      const lightboxImg = document.getElementById("lightboxImg");
      const lightboxMeta = document.getElementById("lightboxMeta");
      const lightboxPrev = document.getElementById("lightboxPrev");
      const lightboxNext = document.getElementById("lightboxNext");
      const lightboxNavStatus = document.getElementById("lightboxNavStatus");
      const shown = document.getElementById("shown-count");
      const rowById = new Map(ROWS.map((row, index) => ["row-" + String(index + 1).padStart(3, "0"), row]));
      let activeFilter = "all";
      let lightboxId = null;

      const esc = (value) => String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");

      const apply = () => {{
        const q = (search.value || "").trim().toLowerCase();
        let visibleCount = 0;

        const check = (node) => {{
          const label = node.dataset.label || "";
          const haystack = [
            node.dataset.species || "",
            node.dataset.variety || "",
            node.dataset.scientific || "",
            node.dataset.note || "",
            node.dataset.weather || "",
            node.dataset.harvest || "",
            node.dataset.caption || "",
            node.dataset.asset || "",
          ].join(" ").toLowerCase();
          const labelOk = activeFilter === "all" || label === activeFilter;
          const queryOk = !q || haystack.includes(q);
          return labelOk && queryOk;
        }};

        const visibleIds = new Set();
        tableRows.forEach((row) => {{
          const show = check(row);
          row.style.display = show ? "" : "none";
          if (show) {{
            visibleCount += 1;
            visibleIds.add(row.dataset.id);
          }}
        }});

        cards.forEach((card) => {{
          card.style.display = visibleIds.has(card.dataset.id) ? "" : "none";
        }});

        shown.textContent = String(visibleCount);
        if (lightbox.classList.contains("open")) updateLightboxNav();
      }};

      const getVisiblePhotoIds = () => {{
        const visible = cards
          .filter((card) => card.style.display !== "none")
          .map((card) => card.dataset.id)
          .filter((id) => Boolean((rowById.get(id)?.photo_url || "").trim()));
        if (visible.length > 0) return visible;
        return cards
          .map((card) => card.dataset.id)
          .filter((id) => Boolean((rowById.get(id)?.photo_url || "").trim()));
      }};

      const updateLightboxNav = () => {{
        if (!lightbox.classList.contains("open") || !lightboxId) return;
        const ids = getVisiblePhotoIds();
        const position = ids.indexOf(lightboxId);
        lightboxPrev.disabled = position <= 0;
        lightboxNext.disabled = position < 0 || position >= ids.length - 1;
        lightboxNavStatus.textContent = position >= 0
          ? `Image ${{position + 1}} of ${{ids.length}}`
          : `${{ids.length}} images`;
      }};

      const renderLightboxMeta = (row) => {{
        const fallbackLabel = row.classification_label === "tomato"
          ? "Tomato"
          : row.classification_label === "non_tomato"
            ? "Non-Tomato"
            : "Needs Review";
        const statusLabel = row.review_status_label || fallbackLabel;
        const reviewStage = row.review_stage || "";
        const resolutionSource = row.resolution_source || "";
        const reviewStageRow = reviewStage && reviewStage !== "none"
          ? `<dt>Review Stage</dt><dd>${{esc(reviewStage)}}</dd>`
          : "";
        const resolutionSourceRow = resolutionSource
          ? `<dt>Resolution Source</dt><dd>${{esc(resolutionSource.replaceAll("_", " "))}}</dd>`
          : "";
        const contextIdRow = row.context_id
          ? `<dt>Context</dt><dd>${{esc(row.context_id)}}</dd>`
          : "";
        return `
          <span class="badge ${{esc(row.classification_label || "unknown")}}">${{esc(statusLabel)}}</span>
          <h3>${{esc(row.variety_name || row.species_common_name || "Unknown")}}</h3>
          <dl class="kv">
            <dt>Status</dt><dd>${{esc(statusLabel)}}</dd>
            ${{reviewStageRow}}
            ${{resolutionSourceRow}}
            ${{contextIdRow}}
            <dt>Common Name</dt><dd>${{esc(row.species_common_name || "")}}</dd>
            <dt>Variety</dt><dd>${{esc(row.variety_name || "")}}</dd>
            <dt>Scientific Name</dt><dd>${{esc(row.species_scientific_name || "")}}</dd>
            <dt>Specific Note</dt><dd>${{esc(row.specific_note || "")}}</dd>
            <dt>Weather Hypothesis</dt><dd>${{esc(row.weather_hypothesis || "")}}</dd>
            <dt>Expected Harvest Window</dt><dd>${{esc(row.expected_harvest_window || "")}}</dd>
            <dt>Caption</dt><dd>${{esc(row.caption || "")}}</dd>
            <dt>Date</dt><dd>${{esc(row.capture_date || "")}}</dd>
            <dt>Confidence</dt><dd>${{esc(row.confidence || "")}}</dd>
            <dt>Method</dt><dd>${{esc(row.labeling_method || "")}}</dd>
            <dt>Asset ID</dt><dd>${{esc(row.source_asset_id || "")}}</dd>
          </dl>
        `;
      }};

      const openLightbox = (id) => {{
        const row = rowById.get(id);
        if (!row || !row.photo_url) return;
        lightboxId = id;
        lightboxImg.src = row.photo_url;
        lightboxImg.alt = row.variety_name || row.species_common_name || "plant photo";
        lightboxMeta.innerHTML = renderLightboxMeta(row);
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        updateLightboxNav();
      }};

      const closeLightbox = () => {{
        if (!lightbox.classList.contains("open")) return;
        lightbox.classList.remove("open");
        lightbox.setAttribute("aria-hidden", "true");
        lightboxImg.removeAttribute("src");
        lightboxImg.alt = "";
        lightboxMeta.innerHTML = "";
        lightboxNavStatus.textContent = "";
        lightboxId = null;
        document.body.style.overflow = "";
      }};

      const moveLightbox = (delta) => {{
        if (!lightbox.classList.contains("open") || !lightboxId) return;
        const ids = getVisiblePhotoIds();
        const currentPosition = ids.indexOf(lightboxId);
        if (currentPosition < 0) return;
        const targetPosition = currentPosition + delta;
        if (targetPosition < 0 || targetPosition >= ids.length) return;
        openLightbox(ids[targetPosition]);
      }};

      search.addEventListener("input", apply);
      filters.forEach((btn) => {{
        btn.addEventListener("click", () => {{
          filters.forEach((node) => node.classList.remove("active"));
          btn.classList.add("active");
          activeFilter = btn.dataset.filter || "all";
          apply();
        }});
      }});

      cards.forEach((card) => {{
        const id = card.dataset.id;
        const trigger = card.querySelector("[data-open-lightbox='true']");
        if (!id || !trigger) return;
        trigger.addEventListener("click", () => openLightbox(id));
        trigger.addEventListener("keydown", (event) => {{
          if (event.key === "Enter" || event.key === " ") {{
            event.preventDefault();
            openLightbox(id);
          }}
        }});
      }});

      tableRows.forEach((rowNode) => {{
        const id = rowNode.dataset.id;
        const link = rowNode.querySelector(".thumb-link");
        if (!id || !link) return;
        link.addEventListener("click", (event) => {{
          event.preventDefault();
          openLightbox(id);
        }});
      }});

      lightboxClose.addEventListener("click", closeLightbox);
      lightboxPrev.addEventListener("click", () => moveLightbox(-1));
      lightboxNext.addEventListener("click", () => moveLightbox(1));
      lightbox.addEventListener("click", (event) => {{
        if (event.target === lightbox) closeLightbox();
      }});
      document.addEventListener("keydown", (event) => {{
        if (event.key === "Escape") {{
          closeLightbox();
          return;
        }}
        if (!lightbox.classList.contains("open")) return;
        const target = event.target;
        const typingContext = target instanceof HTMLElement
          && (target.matches("input, textarea, select") || target.isContentEditable);
        if (typingContext) return;
        if (event.key === "ArrowLeft") {{
          event.preventDefault();
          moveLightbox(-1);
        }} else if (event.key === "ArrowRight") {{
          event.preventDefault();
          moveLightbox(1);
        }}
      }});

      apply();
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a view-only web page for current experiment trails labels."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="OCR-labeled CSV input",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/experiment-trails-view.html"),
        help="Output HTML page",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.input_csv)
    page = build_page(rows, args.input_csv)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
