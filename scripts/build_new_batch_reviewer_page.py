#!/usr/bin/env python3
"""Build focused reviewer page for low-confidence new-batch rows."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing CSV header")
        return list(reader)


def esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def build_page(queue_csv: Path, rows: List[Dict[str, str]]) -> str:
    generated = datetime.now(timezone.utc).isoformat()

    ui_rows: List[Dict[str, str]] = []
    for row in rows:
        row_index = (row.get("row_index", "") or "").strip()
        asset = (row.get("source_asset_id", "") or "").strip()
        image_path = Path(f"local/non_tomato_species/images/{int(row_index):02d}_{asset}.jpg")
        image_url = f"../{image_path.as_posix()}" if image_path.exists() else ""
        predicted = (row.get("predicted_classification_label", "") or "").strip()
        suggested_common = "Tomato" if predicted == "tomato" else (row.get("predicted_variety_name", "") or "").strip()
        suggested_variety = (row.get("predicted_variety_name", "") or "").strip()
        suggested_scientific = (
            "Solanum lycopersicum"
            if predicted == "tomato"
            else ""
        )
        ui_rows.append(
            {
                "row_index": row_index,
                "capture_date": (row.get("capture_date", "") or "").strip(),
                "source_asset_id": asset,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "image_url": image_url,
                "predicted_classification_label": predicted,
                "margin": (row.get("margin", "") or "").strip(),
                "tomato_similarity": (row.get("tomato_similarity", "") or "").strip(),
                "non_tomato_similarity": (row.get("non_tomato_similarity", "") or "").strip(),
                "classification_label": predicted or "unknown",
                "species_common_name": suggested_common,
                "variety_name": suggested_variety,
                "species_scientific_name": suggested_scientific,
                "notes_append": "",
                "verdict": "pending",
            }
        )

    rows_json = json.dumps(ui_rows, ensure_ascii=True)
    total = len(ui_rows)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>New Batch Reviewer</title>
  <style>
    :root {{ --bg:#f4f0e3; --card:#fffdf7; --ink:#1f2b29; --line:#d8d1c2; --green:#2f6947; --amber:#8a5c23; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Trebuchet MS",sans-serif; background:var(--bg); color:var(--ink); }}
    .wrap {{ max-width:1340px; margin:0 auto; padding:14px; }}
    .hero {{ border:1px solid var(--line); border-radius:12px; background:var(--card); padding:12px; margin-bottom:10px; }}
    .toolbar {{ position:sticky; top:8px; z-index:10; border:1px solid var(--line); border-radius:12px; background:var(--card); padding:10px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:10px; }}
    .toolbar select,.toolbar button {{ border:1px solid #d4cdbd; border-radius:8px; background:#fffef9; padding:6px 10px; font:inherit; }}
    .toolbar .primary {{ background:#35597f; color:#fff; border-color:#35597f; font-weight:700; }}
    .stats {{ margin-left:auto; font-size:.84rem; color:#4e5e58; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:10px; }}
    .card {{ border:1px solid var(--line); border-radius:12px; background:var(--card); overflow:hidden; }}
    .head {{ padding:8px 10px; border-bottom:1px solid #e7decd; background:#f6f1e5; }}
    .head p,.meta p {{ margin:3px 0; font-size:.8rem; }}
    .img {{ background:#ece4d3; }}
    .img img {{ width:100%; display:block; aspect-ratio:4/3; object-fit:cover; }}
    .missing {{ min-height:140px; display:grid; place-items:center; color:#6d7a74; font-size:.8rem; }}
    .meta {{ padding:8px 10px; border-top:1px solid #ece4d3; border-bottom:1px solid #ece4d3; }}
    .form {{ padding:8px 10px 10px; display:grid; gap:6px; }}
    label {{ display:grid; gap:3px; font-size:.78rem; color:#4e5e58; }}
    input,select,textarea {{ border:1px solid #d4cdbd; border-radius:7px; padding:6px 8px; background:#fffef9; font:inherit; color:var(--ink); }}
    textarea {{ min-height:48px; resize:vertical; }}
    .hidden {{ display:none !important; }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <section class=\"hero\">
      <h1>New Batch Reviewer (Low-Confidence Queue)</h1>
      <p>Source queue: <code>{esc(str(queue_csv))}</code></p>
      <p>Total rows: <strong>{total}</strong></p>
      <p>Generated (UTC): <code>{esc(generated)}</code></p>
    </section>

    <section class=\"toolbar\">
      <label>Capture Date
        <select id=\"date-filter\"><option value=\"all\">All</option></select>
      </label>
      <label>Prediction
        <select id=\"pred-filter\">
          <option value=\"all\">All</option>
          <option value=\"tomato\">Tomato</option>
          <option value=\"non_tomato\">Non-tomato</option>
        </select>
      </label>
      <button class=\"primary\" id=\"export-btn\">Export Overrides CSV</button>
      <button id=\"reset-btn\">Reset Local Edits</button>
      <span class=\"stats\" id=\"stats\"></span>
    </section>

    <section class=\"grid\" id=\"grid\"></section>
  </main>

<script>
(() => {{
  const STORAGE_KEY = "new_batch_reviewer_v1";
  const rows = {rows_json};
  const grid = document.getElementById("grid");
  const stats = document.getElementById("stats");
  const dateFilter = document.getElementById("date-filter");
  const predFilter = document.getElementById("pred-filter");
  const exportBtn = document.getElementById("export-btn");
  const resetBtn = document.getElementById("reset-btn");

  const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}") || {{}};

  rows.forEach((row, i) => {{ row._id = `row-${{i+1}}`; if (!state[row._id]) state[row._id] = {{...row}}; }});

  function toCsvValue(v) {{
    const text = v == null ? "" : String(v);
    if (text.includes(",") || text.includes("\"") || text.includes("\n")) return `"${{text.replaceAll('"','""')}}"`;
    return text;
  }}

  function render() {{
    const dVal = dateFilter.value || "all";
    const pVal = predFilter.value || "all";
    grid.innerHTML = "";
    let visible = 0;

    rows.forEach((row) => {{
      const s = state[row._id];
      const show = (dVal === "all" || row.capture_date === dVal) && (pVal === "all" || row.predicted_classification_label === pVal);
      if (!show) return;
      visible += 1;

      const card = document.createElement("article");
      card.className = "card";
      card.innerHTML = `
        <header class='head'>
          <p><strong>row=${{row.row_index}}</strong> | ${{row.capture_date}} | pred=<strong>${{row.predicted_classification_label}}</strong></p>
          <p>asset=${{row.source_asset_id}}</p>
        </header>
        <div class='img'>${{row.image_url ? `<a href='${{row.photo_url}}' target='_blank' rel='noreferrer'><img src='${{row.image_url}}' alt='photo' /></a>` : `<div class='missing'>No image</div>`}}</div>
        <div class='meta'>
          <p>margin=<strong>${{row.margin}}</strong> | tomato_sim=${{row.tomato_similarity}} | non_tomato_sim=${{row.non_tomato_similarity}}</p>
        </div>
        <div class='form'>
          <label>Verdict
            <select data-id='${{row._id}}' data-field='verdict'>
              <option value='pending'>Pending</option>
              <option value='accept'>Accept suggestion</option>
              <option value='correct'>Correct suggestion</option>
            </select>
          </label>
          <label>Classification
            <select data-id='${{row._id}}' data-field='classification_label'>
              <option value='tomato'>tomato</option>
              <option value='non_tomato'>non_tomato</option>
              <option value='unknown'>unknown</option>
            </select>
          </label>
          <label>Common Name<input data-id='${{row._id}}' data-field='species_common_name' value='${{(s.species_common_name||"").replaceAll("'","&#39;")}}' /></label>
          <label>Variety<input data-id='${{row._id}}' data-field='variety_name' value='${{(s.variety_name||"").replaceAll("'","&#39;")}}' /></label>
          <label>Scientific<input data-id='${{row._id}}' data-field='species_scientific_name' value='${{(s.species_scientific_name||"").replaceAll("'","&#39;")}}' /></label>
          <label>Notes<textarea data-id='${{row._id}}' data-field='notes_append'>${{s.notes_append||""}}</textarea></label>
        </div>`;
      grid.appendChild(card);
    }});

    document.querySelectorAll("[data-id][data-field]").forEach((el) => {{
      const id = el.getAttribute("data-id");
      const field = el.getAttribute("data-field");
      if (!id || !field) return;
      el.value = state[id][field] || "";
      el.addEventListener("input", () => {{ state[id][field] = el.value; localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }});
      if (el.tagName === "SELECT") el.addEventListener("change", () => {{ state[id][field] = el.value; localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }});
    }});

    stats.textContent = `Visible: ${{visible}} / ${{rows.length}}`;
  }}

  function exportCsv() {{
    const output = [];
    rows.forEach((row) => {{
      const s = state[row._id];
      if (!s) return;
      if ((s.verdict || "pending") === "pending") return;
      output.push({{
        row_index: row.row_index,
        source_asset_id: row.source_asset_id,
        classification_label: s.classification_label || "unknown",
        species_common_name: s.species_common_name || "",
        variety_name: s.variety_name || "",
        species_scientific_name: s.species_scientific_name || "",
        confidence: "0.75",
        labeling_method: "new_batch_reviewer_manual",
        notes_append: s.notes_append || "",
      }});
    }});
    if (!output.length) {{ alert("No reviewed rows to export."); return; }}
    const headers = Object.keys(output[0]);
    const lines = [headers.join(",")];
    output.forEach((row) => lines.push(headers.map((h) => toCsvValue(row[h])).join(",")));
    const blob = new Blob([lines.join("\n") + "\n"], {{type:"text/csv;charset=utf-8"}});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `new_batch_overrides_${{new Date().toISOString().replaceAll(':','-')}}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  }}

  function initFilters() {{
    const dates = Array.from(new Set(rows.map((r) => r.capture_date))).sort();
    dates.forEach((d) => {{ const o = document.createElement("option"); o.value = d; o.textContent = d; dateFilter.appendChild(o); }});
    dateFilter.addEventListener("change", render);
    predFilter.addEventListener("change", render);
  }}

  exportBtn.addEventListener("click", exportCsv);
  resetBtn.addEventListener("click", () => {{ if (!confirm("Reset all local edits?")) return; localStorage.removeItem(STORAGE_KEY); location.reload(); }});
  initFilters();
  render();
}})();
</script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build focused reviewer page for low-confidence new-batch queue.",
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_7/new_batch_unknown_remaining_review_queue.csv"),
        help="Low-confidence new-batch queue CSV.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/new-batch-reviewer.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.queue_csv) if args.queue_csv.exists() else []
    html = build_page(args.queue_csv, rows)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    print(f"queue_csv={args.queue_csv}")
    print(f"rows={len(rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
