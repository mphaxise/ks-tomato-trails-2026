#!/usr/bin/env python3
"""Build a pot-centric intake history page across all capture dates."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from build_tomato_pot_mapping import (
    build_mapping,
    load_baseline_variety_map,
    load_pot_series_overrides,
    load_series_variety_map,
    read_rows,
)


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
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", (raw or "").strip()).upper()
    matched = re.search(r"\b([0-9]{1,3})\s*T?\b", normalized)
    if not matched:
        return ""
    number = int(matched.group(1))
    if number <= 0:
        return ""
    return f"{number}T"


def pot_sort_key(pot_id: str) -> Tuple[int, str]:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return (10**9, pot_id or "")
    return (int(matched.group(1)), pot_id)


def derive_run_dates(rows: List[Dict[str, str]]) -> List[str]:
    return sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )


def expected_for_run(
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


def build_mappings_for_all_runs(
    rows: List[Dict[str, str]],
    run_dates: List[str],
    expected_pots: int,
    series_variety_map: Dict[int, str],
    pot_series_overrides: Dict[str, int],
    baseline_variety_map: Dict[str, str],
) -> Tuple[List[Dict[str, str]], Dict[str, Dict[str, object]]]:
    all_rows: List[Dict[str, str]] = []
    reports: Dict[str, Dict[str, object]] = {}
    for run_date in run_dates:
        expected = expected_for_run(rows, run_date, expected_pots)
        mapped, report = build_mapping(
            rows=rows,
            run_date=run_date,
            expected_pots=expected,
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
        )
        all_rows.extend(mapped)
        reports[run_date] = report
    return all_rows, reports


def organize_by_pot_and_date(
    mapping_rows: List[Dict[str, str]], expected_pots: int
) -> Dict[str, Dict[str, Dict[str, str]]]:
    out: Dict[str, Dict[str, Dict[str, str]]] = {
        f"{pot_number}T": {}
        for pot_number in range(1, expected_pots + 1)
    }
    for row in mapping_rows:
        pot_id = normalize_pot_id((row.get("pot_id", "") or "").strip())
        run_date = (row.get("run_date", "") or "").strip()
        if not pot_id or not run_date:
            continue
        out.setdefault(pot_id, {})
        out[pot_id][run_date] = row
    return out


def latest_variety_by_pot(
    by_pot_date: Dict[str, Dict[str, Dict[str, str]]]
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for pot_id, by_date in by_pot_date.items():
        if not by_date:
            out[pot_id] = ""
            continue
        latest_date = sorted(by_date.keys())[-1]
        out[pot_id] = (by_date[latest_date].get("variety_name", "") or "").strip()
    return out


def status_badge_class(final_status: str) -> str:
    status = (final_status or "").strip()
    if status.startswith("ready_"):
        return "ready"
    return "review"


def resolution_label(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "unknown"
    return text.replace("_", " ")


def run_summary_cards(
    run_dates: List[str], reports: Dict[str, Dict[str, object]]
) -> str:
    cards: List[str] = []
    for run_date in run_dates:
        report = reports.get(run_date, {})
        selected_rows = int(report.get("selected_rows", 0) or 0)
        unique_pot_count = int(report.get("unique_pot_count", 0) or 0)
        ocr_confirmed_rows = int(report.get("ocr_confirmed_rows", 0) or 0)
        final_status_counts = report.get("final_status_counts", {})
        ready_auto = 0
        if isinstance(final_status_counts, dict):
            ready_auto = int(final_status_counts.get("ready_auto_resolved", 0) or 0)
        cards.append(
            "<article class='run-card'>"
            f"<h3>{html_escape(run_date)}</h3>"
            f"<p>Rows: <strong>{selected_rows}</strong></p>"
            f"<p>Pots mapped: <strong>{unique_pot_count}</strong></p>"
            f"<p>OCR confirmed: <strong>{ocr_confirmed_rows}</strong></p>"
            f"<p>Auto-resolved: <strong>{ready_auto}</strong></p>"
            "</article>"
        )
    return "\n".join(cards)


def build_pot_sections(
    run_dates: List[str],
    by_pot_date: Dict[str, Dict[str, Dict[str, str]]],
    varieties: Dict[str, str],
) -> str:
    sections: List[str] = []
    for pot_id in sorted(by_pot_date.keys(), key=pot_sort_key):
        timeline_cards: List[str] = []
        for run_date in run_dates:
            row = by_pot_date.get(pot_id, {}).get(run_date)
            if row is None:
                timeline_cards.append(
                    "<article class='shot missing'>"
                    f"<h4>{html_escape(run_date)}</h4>"
                    "<div class='missing-box'>No mapped photo for this intake</div>"
                    "</article>"
                )
                continue

            photo_url = (row.get("photo_url", "") or "").strip()
            variety_name = (row.get("variety_name", "") or "").strip()
            source_asset_id = (row.get("source_asset_id", "") or "").strip()
            final_status = (row.get("final_status", "") or "").strip()
            resolution_source = (row.get("resolution_source", "") or "").strip()
            review_status = (row.get("review_status_label", "") or "").strip()
            status_class = status_badge_class(final_status)
            status_label = review_status or final_status.replace("_", " ")
            image_html = (
                "<button class='img-btn' data-open-lightbox='true' "
                f"data-full='{attr_escape(photo_url)}' "
                f"data-alt='{attr_escape(f'{pot_id} {run_date}')}'>"
                f"<img src='{html_escape(photo_url)}' alt='{html_escape(f'{pot_id} {run_date}')}' loading='lazy' />"
                "</button>"
                if photo_url
                else "<div class='missing-box'>No photo URL</div>"
            )
            timeline_cards.append(
                "<article class='shot'>"
                f"<h4>{html_escape(run_date)}</h4>"
                f"{image_html}"
                "<div class='meta'>"
                f"<p><strong>{html_escape(variety_name)}</strong></p>"
                f"<p class='badge {status_class}'>{html_escape(status_label)}</p>"
                f"<p>Resolution: {html_escape(resolution_label(resolution_source))}</p>"
                f"<p>Asset: {html_escape(source_asset_id)}</p>"
                "</div>"
                "</article>"
            )

        sections.append(
            f"<section class='pot' id='pot-{html_escape(pot_id)}'>"
            "<header class='pot-head'>"
            f"<h2>{html_escape(pot_id)}</h2>"
            f"<p>{html_escape(varieties.get(pot_id, '') or 'Variety unresolved')}</p>"
            "</header>"
            "<div class='timeline'>"
            f"{''.join(timeline_cards)}"
            "</div>"
            "</section>"
        )
    return "\n".join(sections)


def build_page(
    input_csv: Path,
    run_dates: List[str],
    reports: Dict[str, Dict[str, object]],
    by_pot_date: Dict[str, Dict[str, Dict[str, str]]],
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    pot_ids = sorted(by_pot_date.keys(), key=pot_sort_key)
    pot_nav = " ".join(
        f"<a href='#pot-{html_escape(pot_id)}'>{html_escape(pot_id)}</a>"
        for pot_id in pot_ids
    )
    latest_varieties = latest_variety_by_pot(by_pot_date)
    sections_html = build_pot_sections(run_dates, by_pot_date, latest_varieties)
    runs_html = run_summary_cards(run_dates, reports)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>K's Tomato Trails 2026: Pot Intake History</title>
  <style>
    :root {{
      --bg: #f4f0e3;
      --card: #fffdf7;
      --ink: #1f2b29;
      --line: #d8d1c2;
      --leaf: #2f6947;
      --tomato: #8a2d2b;
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
    .wrap {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 18px 14px 30px;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(140deg, rgba(47, 105, 71, 0.14), rgba(53, 89, 127, 0.09));
      padding: 16px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.35rem, 3vw, 2.1rem);
    }}
    .sub {{
      margin: 0;
      color: #4d5c57;
      font-size: 0.94rem;
    }}
    .meta {{
      margin-top: 7px;
      color: #52625d;
      font-size: 0.84rem;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
    }}
    .run-grid {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
    }}
    .run-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
    }}
    .run-card h3 {{
      margin: 0 0 8px;
      color: #3f514c;
      font-size: 0.92rem;
    }}
    .run-card p {{
      margin: 0;
      color: #5c6c67;
      font-size: 0.82rem;
      line-height: 1.45;
    }}
    .pot-nav {{
      position: sticky;
      top: 8px;
      z-index: 6;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 9px;
      margin-bottom: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}
    .pot-nav span {{
      font-size: 0.8rem;
      color: #556660;
      margin-right: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .pot-nav a {{
      border: 1px solid #d8cfbf;
      background: #fffef9;
      color: #2d3d39;
      text-decoration: none;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .pot {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px;
      margin-bottom: 10px;
    }}
    .pot-head {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px;
      align-items: baseline;
      margin-bottom: 8px;
      border-bottom: 1px solid #ece4d4;
      padding-bottom: 6px;
    }}
    .pot-head h2 {{
      margin: 0;
      font-size: 1.08rem;
      color: #23332f;
    }}
    .pot-head p {{
      margin: 0;
      color: #556560;
      font-size: 0.9rem;
      font-weight: 700;
    }}
    .timeline {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
    }}
    .shot {{
      border: 1px solid #e2dac9;
      border-radius: 10px;
      background: #fefcf5;
      overflow: hidden;
    }}
    .shot h4 {{
      margin: 0;
      padding: 7px 8px;
      background: #f6f1e5;
      border-bottom: 1px solid #e6dfce;
      font-size: 0.82rem;
      color: #4d5d58;
      letter-spacing: 0.03em;
    }}
    .img-btn {{
      width: 100%;
      padding: 0;
      border: 0;
      margin: 0;
      background: #ece5d5;
      cursor: zoom-in;
      aspect-ratio: 4 / 3;
      display: block;
    }}
    .img-btn img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .missing-box {{
      min-height: 120px;
      display: grid;
      place-items: center;
      color: #6a7772;
      font-size: 0.82rem;
      padding: 10px;
      text-align: center;
      background: #f1ebdc;
    }}
    .meta p {{
      margin: 0;
      font-size: 0.79rem;
      color: #53635e;
      line-height: 1.45;
    }}
    .shot .meta {{
      padding: 8px;
      display: grid;
      gap: 4px;
    }}
    .badge {{
      display: inline-block;
      width: fit-content;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.73rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .badge.ready {{
      background: #e4f2e8;
      border: 1px solid #c8dfcf;
      color: #1c5d36;
    }}
    .badge.review {{
      background: #faecd5;
      border: 1px solid #efce9b;
      color: #764813;
    }}
    .lightbox {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 12px;
      z-index: 40;
      background: rgba(9, 12, 11, 0.86);
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-inner {{
      width: min(96vw, 1400px);
      max-height: 95vh;
      border: 1px solid rgba(255, 255, 255, 0.28);
      border-radius: 12px;
      overflow: hidden;
      background: #101312;
    }}
    .lightbox-main {{
      display: grid;
      place-items: center;
      min-height: 300px;
      max-height: 86vh;
      overflow: auto;
    }}
    .lightbox-main img {{
      max-width: 100%;
      max-height: 84vh;
      object-fit: contain;
      display: block;
    }}
    .lightbox-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.18);
      color: #e3ebe8;
      font-size: 0.82rem;
      background: #151b19;
    }}
    .btn {{
      border: 1px solid rgba(255, 255, 255, 0.35);
      background: transparent;
      color: #f4f8f6;
      padding: 5px 9px;
      border-radius: 7px;
      cursor: pointer;
      font: inherit;
    }}
    @media (max-width: 820px) {{
      .timeline {{
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      }}
      .pot-head {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Pot Intake History Across Photo Runs</h1>
      <p class="sub">For each pot ID (`1T` to `32T`), this page shows the mapped photo for each intake date so we can verify continuity over time.</p>
      <div class="meta">
        <span>Source CSV: <code>{html_escape(str(input_csv))}</code></span>
        <span>Run dates: <strong>{html_escape(", ".join(run_dates))}</strong></span>
        <span>Generated (UTC): <code>{html_escape(generated_at)}</code></span>
      </div>
      <div class="run-grid">
        {runs_html}
      </div>
    </section>
    <nav class="pot-nav">
      <span>Jump to Pot:</span>
      {pot_nav}
    </nav>
    {sections_html}
  </main>

  <div class="lightbox" id="lightbox" aria-hidden="true">
    <div class="lightbox-inner" role="dialog" aria-modal="true" aria-label="Photo viewer">
      <div class="lightbox-main">
        <img id="lightbox-image" alt="" />
      </div>
      <div class="lightbox-footer">
        <span id="lightbox-caption"></span>
        <button class="btn" id="lightbox-close" type="button">Close</button>
      </div>
    </div>
  </div>

  <script>
    (() => {{
      const lightbox = document.getElementById("lightbox");
      const lightboxImage = document.getElementById("lightbox-image");
      const lightboxCaption = document.getElementById("lightbox-caption");
      const closeBtn = document.getElementById("lightbox-close");

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

      closeBtn.addEventListener("click", closeLightbox);
      lightbox.addEventListener("click", (event) => {{
        if (event.target === lightbox) closeLightbox();
      }});
      window.addEventListener("keydown", (event) => {{
        if (event.key === "Escape" && lightbox.classList.contains("open")) closeLightbox();
      }});
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build pot-centric intake history page for all run dates."
    )
    parser.add_argument(
        "--labeled-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed intake CSV.",
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
        help="Series-number to variety map CSV.",
    )
    parser.add_argument(
        "--pot-series-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
        help="Pot-level series override CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline mapping CSV for continuity reconciliation.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected pot count for standard run-day photo intake.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/pot-intake-history.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.labeled_csv)
    run_dates = derive_run_dates(rows)
    if not run_dates:
        raise ValueError("No capture_date values found in labeled CSV.")

    series_variety_map = load_series_variety_map(args.series_map_csv)
    pot_series_overrides = load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = load_baseline_variety_map(args.baseline_map_csv)
    mapping_rows, reports = build_mappings_for_all_runs(
        rows=rows,
        run_dates=run_dates,
        expected_pots=args.expected_pots,
        series_variety_map=series_variety_map,
        pot_series_overrides=pot_series_overrides,
        baseline_variety_map=baseline_variety_map,
    )
    by_pot_date = organize_by_pot_and_date(mapping_rows, args.expected_pots)
    page = build_page(args.labeled_csv, run_dates, reports, by_pot_date)

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"labeled_csv={args.labeled_csv}")
    print(f"run_dates={','.join(run_dates)}")
    print(f"expected_pots={args.expected_pots}")
    print(f"mapped_rows={len(mapping_rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
