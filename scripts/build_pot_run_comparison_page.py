#!/usr/bin/env python3
"""Build side-by-side pot comparison page for two run dates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from build_tomato_pot_mapping import (
    build_mapping,
    load_baseline_variety_map,
    load_pot_series_overrides,
    load_row_overrides,
    load_series_variety_map,
    read_rows,
)
from stable_generated_output import stabilize_rendered_text, write_text_if_changed

CONTINUITY_SOURCES = {
    "manual_override",
    "baseline_continuity",
    "historical_continuity",
    "series_map",
    "sequence_inference",
}
DEFAULT_COMPARISON_RUN_A = "2026-03-04"
DEFAULT_COMPARISON_RUN_B = "2026-03-11"


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


def normalize_pot_id(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", (raw or "").strip()).upper()
    matched = re.fullmatch(r"([0-9]{1,3})T?", cleaned)
    if not matched:
        return ""
    number = int(matched.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def pot_sort_key(pot_id: str) -> Tuple[int, str]:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return (10**9, pot_id)
    return (int(matched.group(1)), pot_id)


def choose_expected_for_run(
    rows: List[Dict[str, str]], run_date: str, expected_pots: int
) -> int:
    count = sum(
        1
        for row in rows
        if (row.get("capture_date", "") or "").strip() == run_date
    )
    if count >= expected_pots:
        return expected_pots
    return count


def available_run_dates(rows: List[Dict[str, str]]) -> List[str]:
    return sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )


def resolve_run_dates(
    rows: List[Dict[str, str]],
    run_a: Optional[str],
    run_b: Optional[str],
    preferred_default_pair: Optional[Tuple[str, str]] = None,
) -> Tuple[str, str]:
    dates = available_run_dates(rows)
    normalized_a = (run_a or "").strip()
    normalized_b = (run_b or "").strip()

    if normalized_a and normalized_b:
        return normalized_a, normalized_b

    if len(dates) < 2:
        raise ValueError(
            "need at least two capture dates to build a run comparison page"
        )

    if not normalized_a and not normalized_b:
        if preferred_default_pair:
            preferred_a = (preferred_default_pair[0] or "").strip()
            preferred_b = (preferred_default_pair[1] or "").strip()
            if preferred_a in dates and preferred_b in dates:
                return preferred_a, preferred_b
        return dates[-2], dates[-1]

    if normalized_a:
        if normalized_a in dates:
            index = dates.index(normalized_a)
            if index < len(dates) - 1:
                return normalized_a, dates[index + 1]
        fallback = dates[-1]
        if fallback == normalized_a:
            fallback = dates[-2]
        return normalized_a, fallback

    assert normalized_b
    if normalized_b in dates:
        index = dates.index(normalized_b)
        if index > 0:
            return dates[index - 1], normalized_b
    fallback = dates[-2]
    if fallback == normalized_b:
        fallback = dates[-1]
    return fallback, normalized_b


def row_by_pot(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
        if pot_id:
            out[pot_id] = row
    return out


def is_ocr_confirmed(row: Optional[Dict[str, str]]) -> bool:
    if row is None:
        return False
    note = (row.get("mapping_note", "") or "").strip()
    return "ocr_confirms_pot_number" in note


def continuity_used(row: Optional[Dict[str, str]]) -> bool:
    if row is None:
        return False
    source = (row.get("resolution_source", "") or "").strip()
    return source in CONTINUITY_SOURCES


def compare_status(
    row_a: Optional[Dict[str, str]],
    row_b: Optional[Dict[str, str]],
) -> Tuple[str, str]:
    if row_a is None or row_b is None:
        return ("Missing mapping in one run", "warn")

    variety_a = (row_a.get("variety_name", "") or "").strip()
    variety_b = (row_b.get("variety_name", "") or "").strip()
    ocr_a = is_ocr_confirmed(row_a)
    ocr_b = is_ocr_confirmed(row_b)
    continuity_a = continuity_used(row_a)
    continuity_b = continuity_used(row_b)

    if variety_a and variety_b and variety_a != variety_b:
        return ("Variety mismatch between runs", "drift")

    if continuity_a and continuity_b and not ocr_a and not ocr_b:
        return ("Continuity lock: same assignment both days without OCR confirmation", "risk")

    if ocr_a and ocr_b:
        return ("OCR confirmed both days", "ok")

    if ocr_a or ocr_b:
        return ("Partially OCR confirmed", "info")

    if continuity_a and continuity_b:
        return ("Continuity mapping both days", "warn")

    return ("Mixed evidence", "info")


def compare_row_class(css_class: str) -> str:
    if css_class == "risk":
        return "risk-row"
    if css_class == "drift":
        return "drift-row"
    if css_class == "warn":
        return "warn-row"
    return ""


def run_summary(report: Dict[str, object], run_date: str) -> str:
    selected_rows = int(report.get("selected_rows", 0) or 0)
    unique_pot_count = int(report.get("unique_pot_count", 0) or 0)
    ocr_confirmed_rows = int(report.get("ocr_confirmed_rows", 0) or 0)
    resolution_counts = report.get("resolution_source_counts", {})
    continuity_total = 0
    if isinstance(resolution_counts, dict):
        continuity_total = sum(
            int(resolution_counts.get(key, 0) or 0) for key in CONTINUITY_SOURCES
        )
    return (
        "<article class='run-card'>"
        f"<h3>{html_escape(run_date)}</h3>"
        f"<p>Rows: <strong>{selected_rows}</strong></p>"
        f"<p>Pots mapped: <strong>{unique_pot_count}</strong></p>"
        f"<p>OCR confirmed rows: <strong>{ocr_confirmed_rows}</strong></p>"
        f"<p>Continuity-resolved rows: <strong>{continuity_total}</strong></p>"
        "</article>"
    )


def shot_html(
    row: Optional[Dict[str, str]], run_date: str, side_label: str
) -> str:
    if row is None:
        return (
            "<div class='shot missing'>"
            f"<h4>{html_escape(run_date)} ({html_escape(side_label)})</h4>"
            "<div class='img-missing'>No mapped row</div>"
            "</div>"
        )

    photo_url = (row.get("photo_url", "") or "").strip()
    variety = (row.get("variety_name", "") or "").strip()
    source_asset_id = (row.get("source_asset_id", "") or "").strip()
    resolution_source = (row.get("resolution_source", "") or "").strip().replace("_", " ")
    review_label = (row.get("review_status_label", "") or "").strip()
    ocr_confirm = "yes" if is_ocr_confirmed(row) else "no"

    image = (
        "<button class='img-btn' data-open-lightbox='true' "
        f"data-full='{attr_escape(photo_url)}' "
        f"data-alt='{attr_escape(f'{run_date} {variety}')}' "
        "type='button'>"
        f"<img src='{attr_escape(photo_url)}' alt='{attr_escape(f'{run_date} {variety}')}' loading='lazy' />"
        "</button>"
        if photo_url
        else "<div class='img-missing'>No photo URL</div>"
    )
    return (
        "<div class='shot'>"
        f"<h4>{html_escape(run_date)} ({html_escape(side_label)})</h4>"
        f"{image}"
        "<div class='meta'>"
        f"<p><strong>{html_escape(variety or 'unknown')}</strong></p>"
        f"<p>Status: {html_escape(review_label or 'n/a')}</p>"
        f"<p>Resolution: {html_escape(resolution_source or 'n/a')}</p>"
        f"<p>OCR confirms pot #: <strong>{html_escape(ocr_confirm)}</strong></p>"
        f"<p>Asset: {html_escape(source_asset_id)}</p>"
        "</div>"
        "</div>"
    )


def build_page(
    run_a: str,
    run_b: str,
    report_a: Dict[str, object],
    report_b: Dict[str, object],
    by_pot_a: Dict[str, Dict[str, str]],
    by_pot_b: Dict[str, Dict[str, str]],
    expected_pots: int,
    input_csv: Path,
    generated_at: str = "__GENERATED_AT__",
) -> str:
    cards: List[str] = []
    risk_count = 0
    drift_count = 0
    for pot_number in range(1, expected_pots + 1):
        pot_id = f"{pot_number}T"
        row_a = by_pot_a.get(pot_id)
        row_b = by_pot_b.get(pot_id)
        status_text, status_class = compare_status(row_a, row_b)
        if status_class == "risk":
            risk_count += 1
        if status_class == "drift":
            drift_count += 1
        row_class = compare_row_class(status_class)

        cards.append(
            f"<article class='pot-card {row_class}' data-status='{html_escape(status_class)}'>"
            "<header class='pot-head'>"
            f"<h2>{html_escape(pot_id)}</h2>"
            f"<span class='badge {html_escape(status_class)}'>{html_escape(status_text)}</span>"
            "</header>"
            "<div class='pair'>"
            f"{shot_html(row_a, run_a, 'Left')}"
            f"{shot_html(row_b, run_b, 'Right')}"
            "</div>"
            "</article>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pot Comparison: {html_escape(run_a)} vs {html_escape(run_b)}</title>
  <style>
    :root {{
      --bg: #f4f0e3;
      --card: #fffdf7;
      --ink: #1f2b29;
      --line: #d8d1c2;
      --ok: #2f6947;
      --warn: #8a5c23;
      --risk: #8a2d2b;
      --info: #35597f;
      --drift: #5b3f8a;
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
    .wrap {{
      max-width: 1420px;
      margin: 0 auto;
      padding: 18px 14px 30px;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(145deg, rgba(53, 89, 127, 0.12), rgba(91, 63, 138, 0.1));
      padding: 15px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.3rem, 3vw, 2rem);
    }}
    .sub {{ margin: 0; color: #4f5f5a; }}
    .meta {{
      margin-top: 8px;
      color: #51625d;
      font-size: 0.84rem;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
    }}
    .run-grid {{
      margin-top: 11px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }}
    .run-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--card);
      padding: 9px;
    }}
    .run-card h3 {{ margin: 0 0 6px; font-size: 0.92rem; color: #40524d; }}
    .run-card p {{ margin: 0; font-size: 0.79rem; color: #5a6a65; line-height: 1.45; }}
    .toolbar {{
      position: sticky;
      top: 8px;
      z-index: 6;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--card);
      padding: 9px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .toolbar button {{
      border: 1px solid #d5ccbb;
      border-radius: 999px;
      background: #fffef9;
      color: #2b3b37;
      font: inherit;
      font-size: 0.8rem;
      font-weight: 700;
      padding: 6px 10px;
      cursor: pointer;
    }}
    .toolbar button.active {{
      background: #2e4f70;
      color: #fff;
      border-color: #2e4f70;
    }}
    .summary {{
      margin-left: auto;
      font-size: 0.82rem;
      color: #51625d;
    }}
    .grid {{
      display: grid;
      gap: 10px;
    }}
    .pot-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--card);
      overflow: hidden;
    }}
    .pot-card.risk-row {{ border-left: 8px solid var(--risk); }}
    .pot-card.warn-row {{ border-left: 8px solid var(--warn); }}
    .pot-card.drift-row {{ border-left: 8px solid var(--drift); }}
    .pot-head {{
      padding: 9px 10px;
      border-bottom: 1px solid #ece5d6;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      background: #f8f3e8;
    }}
    .pot-head h2 {{ margin: 0; font-size: 1rem; color: #243430; }}
    .badge {{
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 0.74rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}
    .badge.ok {{ background: #e5f2e8; color: #1e5e39; border: 1px solid #c7dfcf; }}
    .badge.warn {{ background: #faecd5; color: #734611; border: 1px solid #efce9b; }}
    .badge.risk {{ background: #f8e2df; color: #7b2523; border: 1px solid #e9bbb5; }}
    .badge.info {{ background: #e6eef8; color: #2a4e73; border: 1px solid #c8d8ea; }}
    .badge.drift {{ background: #ece6f8; color: #52357f; border: 1px solid #d6caea; }}
    .pair {{
      padding: 9px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}
    .shot {{
      border: 1px solid #e2d9c9;
      border-radius: 10px;
      overflow: hidden;
      background: #fefcf6;
    }}
    .shot h4 {{
      margin: 0;
      padding: 6px 8px;
      border-bottom: 1px solid #e8dfcf;
      font-size: 0.78rem;
      color: #53645f;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: #f7f2e6;
    }}
    .img-btn {{
      width: 100%;
      border: 0;
      margin: 0;
      padding: 0;
      background: #ece4d3;
      aspect-ratio: 4 / 3;
      cursor: zoom-in;
    }}
    .img-btn img {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }}
    .img-missing {{
      min-height: 160px;
      display: grid;
      place-items: center;
      color: #6b7974;
      font-size: 0.82rem;
      padding: 8px;
      text-align: center;
      background: #f0eadb;
    }}
    .meta {{
      padding: 7px 8px 8px;
      display: grid;
      gap: 4px;
    }}
    .meta p {{
      margin: 0;
      color: #556660;
      font-size: 0.78rem;
      line-height: 1.45;
    }}
    .lightbox {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(9, 12, 11, 0.85);
      z-index: 40;
      padding: 12px;
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-inner {{
      width: min(95vw, 1280px);
      max-height: 94vh;
      border: 1px solid rgba(255, 255, 255, 0.25);
      border-radius: 10px;
      overflow: hidden;
      background: #101312;
    }}
    .lightbox-main {{
      display: grid;
      place-items: center;
      max-height: 85vh;
      overflow: auto;
    }}
    .lightbox-main img {{
      max-width: 100%;
      max-height: 83vh;
      object-fit: contain;
      display: block;
    }}
    .lightbox-foot {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.2);
      color: #e4ece9;
      font-size: 0.82rem;
      background: #171d1b;
    }}
    .lightbox-foot button {{
      border: 1px solid rgba(255, 255, 255, 0.35);
      border-radius: 7px;
      background: transparent;
      color: #f3f8f6;
      font: inherit;
      padding: 5px 9px;
    }}
    .hidden {{ display: none !important; }}
    @media (max-width: 900px) {{
      .pair {{ grid-template-columns: 1fr; }}
      .summary {{ width: 100%; margin-left: 0; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Pot Comparison View: {html_escape(run_a)} vs {html_escape(run_b)}</h1>
      <p class="sub">Same pot IDs shown side-by-side so continuity-carried mistakes are visible immediately.</p>
      <div class="meta">
        <span>Source CSV: <code>{html_escape(str(input_csv))}</code></span>
        <span>Generated (UTC): <code>{html_escape(generated_at)}</code></span>
        <span>Continuity-lock risk pots: <strong>{risk_count}</strong></span>
        <span>Variety drift pots: <strong>{drift_count}</strong></span>
      </div>
      <div class="run-grid">
        {run_summary(report_a, run_a)}
        {run_summary(report_b, run_b)}
      </div>
    </section>

    <section class="toolbar">
      <button id="filter-all" class="active" type="button">All Pots</button>
      <button id="filter-risk" type="button">Continuity Lock Risk</button>
      <button id="filter-drift" type="button">Variety Drift</button>
      <span class="summary" id="summary-line"></span>
    </section>

    <section class="grid" id="comparison-grid">
      {''.join(cards)}
    </section>
  </main>

  <div class="lightbox" id="lightbox" aria-hidden="true">
    <div class="lightbox-inner" role="dialog" aria-modal="true" aria-label="Photo comparison viewer">
      <div class="lightbox-main">
        <img id="lightbox-image" alt="" />
      </div>
      <div class="lightbox-foot">
        <span id="lightbox-caption"></span>
        <button id="lightbox-close" type="button">Close</button>
      </div>
    </div>
  </div>

  <script>
    (() => {{
      const grid = document.getElementById("comparison-grid");
      const summaryLine = document.getElementById("summary-line");
      const buttons = {{
        all: document.getElementById("filter-all"),
        risk: document.getElementById("filter-risk"),
        drift: document.getElementById("filter-drift"),
      }};
      const lightbox = document.getElementById("lightbox");
      const lightboxImage = document.getElementById("lightbox-image");
      const lightboxCaption = document.getElementById("lightbox-caption");
      const lightboxClose = document.getElementById("lightbox-close");

      function setActive(which) {{
        Object.entries(buttons).forEach(([key, button]) => {{
          button.classList.toggle("active", key === which);
        }});
      }}

      function applyFilter(which) {{
        const cards = Array.from(grid.querySelectorAll(".pot-card"));
        let visible = 0;
        cards.forEach((card) => {{
          const status = card.getAttribute("data-status") || "";
          const show =
            which === "all" ||
            (which === "risk" && status === "risk") ||
            (which === "drift" && status === "drift");
          card.classList.toggle("hidden", !show);
          if (show) visible += 1;
        }});
        summaryLine.textContent = `Visible pots: ${{visible}} / {expected_pots}`;
      }}

      buttons.all.addEventListener("click", () => {{
        setActive("all");
        applyFilter("all");
      }});
      buttons.risk.addEventListener("click", () => {{
        setActive("risk");
        applyFilter("risk");
      }});
      buttons.drift.addEventListener("click", () => {{
        setActive("drift");
        applyFilter("drift");
      }});

      function openLightbox(url, alt) {{
        if (!url) return;
        lightboxImage.src = url;
        lightboxImage.alt = alt || "";
        lightboxCaption.textContent = alt || "";
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
      }}

      function closeLightbox() {{
        lightbox.classList.remove("open");
        lightbox.setAttribute("aria-hidden", "true");
        lightboxImage.src = "";
        lightboxImage.alt = "";
        lightboxCaption.textContent = "";
      }}

      document.querySelectorAll("[data-open-lightbox='true']").forEach((el) => {{
        el.addEventListener("click", () => {{
          openLightbox(el.getAttribute("data-full") || "", el.getAttribute("data-alt") || "");
        }});
      }});
      lightboxClose.addEventListener("click", closeLightbox);
      lightbox.addEventListener("click", (event) => {{
        if (event.target === lightbox) closeLightbox();
      }});
      window.addEventListener("keydown", (event) => {{
        if (event.key === "Escape" && lightbox.classList.contains("open")) closeLightbox();
      }});

      applyFilter("all");
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build side-by-side pot comparison page for two runs."
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed intake CSV.",
    )
    parser.add_argument(
        "--run-a",
        default="",
        help="Left-side run date (YYYY-MM-DD). Defaults to the second-latest available run.",
    )
    parser.add_argument(
        "--run-b",
        default="",
        help="Right-side run date (YYYY-MM-DD). Defaults to the latest available run.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count for the comparison.",
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
        default=Path("tracker/pot-run-comparison.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.labeled_csv)
    resolved_run_a, resolved_run_b = resolve_run_dates(
        rows,
        args.run_a,
        args.run_b,
        preferred_default_pair=(DEFAULT_COMPARISON_RUN_A, DEFAULT_COMPARISON_RUN_B),
    )
    series_variety_map = load_series_variety_map(args.series_map_csv)
    pot_series_overrides = load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(args.baseline_map_csv)
    row_overrides = load_row_overrides(args.row_overrides_csv)

    expected_a = choose_expected_for_run(rows, resolved_run_a, args.expected_pots)
    expected_b = choose_expected_for_run(rows, resolved_run_b, args.expected_pots)

    mapped_a, report_a = build_mapping(
        rows=rows,
        run_date=resolved_run_a,
        expected_pots=expected_a,
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
    mapped_b, report_b = build_mapping(
        rows=rows,
        run_date=resolved_run_b,
        expected_pots=expected_b,
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

    by_pot_a = row_by_pot(mapped_a)
    by_pot_b = row_by_pot(mapped_b)
    page = stabilize_rendered_text(
        args.output_html,
        build_page(
            run_a=resolved_run_a,
            run_b=resolved_run_b,
            report_a=report_a,
            report_b=report_b,
            by_pot_a=by_pot_a,
            by_pot_b=by_pot_b,
            expected_pots=args.expected_pots,
            input_csv=args.labeled_csv,
        ),
    )
    write_text_if_changed(args.output_html, page)

    print(f"labeled_csv={args.labeled_csv}")
    print(f"run_a={resolved_run_a}")
    print(f"run_b={resolved_run_b}")
    print(f"expected_pots={args.expected_pots}")
    print(f"mapped_rows_a={len(mapped_a)}")
    print(f"mapped_rows_b={len(mapped_b)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
