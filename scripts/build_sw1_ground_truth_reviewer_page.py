#!/usr/bin/env python3
"""Build SW-1 weak-run ground-truth reviewer page."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


TEMPLATE_FIELDS = [
    "run_date",
    "row_index",
    "source_asset_id",
    "photo_url",
    "predicted_pot_id",
    "predicted_pot_number",
    "ocr_match_variants",
    "ocr_numbers_detected",
    "label_crop_path",
    "center_crop_path",
    "full_crop_path",
    "true_pot_id",
    "true_variety_name",
    "truth_source",
    "truth_note",
    "reviewer",
    "reviewed_at",
]


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


def slugify(value: str) -> str:
    out = []
    for char in (value or "").strip().lower():
        if char.isalnum():
            out.append(char)
        else:
            out.append("_")
    merged = "".join(out)
    while "__" in merged:
        merged = merged.replace("__", "_")
    return merged.strip("_")


def copy_asset(path: Path, prefix: str, suffix: str, assets_dir: Path, page_dir: Path) -> str:
    if not path.exists():
        return ""
    ext = path.suffix if path.suffix else ".jpg"
    target = assets_dir / f"{prefix}_{suffix}{ext}"
    shutil.copy2(path, target)
    rel = Path(os.path.relpath(target, page_dir)).as_posix()
    if not rel.startswith("."):
        rel = f"./{rel}"
    return rel


def prepare_rows(rows: List[Dict[str, str]], assets_dir: Path, page_dir: Path) -> List[Dict[str, str]]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    output: List[Dict[str, str]] = []
    for row in rows:
        run_date = (row.get("run_date", "") or "").strip()
        row_index = (row.get("row_index", "") or "").strip()
        asset = (row.get("source_asset_id", "") or "").strip()
        prefix = f"{slugify(run_date)}_{slugify(row_index)}_{slugify(asset[:12])}"

        label_path = Path((row.get("label_crop_path", "") or "").strip())
        center_path = Path((row.get("center_crop_path", "") or "").strip())
        full_path = Path((row.get("full_crop_path", "") or "").strip())

        output.append(
            {
                **row,
                "label_crop_url": copy_asset(label_path, prefix, "label", assets_dir, page_dir),
                "center_crop_url": copy_asset(center_path, prefix, "center", assets_dir, page_dir),
                "full_crop_url": copy_asset(full_path, prefix, "full", assets_dir, page_dir),
            }
        )
    return output


def build_page(queue_csv: Path, rows: List[Dict[str, str]]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    rows_json = json.dumps(rows, ensure_ascii=True)
    total = len(rows)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>SW1 Ground Truth Reviewer</title>
  <style>
    :root {{ --bg:#f3efe6; --card:#fffdf7; --ink:#1f2b29; --line:#d8d1c2; --blue:#35597f; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:\"Avenir Next\",\"Trebuchet MS\",sans-serif; background:var(--bg); color:var(--ink); }}
    .wrap {{ max-width:1450px; margin:0 auto; padding:14px; }}
    .hero {{ border:1px solid var(--line); border-radius:12px; background:var(--card); padding:12px; margin-bottom:10px; }}
    .toolbar {{ position:sticky; top:8px; z-index:10; border:1px solid var(--line); border-radius:12px; background:var(--card); padding:10px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:10px; }}
    .toolbar select,.toolbar input,.toolbar button {{ border:1px solid #d4cdbd; border-radius:8px; background:#fffef9; padding:6px 10px; font:inherit; }}
    .toolbar .primary {{ background:var(--blue); color:#fff; border-color:var(--blue); font-weight:700; }}
    .stats {{ margin-left:auto; font-size:.84rem; color:#4e5e58; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:10px; }}
    .card {{ border:1px solid var(--line); border-radius:12px; background:var(--card); overflow:hidden; }}
    .head {{ padding:8px 10px; border-bottom:1px solid #e7decd; background:#f6f1e5; }}
    .head p,.meta p {{ margin:3px 0; font-size:.8rem; }}
    .imgs {{ display:grid; grid-template-columns:repeat(3,1fr); gap:4px; background:#ece4d3; padding:4px; }}
    .imgs img {{ width:100%; aspect-ratio:4/3; object-fit:cover; display:block; border-radius:6px; border:1px solid #d8d0c1; }}
    .missing {{ min-height:90px; display:grid; place-items:center; color:#6d7a74; font-size:.76rem; border:1px dashed #cdbfa9; border-radius:6px; background:#f8f4e9; }}
    .meta {{ padding:8px 10px; border-top:1px solid #ece4d3; border-bottom:1px solid #ece4d3; }}
    .form {{ padding:8px 10px 10px; display:grid; gap:6px; }}
    label {{ display:grid; gap:3px; font-size:.78rem; color:#4e5e58; }}
    input,select,textarea {{ border:1px solid #d4cdbd; border-radius:7px; padding:6px 8px; background:#fffef9; font:inherit; color:var(--ink); }}
    textarea {{ min-height:52px; resize:vertical; }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <section class=\"hero\">
      <h1>SW-1 Weak-Run Ground Truth Reviewer</h1>
      <p>Source template: <code>{esc(str(queue_csv))}</code></p>
      <p>Total rows: <strong>{total}</strong></p>
      <p>Generated (UTC): <code>{esc(generated)}</code></p>
    </section>

    <section class=\"toolbar\">
      <label>Run Date
        <select id=\"run-filter\"><option value=\"all\">All</option></select>
      </label>
      <label>Review Status
        <select id=\"status-filter\">
          <option value=\"all\">All</option>
          <option value=\"reviewed\">Reviewed</option>
          <option value=\"pending\">Pending</option>
        </select>
      </label>
      <label>Reviewer<input id=\"reviewer-name\" placeholder=\"your initials\" /></label>
      <button class=\"primary\" id=\"export-btn\">Export Reviewed Ground Truth CSV</button>
      <button id=\"reset-btn\">Reset Local Edits</button>
      <span class=\"stats\" id=\"stats\"></span>
    </section>

    <section class=\"grid\" id=\"grid\"></section>
  </main>

<script>
(() => {{
  const STORAGE_KEY = "sw1_ground_truth_reviewer_v1";
  const rows = {rows_json};
  const grid = document.getElementById("grid");
  const stats = document.getElementById("stats");
  const runFilter = document.getElementById("run-filter");
  const statusFilter = document.getElementById("status-filter");
  const reviewerName = document.getElementById("reviewer-name");
  const exportBtn = document.getElementById("export-btn");
  const resetBtn = document.getElementById("reset-btn");

  const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}") || {{}};
  rows.forEach((row, i) => {{
    row._id = `row-${{i + 1}}`;
    if (!state[row._id]) state[row._id] = {{ ...row }};
  }});

  function csvValue(v) {{
    const text = v == null ? "" : String(v);
    if (text.includes(",") || text.includes('"') || text.includes("\\n")) return `"${{text.replaceAll('"', '""')}}"`;
    return text;
  }}

  function render() {{
    const runValue = runFilter.value || "all";
    const statusValue = statusFilter.value || "all";
    const reviewer = (reviewerName.value || "").trim();
    grid.innerHTML = "";
    let visible = 0;
    let reviewed = 0;

    rows.forEach((row) => {{
      const s = state[row._id];
      const isReviewed = !!((s.true_pot_id || "").trim() || (s.truth_source || "").trim());
      if (statusValue === "reviewed" && !isReviewed) return;
      if (statusValue === "pending" && isReviewed) return;
      if (runValue !== "all" && row.run_date !== runValue) return;

      visible += 1;
      if (isReviewed) reviewed += 1;

      const card = document.createElement("article");
      card.className = "card";
      card.innerHTML = `
        <header class='head'>
          <p><strong>${{row.run_date}} row=${{row.row_index}}</strong> | pred_pot=<strong>${{row.predicted_pot_id}}</strong></p>
          <p>asset=${{row.source_asset_id}}</p>
        </header>
        <div class='imgs'>
          ${{row.label_crop_url ? `<img src='${{row.label_crop_url}}' alt='label crop' />` : `<div class='missing'>No label crop</div>`}}
          ${{row.center_crop_url ? `<img src='${{row.center_crop_url}}' alt='center crop' />` : `<div class='missing'>No center crop</div>`}}
          ${{row.full_crop_url ? `<img src='${{row.full_crop_url}}' alt='full crop' />` : `<div class='missing'>No full crop</div>`}}
        </div>
        <div class='meta'>
          <p>predicted_pot=${{row.predicted_pot_id}} | ocr_matches=${{row.ocr_match_variants}} | ocr_numbers=${{row.ocr_numbers_detected || "-"}}</p>
        </div>
        <div class='form'>
          <label>True Pot ID (e.g. 8T)<input data-id='${{row._id}}' data-field='true_pot_id' value='${{(s.true_pot_id || "").replaceAll("'","&#39;")}}' /></label>
          <label>True Variety Name<input data-id='${{row._id}}' data-field='true_variety_name' value='${{(s.true_variety_name || "").replaceAll("'","&#39;")}}' /></label>
          <label>Truth Source
            <select data-id='${{row._id}}' data-field='truth_source'>
              <option value=''>-- select --</option>
              <option value='label_visible'>label_visible</option>
              <option value='context_memory'>context_memory</option>
              <option value='cannot_verify'>cannot_verify</option>
              <option value='other'>other</option>
            </select>
          </label>
          <label>Truth Note<textarea data-id='${{row._id}}' data-field='truth_note'>${{s.truth_note || ""}}</textarea></label>
          <label>Reviewer<input data-id='${{row._id}}' data-field='reviewer' value='${{(s.reviewer || reviewer || "").replaceAll("'","&#39;")}}' /></label>
          <label>Reviewed At (ISO UTC)<input data-id='${{row._id}}' data-field='reviewed_at' value='${{(s.reviewed_at || "").replaceAll("'","&#39;")}}' /></label>
        </div>`;
      grid.appendChild(card);
    }});

    document.querySelectorAll("[data-id][data-field]").forEach((el) => {{
      const id = el.getAttribute("data-id");
      const field = el.getAttribute("data-field");
      if (!id || !field) return;
      if (el.tagName === "SELECT") el.value = state[id][field] || "";
      el.addEventListener("input", () => {{
        state[id][field] = el.value;
        if (field === "true_pot_id" || field === "truth_source" || field === "truth_note") {{
          state[id].reviewed_at = new Date().toISOString();
          if (!state[id].reviewer && reviewerName.value) state[id].reviewer = reviewerName.value.trim();
        }}
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }});
      if (el.tagName === "SELECT") el.addEventListener("change", () => {{
        state[id][field] = el.value;
        state[id].reviewed_at = new Date().toISOString();
        if (!state[id].reviewer && reviewerName.value) state[id].reviewer = reviewerName.value.trim();
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }});
    }});

    stats.textContent = `Visible: ${{visible}} / ${{rows.length}} | Reviewed visible: ${{reviewed}}`;
  }}

  function exportCsv() {{
    const nowIso = new Date().toISOString();
    const output = rows.map((row) => {{
      const s = state[row._id] || {{}};
      const merged = {{}};
      const fields = {json.dumps(TEMPLATE_FIELDS)};
      fields.forEach((field) => merged[field] = s[field] || row[field] || "");
      if (!merged.reviewed_at && (merged.true_pot_id || merged.truth_source || merged.truth_note)) merged.reviewed_at = nowIso;
      if (!merged.reviewer && reviewerName.value) merged.reviewer = reviewerName.value.trim();
      return merged;
    }});

    const headers = {json.dumps(TEMPLATE_FIELDS)};
    const lines = [headers.join(",")];
    output.forEach((row) => lines.push(headers.map((h) => csvValue(row[h] || "")).join(",")));
    const blob = new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `sw1_ground_truth_reviewed_${{new Date().toISOString().replaceAll(":", "-")}}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  }}

  function initFilters() {{
    const runDates = Array.from(new Set(rows.map((row) => row.run_date))).sort();
    runDates.forEach((runDate) => {{
      const option = document.createElement("option");
      option.value = runDate;
      option.textContent = runDate;
      runFilter.appendChild(option);
    }});
    runFilter.addEventListener("change", render);
    statusFilter.addEventListener("change", render);
    reviewerName.addEventListener("input", () => {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }});
  }}

  exportBtn.addEventListener("click", exportCsv);
  resetBtn.addEventListener("click", () => {{
    if (!confirm("Reset all local edits for this reviewer page?")) return;
    localStorage.removeItem(STORAGE_KEY);
    location.reload();
  }});
  initFilters();
  render();
}})();
</script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build SW-1 weak-run ground-truth reviewer page."
    )
    parser.add_argument(
        "--template-csv",
        type=Path,
        default=Path("data/research/v1_7/sw1_weak_run_ground_truth_template.csv"),
        help="Input SW-1 weak-run truth template CSV.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("tracker/assets/sw1-ground-truth"),
        help="Asset output directory for copied review crops.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/sw1-ground-truth-reviewer.html"),
        help="Output HTML reviewer page path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.template_csv)
    page_dir = args.output_html.parent
    prepared = prepare_rows(rows, args.assets_dir, page_dir)
    html = build_page(args.template_csv, prepared)

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    print(f"template_csv={args.template_csv}")
    print(f"rows={len(prepared)}")
    print(f"assets_dir={args.assets_dir}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
