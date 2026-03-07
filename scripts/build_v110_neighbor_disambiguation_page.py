#!/usr/bin/env python3
"""Build a v1.10 neighbor-disambiguation queue CSV and HTML page from pot CV metrics."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


QUEUE_FIELDNAMES = [
    "queue_priority_rank",
    "severity_score",
    "pot_id",
    "variety_name",
    "tracking_readiness",
    "anchor_mode",
    "focus_score",
    "pot_coverage",
    "neighbor_spill_ratio",
    "spill_in_pot_ratio",
    "chlorosis_ratio",
    "growth_delta",
    "capture_date",
    "disambiguation_note",
    "next_step_text",
    "overlay_path",
    "crop_path",
    "photo_url",
    "source_asset_id",
]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv_rows(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_json_optional(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def pot_sort_key(pot_id: str) -> Tuple[int, str]:
    cleaned = (pot_id or "").strip().upper()
    if cleaned.endswith("T") and cleaned[:-1].isdigit():
        return int(cleaned[:-1]), cleaned
    return 10_000, cleaned


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


def severity_score(row: Dict[str, str]) -> float:
    spill = safe_float(row.get("neighbor_spill_ratio")) or 0.0
    focus = safe_float(row.get("focus_score")) or 0.0
    coverage = safe_float(row.get("pot_coverage")) or 0.0
    readiness = (row.get("tracking_readiness", "") or "").strip().lower()
    readiness_penalty = {"low": 0.10, "moderate": 0.05, "high": 0.0}.get(readiness, 0.03)
    coverage_component = min(max(coverage, 0.0), 0.08) / 0.08 if coverage > 0 else 0.0
    return (spill * 0.70) + ((1.0 - focus) * 0.15) + (coverage_component * 0.05) + readiness_penalty


def build_disambiguation_note(row: Dict[str, str]) -> str:
    spill = safe_float(row.get("neighbor_spill_ratio")) or 0.0
    focus = safe_float(row.get("focus_score")) or 0.0
    readiness = (row.get("tracking_readiness", "") or "").strip().lower()

    if spill >= 0.70:
        return "Severe neighbor overlap. Lock the pot walls first, then isolate only foliage clearly rooted inside that pot."
    if spill >= 0.55:
        return "High spill case. Treat the current overlay as a hint only and separate target leaves from adjacent pots before tracing."
    if readiness == "low" or focus < 0.50:
        return "Weak focus and neighbor spill combine here. Verify the pot center manually before deciding which canopy belongs to the target pot."
    return "Moderate overlap. Trace the pot interior first, then keep the canopy tight to that boundary and exclude crossing leaves."


def build_queue_rows(metrics_rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    filtered = [
        dict(row)
        for row in metrics_rows
        if (row.get("next_step_code", "") or "").strip() == "needs_neighbor_disambiguation"
        and (row.get("pot_id", "") or "").strip()
    ]
    filtered.sort(
        key=lambda row: (
            -severity_score(row),
            -(safe_float(row.get("neighbor_spill_ratio")) or 0.0),
            pot_sort_key(row.get("pot_id", "")),
        )
    )

    output: List[Dict[str, str]] = []
    for index, row in enumerate(filtered, start=1):
        enriched = dict(row)
        enriched["queue_priority_rank"] = str(index)
        enriched["severity_score"] = f"{severity_score(row):.3f}"
        enriched["disambiguation_note"] = build_disambiguation_note(row)
        output.append(enriched)
    return output


def build_page(
    queue_rows: Sequence[Dict[str, str]],
    summary: Dict[str, object],
    source_metrics_csv: Path,
    source_queue_csv: Path,
) -> str:
    generated_at = str(summary.get("created_at", "") or datetime.now(timezone.utc).isoformat())
    run_date = str(summary.get("run_date", "") or "")
    cards: List[str] = []
    for row in queue_rows:
        pot_id = (row.get("pot_id", "") or "").strip()
        variety = (row.get("variety_name", "") or "").strip()
        overlay_path = path_for_page(row.get("overlay_path", "") or "")
        crop_path = path_for_page(row.get("crop_path", "") or "")
        photo_url = path_for_page(row.get("photo_url", "") or "")
        rank = (row.get("queue_priority_rank", "") or "").strip()
        readiness = (row.get("tracking_readiness", "") or "").strip() or "n/a"
        anchor_mode = (row.get("anchor_mode", "") or "").strip() or "n/a"
        focus = safe_float(row.get("focus_score")) or 0.0
        spill = safe_float(row.get("neighbor_spill_ratio")) or 0.0
        in_pot_spill = safe_float(row.get("spill_in_pot_ratio")) or 0.0
        coverage = safe_float(row.get("pot_coverage")) or 0.0
        severity = safe_float(row.get("severity_score")) or 0.0
        note = (row.get("disambiguation_note", "") or "").strip()
        next_step_text = (row.get("next_step_text", "") or "").strip()

        overlay_html = (
            f"<img src='{attr_escape(overlay_path)}' alt='Overlay for {attr_escape(pot_id)}' loading='lazy' />"
            if overlay_path
            else "<div class='missing'>No overlay</div>"
        )
        crop_html = (
            f"<img src='{attr_escape(crop_path)}' alt='Crop for {attr_escape(pot_id)}' loading='lazy' />"
            if crop_path
            else "<div class='missing'>No crop</div>"
        )
        links = []
        if photo_url:
            links.append(
                f"<a href='{attr_escape(photo_url)}' target='_blank' rel='noreferrer'>Original</a>"
            )
        if overlay_path:
            links.append(
                f"<a href='{attr_escape(overlay_path)}' target='_blank' rel='noreferrer'>Overlay</a>"
            )
        if crop_path:
            links.append(
                f"<a href='{attr_escape(crop_path)}' target='_blank' rel='noreferrer'>Crop</a>"
            )
        link_html = " | ".join(links)

        cards.append(
            "<article class='card'>"
            "<header class='card-head'>"
            f"<p class='rank'>Queue {html_escape(rank)}</p>"
            f"<h2>{html_escape(pot_id)} <span>{html_escape(variety)}</span></h2>"
            "</header>"
            "<div class='images'>"
            f"<figure><figcaption>Overlay</figcaption>{overlay_html}</figure>"
            f"<figure><figcaption>Crop</figcaption>{crop_html}</figure>"
            "</div>"
            "<dl class='stats'>"
            f"<div><dt>Severity</dt><dd>{severity:.3f}</dd></div>"
            f"<div><dt>Readiness</dt><dd>{html_escape(readiness)}</dd></div>"
            f"<div><dt>Anchor</dt><dd>{html_escape(anchor_mode)}</dd></div>"
            f"<div><dt>Focus</dt><dd>{focus:.3f}</dd></div>"
            f"<div><dt>Neighbor Spill</dt><dd>{spill * 100:.1f}%</dd></div>"
            f"<div><dt>In-Pot Spill</dt><dd>{in_pot_spill * 100:.1f}%</dd></div>"
            f"<div><dt>Coverage</dt><dd>{coverage * 100:.1f}%</dd></div>"
            "</dl>"
            f"<p class='note'>{html_escape(note)}</p>"
            f"<p class='detail'>{html_escape(next_step_text)}</p>"
            f"<p class='links'>{link_html}</p>"
            "</article>"
        )

    card_html = "\n".join(cards) if cards else "<p class='empty'>No neighbor-disambiguation rows found.</p>"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>V1.10 Neighbor Disambiguation Queue</title>
  <style>
    :root {{
      --bg: #f3ecdf;
      --card: #fffdf8;
      --ink: #1c2926;
      --line: #d9cfbf;
      --accent: #6f4d2d;
      --leaf: #2f6947;
      --alert: #8c3b28;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: \"Avenir Next\", \"Trebuchet MS\", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 420px at 115% -10%, #ded2bb 0%, transparent 60%),
        radial-gradient(800px 380px at -10% 120%, #e5d9c1 0%, transparent 60%),
        linear-gradient(160deg, #f4eee1, #ece4d4);
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px 16px 44px;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      background: linear-gradient(145deg, rgba(140, 59, 40, 0.10), rgba(47, 105, 71, 0.08));
      margin-bottom: 16px;
      display: grid;
      gap: 12px;
      grid-template-columns: 1.6fr 1fr;
    }}
    h1 {{
      margin: 0 0 8px;
      font-family: \"Iowan Old Style\", \"Palatino Linotype\", serif;
      font-size: clamp(1.5rem, 4vw, 2.5rem);
    }}
    .hero p {{
      margin: 0;
      color: #495a56;
    }}
    .hero-meta {{
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .meta-chip {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.75);
      padding: 10px 12px;
      font-size: 0.92rem;
    }}
    .guide {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--card);
      padding: 16px;
      margin-bottom: 16px;
    }}
    .guide h2 {{
      margin: 0 0 10px;
      font-size: 1.08rem;
    }}
    .guide ul {{
      margin: 0;
      padding-left: 18px;
      color: #485854;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 12px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--card);
      overflow: hidden;
    }}
    .card-head {{
      padding: 12px 14px;
      border-bottom: 1px solid #ece3d2;
      background: #f8f2e6;
    }}
    .rank {{
      margin: 0 0 4px;
      color: var(--alert);
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .card-head h2 {{
      margin: 0;
      font-size: 1.1rem;
    }}
    .card-head span {{
      color: #5c6d68;
      font-weight: 500;
      margin-left: 6px;
      font-size: 0.92rem;
    }}
    .images {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      padding: 12px;
    }}
    figure {{
      margin: 0;
      border: 1px solid #e6dccb;
      border-radius: 12px;
      background: #faf7ef;
      overflow: hidden;
    }}
    figcaption {{
      padding: 8px 10px;
      font-size: 0.78rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #60706a;
      border-bottom: 1px solid #e6dccb;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #ebe3d2;
    }}
    .missing {{
      padding: 40px 10px;
      text-align: center;
      color: #6a7874;
    }}
    .stats {{
      margin: 0;
      padding: 0 12px 12px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }}
    .stats div {{
      border: 1px solid #e6dccb;
      border-radius: 10px;
      padding: 8px;
      background: #faf7ef;
    }}
    .stats dt {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #677873;
    }}
    .stats dd {{
      margin: 4px 0 0;
      font-size: 0.94rem;
      font-weight: 700;
      color: #243532;
    }}
    .note, .detail, .links {{
      margin: 0;
      padding: 0 12px 12px;
      color: #465854;
      font-size: 0.92rem;
    }}
    .links a {{
      color: #1d5778;
      text-decoration: none;
      font-weight: 700;
    }}
    .footer {{
      margin-top: 16px;
      color: #566864;
      font-size: 0.84rem;
    }}
    @media (max-width: 980px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main>
    <section class=\"hero\">
      <div>
        <p class=\"rank\">V1.10 Hard Cases</p>
        <h1>Neighbor Disambiguation Queue</h1>
        <p>These pots still fail the clean mask gate because neighbor foliage dominates the crop. Use this packet after the seed set to test whether manual pot-boundary labeling can rescue the hardest multi-pot scenes.</p>
      </div>
      <div class=\"hero-meta\">
        <div class=\"meta-chip\"><strong>Run date:</strong> {html_escape(run_date or "n/a")}</div>
        <div class=\"meta-chip\"><strong>Queued pots:</strong> {len(queue_rows)}</div>
        <div class=\"meta-chip\"><strong>Metrics source:</strong> <code>{html_escape(str(source_metrics_csv))}</code></div>
        <div class=\"meta-chip\"><strong>Queue CSV:</strong> <code>{html_escape(str(source_queue_csv))}</code></div>
        <div class=\"meta-chip\"><strong>Generated (UTC):</strong> {html_escape(generated_at)}</div>
      </div>
    </section>
    <section class=\"guide\">
      <h2>Disambiguation Guidance</h2>
      <ul>
        <li>Trace the target pot walls first. Only then decide which leaves belong to the target canopy.</li>
        <li>Exclude crossing leaves from neighboring pots even when the overlay spills over them.</li>
        <li>If the target foliage cannot be separated with confidence, keep the boundary tight and note the ambiguity instead of widening the mask.</li>
        <li>Use this queue after the mask seed pack, not before it, so label style stays consistent.</li>
      </ul>
    </section>
    <section class=\"grid\">
      {card_html}
    </section>
    <p class=\"footer\">Derived from the isolated v1.10 track. Rebuild with <code>python3 scripts/build_v110_neighbor_disambiguation_page.py</code>.</p>
  </main>
</body>
</html>
"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=Path("data/research/v1_10/pot_cv_metrics.csv"),
        help="Full v1.10 metrics CSV.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/research/v1_10/pot_cv_summary.json"),
        help="v1.10 summary JSON.",
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_10/neighbor_disambiguation_queue.csv"),
        help="Output CSV for neighbor disambiguation queue rows.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/v1-10-neighbor-disambiguation.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    metrics_rows = read_csv_rows(args.metrics_csv)
    summary = read_json_optional(args.summary_json)
    queue_rows = build_queue_rows(metrics_rows)
    if not queue_rows:
        raise ValueError("No rows found for neighbor disambiguation.")

    write_csv_rows(args.queue_csv, QUEUE_FIELDNAMES, queue_rows)

    html = build_page(
        queue_rows=queue_rows,
        summary=summary,
        source_metrics_csv=args.metrics_csv,
        source_queue_csv=args.queue_csv,
    )
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
