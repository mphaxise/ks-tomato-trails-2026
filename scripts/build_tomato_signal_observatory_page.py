#!/usr/bin/env python3
"""Build a visual observatory page for the latest tomato photo batch."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from build_pot_run_comparison_page import (
    CONTINUITY_SOURCES,
    available_run_dates,
    choose_expected_for_run,
    compare_status,
    is_ocr_confirmed,
    normalize_pot_id,
    pot_sort_key,
    resolve_run_dates,
    row_by_pot,
)
from build_tomato_pot_mapping import (
    build_mapping,
    load_baseline_variety_map,
    load_pot_series_overrides,
    load_row_overrides,
    load_series_variety_map,
    read_rows,
)

STATUS_LABELS = {
    "risk": "continuity lock",
    "drift": "variety drift",
    "info": "partial OCR",
    "warn": "continuity mapped",
    "ok": "OCR confirmed",
}

STATUS_ORDER = {
    "risk": 0,
    "drift": 1,
    "info": 2,
    "warn": 3,
    "ok": 4,
}


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


def short_date(run_date: str) -> str:
    try:
        parsed = datetime.strptime(run_date, "%Y-%m-%d")
    except ValueError:
        return run_date
    return parsed.strftime("%b %d").replace(" 0", " ")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def continuity_total(report: Dict[str, object]) -> int:
    value = report.get("resolution_source_counts", {})
    if not isinstance(value, dict):
        return 0
    return sum(int(value.get(key, 0) or 0) for key in CONTINUITY_SOURCES)


def rows_for_date(rows: List[Dict[str, str]], run_date: str) -> int:
    return sum(
        1
        for row in rows
        if (row.get("capture_date", "") or "").strip() == run_date
    )


def map_warning_rows(warnings: List[str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    pattern = re.compile(r"\bpot\s+([0-9]{1,3}T)\b", re.IGNORECASE)
    for warning in warnings:
        matched = pattern.search(warning)
        if not matched:
            continue
        pot_id = normalize_pot_id(matched.group(1))
        if not pot_id:
            continue
        out.setdefault(pot_id, []).append(warning)
    return out


def build_run_bundle(
    rows: List[Dict[str, str]],
    run_date: str,
    expected_pots: int,
    series_variety_map: Dict[int, str],
    pot_series_overrides: Dict[str, int],
    baseline_variety_map: Dict[str, str],
    row_overrides: Dict[Tuple[str, str, str], Dict[str, object]],
) -> Tuple[Dict[str, object], Dict[str, Dict[str, str]], Dict[str, object]]:
    expected_for_run = choose_expected_for_run(rows, run_date, expected_pots)
    mapped_rows, report = build_mapping(
        rows=rows,
        run_date=run_date,
        expected_pots=expected_for_run,
        potting_date="2026-02-24",
        day_one_photo_date="2026-02-25",
        lifecycle_stage="sapling",
        assume_sequential_pot_ids=True,
        tomato_only_run=True,
        series_variety_map=series_variety_map,
        pot_series_overrides=pot_series_overrides,
        baseline_variety_map=baseline_variety_map,
        baseline_reconcile=True,
        context_id="context_default",
        row_overrides=row_overrides,
    )
    summary = {
        "run_date": run_date,
        "short_date": short_date(run_date),
        "photo_rows": rows_for_date(rows, run_date),
        "mapped_pots": int(report.get("unique_pot_count", 0) or 0),
        "ocr_confirmed_rows": int(report.get("ocr_confirmed_rows", 0) or 0),
        "continuity_rows": continuity_total(report),
        "warning_count": len(report.get("warnings", []))
        if isinstance(report.get("warnings", []), list)
        else 0,
    }
    summary["batch_mode"] = "census" if summary["photo_rows"] == expected_pots else "mixed"
    return summary, row_by_pot(mapped_rows), report


def build_pot_cards(
    previous_run: str,
    latest_run: str,
    by_pot_previous: Dict[str, Dict[str, str]],
    by_pot_latest: Dict[str, Dict[str, str]],
    latest_warning_map: Dict[str, List[str]],
    expected_pots: int,
) -> List[Dict[str, object]]:
    cards: List[Dict[str, object]] = []
    for pot_number in range(1, expected_pots + 1):
        pot_id = f"{pot_number}T"
        previous_row = by_pot_previous.get(pot_id)
        latest_row = by_pot_latest.get(pot_id)
        status_text, status_class = compare_status(previous_row, latest_row)
        variety_name = ""
        if latest_row is not None:
            variety_name = (latest_row.get("variety_name", "") or "").strip()
        if not variety_name and previous_row is not None:
            variety_name = (previous_row.get("variety_name", "") or "").strip()

        latest_warnings = latest_warning_map.get(pot_id, [])
        latest_resolution = (
            (latest_row.get("resolution_source", "") or "").strip().replace("_", " ")
            if latest_row
            else ""
        )
        previous_resolution = (
            (previous_row.get("resolution_source", "") or "").strip().replace("_", " ")
            if previous_row
            else ""
        )

        cards.append(
            {
                "pot_id": pot_id,
                "pot_number": pot_number,
                "variety_name": variety_name or "unknown",
                "status_class": status_class,
                "status_label": STATUS_LABELS.get(status_class, status_text.lower()),
                "status_text": status_text,
                "previous_run": previous_run,
                "latest_run": latest_run,
                "previous_photo_url": (previous_row or {}).get("photo_url", "") or "",
                "latest_photo_url": (latest_row or {}).get("photo_url", "") or "",
                "previous_resolution": previous_resolution or "n/a",
                "latest_resolution": latest_resolution or "n/a",
                "previous_ocr": is_ocr_confirmed(previous_row),
                "latest_ocr": is_ocr_confirmed(latest_row),
                "latest_warning_count": len(latest_warnings),
                "latest_warnings": latest_warnings,
                "latest_mapping_note": (latest_row or {}).get("mapping_note", "") or "",
                "source_asset_id": (latest_row or {}).get("source_asset_id", "") or "",
            }
        )

    cards.sort(
        key=lambda card: (
            STATUS_ORDER.get(str(card.get("status_class", "")), 99),
            -int(card.get("latest_warning_count", 0) or 0),
            pot_sort_key(str(card.get("pot_id", ""))),
        )
    )
    return cards


def build_headline(
    previous_summary: Dict[str, object],
    latest_summary: Dict[str, object],
    expected_pots: int,
) -> str:
    latest_rows = int(latest_summary.get("photo_rows", 0) or 0)
    previous_rows = int(previous_summary.get("photo_rows", 0) or 0)
    latest_short = str(latest_summary.get("short_date", latest_summary.get("run_date", "")))
    previous_short = str(
        previous_summary.get("short_date", previous_summary.get("run_date", ""))
    )
    if latest_rows == expected_pots and previous_rows > latest_rows:
        return (
            f"{latest_short} landed as a clean {expected_pots}-pot census after the "
            f"noisier {previous_rows}-frame {previous_short} sweep."
        )
    if latest_rows == expected_pots:
        return f"{latest_short} reads as a complete {expected_pots}-pot sweep with no extra frames."
    return (
        f"{latest_short} closes the latest tomato batch with {latest_rows} frames across "
        f"{int(latest_summary.get('mapped_pots', 0) or 0)} mapped pots."
    )


def build_insights(
    previous_summary: Dict[str, object],
    latest_summary: Dict[str, object],
    cards: List[Dict[str, object]],
) -> List[str]:
    risk_count = sum(1 for card in cards if card.get("status_class") == "risk")
    partial_count = sum(1 for card in cards if card.get("status_class") == "info")
    previous_ocr = int(previous_summary.get("ocr_confirmed_rows", 0) or 0)
    latest_ocr = int(latest_summary.get("ocr_confirmed_rows", 0) or 0)
    latest_warnings = int(latest_summary.get("warning_count", 0) or 0)
    return [
        (
            f"{risk_count} pots are leaning entirely on continuity across "
            f"{previous_summary.get('run_date', 'the prior run')} and "
            f"{latest_summary.get('run_date', 'the latest run')}."
        ),
        f"OCR evidence moved from {previous_ocr} confirmed rows to {latest_ocr}.",
        (
            f"{partial_count} pots still have at least one OCR anchor between the two runs, "
            f"while the latest map carries {latest_warnings} warning lines."
        ),
    ]


def build_variety_counts(cards: List[Dict[str, object]]) -> List[Tuple[str, int]]:
    counts = Counter(str(card.get("variety_name", "")).strip() for card in cards)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def run_card_html(
    summary: Dict[str, object], latest_run: str, previous_run: str, index: int
) -> str:
    run_date = str(summary.get("run_date", ""))
    modifier = ""
    label = str(summary.get("batch_mode", ""))
    if run_date == latest_run:
        modifier = " current"
        label = "latest census" if label == "census" else "latest run"
    elif run_date == previous_run:
        modifier = " compare"
        label = "comparison run"

    photo_rows = int(summary.get("photo_rows", 0) or 0)
    mapped_pots = int(summary.get("mapped_pots", 0) or 0)
    ocr_confirmed = int(summary.get("ocr_confirmed_rows", 0) or 0)
    continuity_rows = int(summary.get("continuity_rows", 0) or 0)

    return (
        f"<article class='run-node{modifier}' style='--delay:{index * 80}ms'>"
        "<div class='run-bar-track'>"
        f"<div class='run-bar' style='height:{max(16, photo_rows * 3)}px'></div>"
        "</div>"
        f"<p class='run-date'>{html_escape(str(summary.get('short_date', run_date)))}</p>"
        f"<p class='run-rows'>{photo_rows} frames</p>"
        f"<p class='run-meta'>{mapped_pots} mapped · {ocr_confirmed} OCR · {continuity_rows} continuity</p>"
        f"<span class='mode-pill'>{html_escape(label)}</span>"
        "</article>"
    )


def stat_tile_html(label: str, value: str, detail: str, accent: str) -> str:
    return (
        f"<article class='stat-tile {html_escape(accent)}'>"
        f"<p class='stat-label'>{html_escape(label)}</p>"
        f"<p class='stat-value'>{html_escape(value)}</p>"
        f"<p class='stat-detail'>{html_escape(detail)}</p>"
        "</article>"
    )


def variety_bar_html(variety: str, count: int, max_count: int) -> str:
    width = 22 if max_count <= 0 else int(round((count / max_count) * 100))
    return (
        "<div class='variety-row'>"
        "<div class='variety-head'>"
        f"<span>{html_escape(variety)}</span>"
        f"<strong>{count}</strong>"
        "</div>"
        "<div class='variety-track'>"
        f"<div class='variety-fill' style='width:{max(width, 14)}%'></div>"
        "</div>"
        "</div>"
    )


def card_html(card: Dict[str, object], index: int) -> str:
    search_tokens = " ".join(
        [
            str(card.get("pot_id", "")),
            str(card.get("variety_name", "")),
            str(card.get("status_label", "")),
            str(card.get("status_text", "")),
        ]
    ).lower()
    latest_photo = str(card.get("latest_photo_url", ""))
    status_class = str(card.get("status_class", ""))
    warning_count = int(card.get("latest_warning_count", 0) or 0)
    alt_text = (
        f"{card.get('latest_run', '')} {card.get('variety_name', '')} {card.get('pot_id', '')}"
    ).strip()
    warning_label = (
        f"{warning_count} latest warning" if warning_count == 1 else f"{warning_count} latest warnings"
    )
    if warning_count == 0:
        warning_label = "clean latest row"
    if latest_photo:
        image_html = (
            f"<img src='{attr_escape(latest_photo)}' "
            f"alt='{attr_escape(alt_text)}' "
            "loading='lazy' />"
        )
    else:
        image_html = "<div class='card-missing'>No latest photo</div>"

    return (
        f"<article class='signal-card status-{html_escape(status_class)}' "
        f"data-index='{index}' "
        f"data-status='{html_escape(status_class)}' "
        f"data-variety='{attr_escape(str(card.get('variety_name', '')).lower())}' "
        f"data-search='{attr_escape(search_tokens)}' "
        f"style='--delay:{index * 28}ms'>"
        "<button class='card-button' type='button'>"
        "<div class='card-shot'>"
        f"{image_html}"
        "<div class='card-overlay'>"
        f"<span class='run-chip now'>{html_escape(str(card.get('latest_run', '')))}</span>"
        f"<span class='run-chip then'>echo {html_escape(str(card.get('previous_run', '')))}</span>"
        "</div>"
        "</div>"
        "<div class='card-copy'>"
        "<div class='card-head'>"
        f"<span class='pot-pill'>{html_escape(str(card.get('pot_id', '')))}</span>"
        f"<span class='status-pill status-{html_escape(status_class)}'>{html_escape(str(card.get('status_label', '')))}</span>"
        "</div>"
        f"<h3>{html_escape(str(card.get('variety_name', 'unknown')))}</h3>"
        f"<p class='card-line'>Latest: {html_escape(str(card.get('latest_resolution', 'n/a')))} "
        f"· OCR {'yes' if card.get('latest_ocr') else 'no'}</p>"
        f"<p class='card-line subtle'>{html_escape(warning_label)}</p>"
        "</div>"
        "</button>"
        "</article>"
    )


def build_page(
    *,
    latest_run: str,
    previous_run: str,
    run_summaries: List[Dict[str, object]],
    cards: List[Dict[str, object]],
    source_csv: Path,
    latest_report: Dict[str, object],
) -> str:
    latest_summary = next(
        (summary for summary in run_summaries if summary.get("run_date") == latest_run),
        run_summaries[-1],
    )
    previous_summary = next(
        (summary for summary in run_summaries if summary.get("run_date") == previous_run),
        run_summaries[-2] if len(run_summaries) >= 2 else run_summaries[-1],
    )
    status_counts = Counter(str(card.get("status_class", "")) for card in cards)
    variety_counts = build_variety_counts(cards)
    max_variety_count = max((count for _, count in variety_counts), default=0)
    spotlight_index = 0

    headline = build_headline(previous_summary, latest_summary, len(cards))
    insights = build_insights(previous_summary, latest_summary, cards)
    generated_at = iso_now()

    timeline_html = "".join(
        run_card_html(summary, latest_run, previous_run, index)
        for index, summary in enumerate(run_summaries)
    )
    stats_html = "".join(
        [
            stat_tile_html(
                "Latest sweep",
                f"{int(latest_summary.get('photo_rows', 0) or 0)} frames",
                f"{int(latest_summary.get('mapped_pots', 0) or 0)} mapped pots on {latest_run}",
                "warm",
            ),
            stat_tile_html(
                "Continuity lock",
                f"{status_counts.get('risk', 0)} pots",
                "same assignment across both runs without OCR proof",
                "red",
            ),
            stat_tile_html(
                "OCR signal",
                f"{int(previous_summary.get('ocr_confirmed_rows', 0) or 0)} -> {int(latest_summary.get('ocr_confirmed_rows', 0) or 0)}",
                "comparison run to latest run",
                "blue",
            ),
            stat_tile_html(
                "Variety spread",
                f"{len(variety_counts)} names",
                f"{int(latest_report.get('expected_pots', len(cards)) or len(cards))} pots in play",
                "green",
            ),
        ]
    )
    variety_html = "".join(
        variety_bar_html(variety, count, max_variety_count)
        for variety, count in variety_counts
    )
    top_varieties = [variety for variety, _ in variety_counts[:3]]
    if len(top_varieties) >= 3:
        variety_copy = (
            f"The latest mapped batch clusters around {top_varieties[0]}, "
            f"{top_varieties[1]}, and {top_varieties[2]} rather than reading like a flat one-off mix."
        )
    elif top_varieties:
        variety_copy = (
            f"The latest mapped batch is concentrated around {', '.join(top_varieties)}."
        )
    else:
        variety_copy = "The latest mapped batch is ready for variety clustering once rows are available."
    cards_html = "".join(card_html(card, index) for index, card in enumerate(cards))
    variety_options = "".join(
        f"<option value='{attr_escape(variety.lower())}'>{html_escape(variety)}</option>"
        for variety, _ in variety_counts
    )
    payload_json = json.dumps(cards, ensure_ascii=True)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tomato Signal Observatory</title>
  <style>
    :root {{
      --bg: #f6eddc;
      --paper: rgba(255, 250, 241, 0.84);
      --paper-strong: #fffaf2;
      --ink: #20322d;
      --muted: #5d6c66;
      --line: rgba(92, 72, 42, 0.16);
      --warm: #c86a34;
      --sun: #f3b24d;
      --leaf: #2f6f50;
      --sky: #295a73;
      --berry: #8b2f3d;
      --iris: #5a4f8c;
      --shadow: 0 28px 70px rgba(84, 57, 24, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(900px 480px at 100% -10%, rgba(243, 178, 77, 0.38), transparent 62%),
        radial-gradient(860px 520px at -10% 10%, rgba(47, 111, 80, 0.2), transparent 58%),
        linear-gradient(180deg, #f8f0e2 0%, #f3e7d4 52%, #efe0cb 100%);
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(115deg, rgba(255, 255, 255, 0.28), transparent 35%),
        repeating-linear-gradient(
          135deg,
          rgba(255, 255, 255, 0.07) 0,
          rgba(255, 255, 255, 0.07) 2px,
          transparent 2px,
          transparent 14px
        );
      opacity: 0.55;
      mix-blend-mode: soft-light;
    }}
    a {{
      color: inherit;
      text-decoration: none;
    }}
    .page {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 24px 18px 48px;
    }}
    .topbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
      position: relative;
      z-index: 1;
    }}
    .topbar a {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 10px 14px;
      background: rgba(255, 250, 241, 0.72);
      backdrop-filter: blur(14px);
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .hidden {{
      display: none !important;
    }}
    .hero,
    .section-card,
    .spotlight,
    .deck-shell {{
      border: 1px solid var(--line);
      background: var(--paper);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      border-radius: 28px;
      padding: 30px;
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.9fr);
      gap: 22px;
      animation: rise-in 760ms ease both;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -120px -180px auto;
      width: 460px;
      height: 460px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(243, 178, 77, 0.28), transparent 68%);
      filter: blur(14px);
      pointer-events: none;
    }}
    .eyebrow {{
      margin: 0 0 10px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 0.76rem;
      font-weight: 800;
      color: #855227;
    }}
    h1,
    h2,
    h3 {{
      font-family: "Iowan Old Style", "Baskerville", "Palatino Linotype", serif;
      letter-spacing: -0.02em;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(2.3rem, 5vw, 4.9rem);
      line-height: 0.96;
      max-width: 10ch;
    }}
    .lede {{
      margin: 0;
      max-width: 58ch;
      font-size: 1.02rem;
      line-height: 1.65;
      color: var(--muted);
    }}
    .insights {{
      display: grid;
      gap: 8px;
      margin: 18px 0 0;
      padding: 0;
      list-style: none;
    }}
    .insights li {{
      border: 1px solid rgba(92, 72, 42, 0.12);
      border-radius: 14px;
      background: rgba(255, 253, 247, 0.7);
      padding: 10px 12px;
      color: #566763;
      font-size: 0.88rem;
    }}
    .hero-side {{
      display: grid;
      gap: 14px;
      align-content: start;
      position: relative;
      z-index: 1;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .stat-tile {{
      border: 1px solid rgba(92, 72, 42, 0.14);
      border-radius: 18px;
      background: rgba(255, 252, 247, 0.84);
      padding: 14px;
      min-height: 130px;
      display: grid;
      align-content: start;
      gap: 6px;
    }}
    .stat-tile.warm {{ box-shadow: inset 0 0 0 1px rgba(200, 106, 52, 0.08); }}
    .stat-tile.red {{ box-shadow: inset 0 0 0 1px rgba(139, 47, 61, 0.08); }}
    .stat-tile.blue {{ box-shadow: inset 0 0 0 1px rgba(41, 90, 115, 0.08); }}
    .stat-tile.green {{ box-shadow: inset 0 0 0 1px rgba(47, 111, 80, 0.08); }}
    .stat-label {{
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.72rem;
      color: #7b6c56;
      font-weight: 800;
    }}
    .stat-value {{
      margin: 0;
      font-size: clamp(1.35rem, 2vw, 2rem);
      font-weight: 800;
    }}
    .stat-detail {{
      margin: 0;
      font-size: 0.84rem;
      line-height: 1.45;
      color: var(--muted);
    }}
    .variety-panel {{
      border: 1px solid rgba(92, 72, 42, 0.14);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255, 252, 247, 0.88), rgba(255, 247, 237, 0.74));
      padding: 18px;
    }}
    .panel-title {{
      margin: 0 0 10px;
      font-size: 1.12rem;
    }}
    .panel-copy {{
      margin: 0 0 14px;
      font-size: 0.88rem;
      color: var(--muted);
      line-height: 1.5;
    }}
    .variety-grid {{
      display: grid;
      gap: 10px;
    }}
    .variety-row {{
      display: grid;
      gap: 5px;
    }}
    .variety-head {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 0.83rem;
      color: #455954;
    }}
    .variety-track {{
      height: 10px;
      border-radius: 999px;
      background: rgba(47, 111, 80, 0.11);
      overflow: hidden;
    }}
    .variety-fill {{
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #2f6f50, #f0a63f);
    }}
    .section-card {{
      border-radius: 24px;
      padding: 22px;
      margin-top: 18px;
      animation: rise-in 760ms ease both;
      animation-delay: 120ms;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: clamp(1.4rem, 2.2vw, 2rem);
    }}
    .section-head p {{
      margin: 8px 0 0;
      color: var(--muted);
      max-width: 60ch;
      line-height: 1.55;
    }}
    .rhythm-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
      gap: 12px;
    }}
    .run-node {{
      border: 1px solid rgba(92, 72, 42, 0.12);
      border-radius: 18px;
      background: rgba(255, 253, 249, 0.84);
      padding: 16px;
      display: grid;
      gap: 8px;
      align-content: end;
      min-height: 210px;
      animation: rise-in 760ms ease both;
      animation-delay: var(--delay);
    }}
    .run-node.current {{
      background: linear-gradient(180deg, rgba(255, 248, 234, 0.95), rgba(255, 253, 249, 0.82));
      box-shadow: inset 0 0 0 1px rgba(200, 106, 52, 0.18);
    }}
    .run-node.compare {{
      box-shadow: inset 0 0 0 1px rgba(41, 90, 115, 0.14);
    }}
    .run-bar-track {{
      height: 146px;
      display: flex;
      align-items: end;
    }}
    .run-bar {{
      width: 100%;
      border-radius: 14px 14px 6px 6px;
      background: linear-gradient(180deg, rgba(243, 178, 77, 0.82), rgba(200, 106, 52, 0.94));
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.26);
    }}
    .run-node.compare .run-bar {{
      background: linear-gradient(180deg, rgba(41, 90, 115, 0.64), rgba(41, 90, 115, 0.92));
    }}
    .run-node.current .run-bar {{
      background: linear-gradient(180deg, rgba(47, 111, 80, 0.74), rgba(47, 111, 80, 1));
    }}
    .run-date,
    .run-rows,
    .run-meta {{
      margin: 0;
    }}
    .run-date {{
      font-size: 1.1rem;
      font-weight: 800;
    }}
    .run-rows {{
      font-size: 0.9rem;
      color: #445853;
    }}
    .run-meta {{
      font-size: 0.82rem;
      line-height: 1.45;
      color: var(--muted);
    }}
    .mode-pill,
    .status-pill,
    .pot-pill,
    .run-chip {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .mode-pill {{
      justify-self: start;
      padding: 6px 10px;
      background: rgba(47, 111, 80, 0.11);
      color: #315f4a;
    }}
    .observatory {{
      display: grid;
      grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
      margin-top: 18px;
    }}
    .spotlight {{
      position: sticky;
      top: 18px;
      border-radius: 24px;
      overflow: hidden;
      animation: rise-in 760ms ease both;
      animation-delay: 180ms;
    }}
    .spotlight-copy {{
      padding: 20px 20px 14px;
      background: linear-gradient(180deg, rgba(255, 250, 241, 0.94), rgba(255, 247, 238, 0.8));
      border-bottom: 1px solid var(--line);
    }}
    .spotlight-copy h2 {{
      margin: 0 0 8px;
      font-size: clamp(1.7rem, 3vw, 2.7rem);
    }}
    .spotlight-copy p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }}
    .spotlight-facts {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .fact {{
      border: 1px solid rgba(92, 72, 42, 0.11);
      border-radius: 14px;
      padding: 10px;
      background: rgba(255, 255, 255, 0.58);
    }}
    .fact span {{
      display: block;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #7a6a56;
      margin-bottom: 5px;
      font-weight: 800;
    }}
    .fact strong {{
      display: block;
      font-size: 0.92rem;
      line-height: 1.4;
    }}
    .warning-stack {{
      margin: 16px 0 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 8px;
    }}
    .warning-stack li {{
      border-left: 4px solid rgba(139, 47, 61, 0.42);
      padding: 8px 10px;
      background: rgba(139, 47, 61, 0.05);
      border-radius: 0 12px 12px 0;
      font-size: 0.8rem;
      line-height: 1.45;
      color: #5e4f4f;
    }}
    .spotlight-pair {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
    }}
    .spotlight-frame {{
      position: relative;
      min-height: 220px;
      background: #e6dcc8;
      border-right: 1px solid var(--line);
    }}
    .spotlight-frame:last-child {{
      border-right: 0;
    }}
    .spotlight-frame img {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
      aspect-ratio: 4 / 3;
    }}
    .spotlight-frame figcaption {{
      position: absolute;
      left: 12px;
      bottom: 12px;
      border-radius: 999px;
      padding: 7px 10px;
      background: rgba(22, 29, 27, 0.72);
      color: #fbf6ef;
      font-size: 0.74rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 800;
    }}
    .spotlight-empty {{
      display: grid;
      place-items: center;
      min-height: 220px;
      color: #64736d;
      font-size: 0.88rem;
      padding: 18px;
      text-align: center;
    }}
    .deck-shell {{
      border-radius: 24px;
      padding: 18px;
      animation: rise-in 760ms ease both;
      animation-delay: 220ms;
    }}
    .controls {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 16px;
    }}
    .search-input,
    .variety-select {{
      width: 100%;
      border: 1px solid rgba(92, 72, 42, 0.16);
      border-radius: 14px;
      background: rgba(255, 252, 247, 0.92);
      color: var(--ink);
      font: inherit;
      padding: 12px 14px;
    }}
    .status-filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .filter-button {{
      border: 1px solid rgba(92, 72, 42, 0.14);
      border-radius: 999px;
      padding: 8px 12px;
      background: rgba(255, 252, 247, 0.8);
      color: #344742;
      font: inherit;
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      cursor: pointer;
      transition: transform 180ms ease, background 180ms ease, color 180ms ease;
    }}
    .filter-button:hover,
    .filter-button.active {{
      background: #23493b;
      color: #f8f2e8;
      transform: translateY(-1px);
    }}
    .controls-meta {{
      justify-self: end;
      font-size: 0.84rem;
      color: var(--muted);
      white-space: nowrap;
    }}
    .deck {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 14px;
    }}
    .signal-card {{
      animation: rise-in 740ms ease both;
      animation-delay: var(--delay);
    }}
    .signal-card.hidden {{
      display: none;
    }}
    .card-button {{
      width: 100%;
      padding: 0;
      border: 1px solid rgba(92, 72, 42, 0.12);
      border-radius: 22px;
      overflow: hidden;
      background: rgba(255, 253, 248, 0.9);
      box-shadow: 0 18px 40px rgba(84, 57, 24, 0.08);
      text-align: left;
      cursor: pointer;
      transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }}
    .card-button:hover,
    .signal-card.selected .card-button {{
      transform: translateY(-4px);
      box-shadow: 0 24px 50px rgba(84, 57, 24, 0.14);
      border-color: rgba(35, 73, 59, 0.42);
    }}
    .card-shot {{
      position: relative;
      aspect-ratio: 4 / 3;
      overflow: hidden;
      background: #dccfb8;
    }}
    .card-shot img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transform: scale(1.02);
      transition: transform 260ms ease;
    }}
    .card-button:hover .card-shot img,
    .signal-card.selected .card-shot img {{
      transform: scale(1.08);
    }}
    .card-overlay {{
      position: absolute;
      inset: auto 12px 12px 12px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }}
    .run-chip {{
      padding: 6px 9px;
      background: rgba(18, 24, 23, 0.72);
      color: #f8f4ee;
      backdrop-filter: blur(8px);
    }}
    .run-chip.then {{
      background: rgba(255, 250, 242, 0.84);
      color: #5c4c39;
    }}
    .card-missing {{
      display: grid;
      place-items: center;
      height: 100%;
      color: #62716c;
      font-size: 0.86rem;
    }}
    .card-copy {{
      padding: 14px;
      display: grid;
      gap: 8px;
    }}
    .card-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .pot-pill {{
      padding: 6px 9px;
      background: rgba(47, 111, 80, 0.12);
      color: #2a5f46;
    }}
    .status-pill {{
      padding: 6px 9px;
    }}
    .status-risk {{
      background: rgba(139, 47, 61, 0.1);
      color: #7d2235;
    }}
    .status-drift {{
      background: rgba(90, 79, 140, 0.12);
      color: #51417b;
    }}
    .status-info {{
      background: rgba(41, 90, 115, 0.11);
      color: #28536c;
    }}
    .status-warn {{
      background: rgba(200, 106, 52, 0.12);
      color: #8d532d;
    }}
    .status-ok {{
      background: rgba(47, 111, 80, 0.12);
      color: #2a5f46;
    }}
    .card-copy h3 {{
      margin: 0;
      font-size: 1.15rem;
      line-height: 1.08;
    }}
    .card-line {{
      margin: 0;
      color: #485c57;
      font-size: 0.85rem;
      line-height: 1.45;
    }}
    .card-line.subtle {{
      color: #6b7a75;
    }}
    .footnote {{
      margin-top: 18px;
      font-size: 0.8rem;
      color: #64746f;
      text-align: right;
    }}
    .footnote code {{
      background: rgba(255, 255, 255, 0.55);
      border: 1px solid rgba(92, 72, 42, 0.12);
      border-radius: 8px;
      padding: 2px 6px;
    }}
    @keyframes rise-in {{
      from {{
        opacity: 0;
        transform: translateY(22px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}
    @media (max-width: 1120px) {{
      .hero,
      .observatory {{
        grid-template-columns: 1fr;
      }}
      .spotlight {{
        position: static;
      }}
    }}
    @media (max-width: 760px) {{
      .page {{
        padding: 18px 12px 36px;
      }}
      .hero,
      .section-card,
      .deck-shell {{
        padding: 18px;
      }}
      .stats-grid,
      .spotlight-facts,
      .controls {{
        grid-template-columns: 1fr;
      }}
      .controls-meta {{
        justify-self: start;
      }}
      .spotlight-pair {{
        grid-template-columns: 1fr;
      }}
      .deck {{
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      }}
      h1 {{
        max-width: none;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <nav class="topbar" aria-label="Tracker navigation">
      <a href="./index.html">Tracker Index</a>
      <a href="./pot-run-comparison.html">Full Pair Comparison</a>
      <a href="./tomato-trails-view.html">Tomato Trails View</a>
      <a href="./pot-intake-history.html">Run History</a>
    </nav>

    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Tomato Signal Observatory</p>
        <h1>{html_escape(headline)}</h1>
        <p class="lede">
          This page treats the latest garden intake like weather: how the batch rhythm changed over time,
          where the latest sweep is leaning too hard on continuity, and which pots are most worth opening
          side-by-side instead of reading from thumbnails alone.
        </p>
        <ul class="insights">
          {''.join(f"<li>{html_escape(item)}</li>" for item in insights)}
        </ul>
      </div>
      <div class="hero-side">
        <div class="stats-grid">
          {stats_html}
        </div>
        <section class="variety-panel">
          <h2 class="panel-title">Latest variety spread</h2>
          <p class="panel-copy">
            {html_escape(variety_copy)}
          </p>
          <div class="variety-grid">
            {variety_html}
          </div>
        </section>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <div>
          <p class="eyebrow">Batch Rhythm</p>
          <h2>How the season has been arriving</h2>
          <p>Every run below is built from the same mapping logic as the main tracker, so the count shifts show real intake shape changes rather than decorative summaries.</p>
        </div>
      </div>
      <div class="rhythm-grid">
        {timeline_html}
      </div>
    </section>

    <section class="observatory">
      <aside class="spotlight" aria-live="polite">
        <div class="spotlight-copy">
          <p class="eyebrow" id="spotlight-eyebrow">Selected signal</p>
          <h2 id="spotlight-title"></h2>
          <p id="spotlight-description"></p>
          <div class="spotlight-facts" id="spotlight-facts"></div>
          <ul class="warning-stack" id="spotlight-warnings"></ul>
        </div>
        <div class="spotlight-pair">
          <figure class="spotlight-frame" id="spotlight-previous-frame">
            <img id="spotlight-previous-image" alt="" />
            <figcaption id="spotlight-previous-caption"></figcaption>
            <div class="spotlight-empty hidden" id="spotlight-previous-empty">No mapped comparison image.</div>
          </figure>
          <figure class="spotlight-frame" id="spotlight-latest-frame">
            <img id="spotlight-latest-image" alt="" />
            <figcaption id="spotlight-latest-caption"></figcaption>
            <div class="spotlight-empty hidden" id="spotlight-latest-empty">No mapped latest image.</div>
          </figure>
        </div>
      </aside>

      <div class="deck-shell">
        <div class="section-head">
          <div>
            <p class="eyebrow">Compare Deck</p>
            <h2>Pick a pot and open the pair</h2>
            <p>The deck defaults to the highest-signal rows first. Filter by evidence mode, jump to a variety cluster, or search directly for a pot ID.</p>
          </div>
        </div>
        <div class="controls">
          <input class="search-input" id="search-input" type="search" placeholder="Search pot, variety, or signal..." />
          <select class="variety-select" id="variety-select" aria-label="Filter by variety">
            <option value="">All varieties</option>
            {variety_options}
          </select>
          <div class="controls-meta" id="result-count"></div>
        </div>
        <div class="status-filters" role="tablist" aria-label="Signal filters">
          <button class="filter-button active" type="button" data-filter="all">All</button>
          <button class="filter-button" type="button" data-filter="risk">Continuity Lock</button>
          <button class="filter-button" type="button" data-filter="info">Partial OCR</button>
          <button class="filter-button" type="button" data-filter="warn">Continuity</button>
          <button class="filter-button" type="button" data-filter="ok">OCR Confirmed</button>
          <button class="filter-button" type="button" data-filter="drift">Drift</button>
        </div>
        <div class="deck" id="deck">
          {cards_html}
        </div>
        <p class="footnote">
          Generated from <code>{html_escape(str(source_csv))}</code> at <code>{html_escape(generated_at)}</code>.
        </p>
      </div>
    </section>
  </main>

  <script>
    (() => {{
      const cards = {payload_json};
      const spotlightIndexDefault = {spotlight_index};
      const deck = document.getElementById("deck");
      const searchInput = document.getElementById("search-input");
      const varietySelect = document.getElementById("variety-select");
      const resultCount = document.getElementById("result-count");
      const filterButtons = Array.from(document.querySelectorAll(".filter-button"));
      const cardNodes = Array.from(document.querySelectorAll(".signal-card"));

      const spotlightEyebrow = document.getElementById("spotlight-eyebrow");
      const spotlightTitle = document.getElementById("spotlight-title");
      const spotlightDescription = document.getElementById("spotlight-description");
      const spotlightFacts = document.getElementById("spotlight-facts");
      const spotlightWarnings = document.getElementById("spotlight-warnings");

      const previousFrame = document.getElementById("spotlight-previous-frame");
      const previousImage = document.getElementById("spotlight-previous-image");
      const previousCaption = document.getElementById("spotlight-previous-caption");
      const previousEmpty = document.getElementById("spotlight-previous-empty");

      const latestFrame = document.getElementById("spotlight-latest-frame");
      const latestImage = document.getElementById("spotlight-latest-image");
      const latestCaption = document.getElementById("spotlight-latest-caption");
      const latestEmpty = document.getElementById("spotlight-latest-empty");

      let activeFilter = "all";
      let selectedIndex = spotlightIndexDefault;

      function factHtml(label, value) {{
        return `<div class="fact"><span>${{label}}</span><strong>${{value}}</strong></div>`;
      }}

      function updateFrame(frame, image, caption, empty, url, alt, text) {{
        const hasImage = Boolean(url);
        image.classList.toggle("hidden", !hasImage);
        caption.classList.toggle("hidden", !hasImage);
        empty.classList.toggle("hidden", hasImage);
        if (hasImage) {{
          image.src = url;
          image.alt = alt;
          caption.textContent = text;
        }} else {{
          image.src = "";
          image.alt = "";
          caption.textContent = "";
        }}
        frame.classList.toggle("is-empty", !hasImage);
      }}

      function renderSpotlight(index) {{
        const item = cards[index];
        if (!item) return;
        selectedIndex = index;
        cardNodes.forEach((node) => {{
          node.classList.toggle("selected", Number(node.dataset.index) === index);
        }});

        spotlightEyebrow.textContent = item.status_label;
        spotlightTitle.textContent = `${{item.pot_id}} · ${{item.variety_name}}`;
        spotlightDescription.textContent = item.status_text;

        spotlightFacts.innerHTML = [
          factHtml("Latest resolution", item.latest_resolution),
          factHtml("Previous resolution", item.previous_resolution),
          factHtml("OCR path", `${{item.previous_ocr ? "yes" : "no"}} -> ${{item.latest_ocr ? "yes" : "no"}}`),
          factHtml("Latest warnings", item.latest_warning_count ? String(item.latest_warning_count) : "none"),
        ].join("");

        const warnings = item.latest_warnings && item.latest_warnings.length
          ? item.latest_warnings.map((warning) => `<li>${{warning}}</li>`).join("")
          : "<li>No pot-specific latest warning lines.</li>";
        spotlightWarnings.innerHTML = warnings;

        updateFrame(
          previousFrame,
          previousImage,
          previousCaption,
          previousEmpty,
          item.previous_photo_url,
          `${{item.previous_run}} ${{item.variety_name}} ${{item.pot_id}}`,
          `${{item.previous_run}} comparison frame`
        );
        updateFrame(
          latestFrame,
          latestImage,
          latestCaption,
          latestEmpty,
          item.latest_photo_url,
          `${{item.latest_run}} ${{item.variety_name}} ${{item.pot_id}}`,
          `${{item.latest_run}} latest frame`
        );
      }}

      function applyFilters() {{
        const query = (searchInput.value || "").trim().toLowerCase();
        const variety = (varietySelect.value || "").trim().toLowerCase();
        let visibleCount = 0;
        let firstVisibleIndex = null;

        cardNodes.forEach((node) => {{
          const matchesFilter = activeFilter === "all" || node.dataset.status === activeFilter;
          const matchesVariety = !variety || node.dataset.variety === variety;
          const matchesQuery = !query || (node.dataset.search || "").includes(query);
          const visible = matchesFilter && matchesVariety && matchesQuery;
          node.classList.toggle("hidden", !visible);
          if (visible) {{
            visibleCount += 1;
            if (firstVisibleIndex === null) {{
              firstVisibleIndex = Number(node.dataset.index);
            }}
          }}
        }});

        resultCount.textContent = `${{visibleCount}} of ${{cards.length}} visible`;
        const selectedNode = cardNodes.find((node) => Number(node.dataset.index) === selectedIndex);
        const selectedVisible = selectedNode && !selectedNode.classList.contains("hidden");
        if (!selectedVisible && firstVisibleIndex !== null) {{
          renderSpotlight(firstVisibleIndex);
        }}
      }}

      filterButtons.forEach((button) => {{
        button.addEventListener("click", () => {{
          activeFilter = button.dataset.filter || "all";
          filterButtons.forEach((node) => node.classList.toggle("active", node === button));
          applyFilters();
        }});
      }});

      cardNodes.forEach((node) => {{
        const index = Number(node.dataset.index);
        const button = node.querySelector(".card-button");
        if (!button) return;
        button.addEventListener("click", () => renderSpotlight(index));
      }});

      searchInput.addEventListener("input", applyFilters);
      varietySelect.addEventListener("change", applyFilters);

      renderSpotlight(spotlightIndexDefault);
      applyFilters();
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a visual observatory page for the latest tomato batch."
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed intake CSV.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count for tomato runs.",
    )
    parser.add_argument(
        "--previous-run",
        default="",
        help="Comparison run date. Defaults to the run immediately before the latest run.",
    )
    parser.add_argument(
        "--latest-run",
        default="",
        help="Latest run date. Defaults to the latest available run.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series map CSV.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot override CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline map CSV for continuity reconciliation.",
    )
    parser.add_argument(
        "--row-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_two_run_tag_overrides.csv"),
        help="Optional row-level manual override CSV from manual-two-run tagger.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/tomato-signal-observatory.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.labeled_csv)
    available_dates = available_run_dates(rows)
    if len(available_dates) < 2:
        raise ValueError("need at least two capture dates to build the observatory page")

    previous_run, latest_run = resolve_run_dates(rows, args.previous_run, args.latest_run)
    series_variety_map = load_series_variety_map(args.series_map_csv)
    pot_series_overrides = load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(args.baseline_map_csv)
    row_overrides = load_row_overrides(args.row_overrides_csv)

    run_summaries: List[Dict[str, object]] = []
    bundles_by_run: Dict[str, Dict[str, Dict[str, str]]] = {}
    reports_by_run: Dict[str, Dict[str, object]] = {}

    for run_date in available_dates:
        summary, by_pot, report = build_run_bundle(
            rows=rows,
            run_date=run_date,
            expected_pots=args.expected_pots,
            series_variety_map=series_variety_map,
            pot_series_overrides=pot_series_overrides,
            baseline_variety_map=baseline_variety_map,
            row_overrides=row_overrides,
        )
        run_summaries.append(summary)
        bundles_by_run[run_date] = by_pot
        reports_by_run[run_date] = report

    latest_warning_map = map_warning_rows(
        list(reports_by_run.get(latest_run, {}).get("warnings", []))
        if isinstance(reports_by_run.get(latest_run, {}).get("warnings", []), list)
        else []
    )
    cards = build_pot_cards(
        previous_run=previous_run,
        latest_run=latest_run,
        by_pot_previous=bundles_by_run.get(previous_run, {}),
        by_pot_latest=bundles_by_run.get(latest_run, {}),
        latest_warning_map=latest_warning_map,
        expected_pots=args.expected_pots,
    )
    page = build_page(
        latest_run=latest_run,
        previous_run=previous_run,
        run_summaries=run_summaries,
        cards=cards,
        source_csv=args.labeled_csv,
        latest_report=reports_by_run.get(latest_run, {}),
    )

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"labeled_csv={args.labeled_csv}")
    print(f"previous_run={previous_run}")
    print(f"latest_run={latest_run}")
    print(f"cards={len(cards)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
