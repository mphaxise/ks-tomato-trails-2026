#!/usr/bin/env python3
"""Build a one-photo-at-a-time manual tagger for two photo runs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import build_tomato_pot_mapping as pot_mapping
from stable_generated_output import stabilize_rendered_text, write_text_if_changed


def esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def parse_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return 0


def derive_latest_run_date(rows: List[Dict[str, str]]) -> str:
    dates = sorted(
        {
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        }
    )
    if not dates:
        raise ValueError("No capture_date values found in input CSV")
    return dates[-1]


def phase_label_for_run(
    run_date: str,
    lifecycle_stage: str,
    phase_timeline: List[Dict[str, str]],
) -> Tuple[str, str]:
    context = pot_mapping.resolve_phase_context(run_date, lifecycle_stage, phase_timeline)
    return (context.get("phase_name", ""), context.get("phase_day_label", ""))


def mapping_for_run(
    rows: List[Dict[str, str]],
    run_date: str,
    expected_pots: int,
    potting_date: str,
    day_one_photo_date: str,
    lifecycle_stage: str,
    assume_sequential_pot_ids: bool,
    tomato_only_run: bool,
    series_variety_map: Dict[int, str],
    pot_series_overrides: Dict[str, int],
    baseline_variety_map: Dict[str, str],
    baseline_reconcile: bool,
    context_id: str,
) -> Tuple[List[Dict[str, str]], Dict[str, object]]:
    mapping_rows, report = pot_mapping.build_mapping(
        rows,
        run_date,
        expected_pots,
        potting_date,
        day_one_photo_date,
        lifecycle_stage,
        assume_sequential_pot_ids,
        tomato_only_run,
        series_variety_map,
        pot_series_overrides,
        baseline_variety_map,
        baseline_reconcile,
        context_id,
    )
    mapping_rows.sort(
        key=lambda row: (
            parse_int((row.get("row_index", "") or "0")),
            (row.get("source_asset_id", "") or "").strip(),
        )
    )
    return mapping_rows, report


def ensure_count(
    rows: List[Dict[str, str]], run_date: str, expected_count: int
) -> List[Dict[str, str]]:
    if len(rows) < expected_count:
        raise ValueError(
            f"run_date={run_date}: found {len(rows)} rows, expected {expected_count}"
        )
    if len(rows) > expected_count:
        rows = rows[:expected_count]
    return rows


def local_image_src(
    row: Dict[str, str],
    image_dir: Path,
    output_parent: Path,
) -> str:
    row_index = parse_int((row.get("row_index", "") or "").strip())
    source_asset_id = (row.get("source_asset_id", "") or "").strip()
    if row_index <= 0 or not source_asset_id:
        return ""
    image_path = image_dir / f"{row_index:02d}_{source_asset_id}.jpg"
    if not image_path.exists():
        return ""
    relative = Path(os.path.relpath(image_path, output_parent)).as_posix()
    if not relative.startswith("."):
        relative = f"./{relative}"
    return relative


def build_photos_payload(
    run_a_rows: List[Dict[str, str]],
    run_b_rows: List[Dict[str, str]],
    image_dir: Path,
    output_parent: Path,
) -> List[Dict[str, str]]:
    photos: List[Dict[str, str]] = []
    for row in run_a_rows + run_b_rows:
        run_date = (row.get("run_date", "") or row.get("capture_date", "") or "").strip()
        row_index = (row.get("row_index", "") or "").strip()
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        key = f"{run_date}::{row_index}::{source_asset_id}"
        photos.append(
            {
                "key": key,
                "run_date": run_date,
                "row_index": row_index,
                "source_asset_id": source_asset_id,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "local_image_src": local_image_src(row, image_dir, output_parent),
                "suggested_pot_id": (row.get("pot_id", "") or "").strip(),
                "suggested_varietal_id": (row.get("packet_number", "") or "").strip(),
                "suggested_variety_name": (row.get("variety_name", "") or "").strip(),
            }
        )
    return photos


def build_page(
    photos: List[Dict[str, str]],
    run_a_date: str,
    run_b_date: str,
    run_a_day_label: str,
    run_b_day_label: str,
    phase_name: str,
    per_run_count: int,
    generated_at: str,
) -> str:
    photos_json = json.dumps(photos, ensure_ascii=True)
    title = "Two-Run Manual Pot/Varietal Tagger"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg: #f2eee4;
      --card: #fffdf8;
      --line: #d9d0be;
      --ink: #1f2a2a;
      --brand: #1f5a7a;
      --ok: #2d6a4f;
      --warn: #915c1f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: \"Avenir Next\", \"Trebuchet MS\", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(950px 450px at 110% -10%, #ded4be 0%, transparent 65%),
        radial-gradient(900px 420px at -10% 110%, #e7dbc2 0%, transparent 65%),
        linear-gradient(145deg, #f4efe3, #ece4d4);
    }}
    .wrap {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 14px;
      display: grid;
      gap: 10px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-family: \"Iowan Old Style\", \"Palatino Linotype\", serif;
      font-size: clamp(1.2rem, 3vw, 1.9rem);
    }}
    .small {{ font-size: 0.82rem; color: #51615d; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }}
    .chip {{
      border: 1px solid #d8cdb7;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 0.79rem;
      background: #fffef8;
    }}
    .toolbar {{
      position: sticky;
      top: 8px;
      z-index: 8;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    button {{
      border: 1px solid #d4c9b2;
      border-radius: 8px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 7px 10px;
    }}
    .primary {{ background: var(--brand); color: #fff; border-color: var(--brand); font-weight: 700; }}
    .good {{ background: var(--ok); color: #fff; border-color: var(--ok); font-weight: 700; }}
    .warn {{ background: var(--warn); color: #fff; border-color: var(--warn); font-weight: 700; }}
    .status {{ margin-left: auto; font-size: 0.84rem; color: #4d5d58; }}
    .work {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 10px;
      align-items: start;
    }}
    .image-wrap {{
      border: 1px solid #ddd4c3;
      border-radius: 10px;
      overflow: hidden;
      background: #f0e9d8;
      min-height: 380px;
      display: grid;
      place-items: center;
    }}
    .image-wrap img {{
      width: 100%;
      max-height: 76vh;
      object-fit: contain;
      display: block;
      background: #efe8d7;
    }}
    .image-missing {{
      padding: 16px;
      color: #5e6d69;
      font-size: 0.9rem;
      text-align: center;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 8px;
      font-size: 0.82rem;
      color: #4d5e59;
    }}
    .meta-grid .meta {{
      border: 1px solid #e5dccb;
      border-radius: 8px;
      padding: 6px 8px;
      background: #faf6ec;
    }}
    label {{
      display: grid;
      gap: 4px;
      font-size: 0.82rem;
      color: #4f5f5a;
      margin-bottom: 8px;
    }}
    input, textarea {{
      border: 1px solid #d8cebc;
      border-radius: 8px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 8px 9px;
      width: 100%;
    }}
    textarea {{ min-height: 84px; resize: vertical; }}
    .read-only {{ background: #f6f1e4; color: #5d6d68; }}
    .field-help {{ font-size: 0.74rem; color: #63726e; margin-top: -4px; margin-bottom: 8px; }}
    .footer-note {{ font-size: 0.78rem; color: #5d6d68; }}
    @media (max-width: 980px) {{
      .work {{ grid-template-columns: 1fr; }}
      .status {{ width: 100%; margin-left: 0; }}
      .meta-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <section class=\"card\">
      <h1>{esc(title)}</h1>
      <p class=\"small\">Manual queue for two runs: <strong>{esc(run_a_date)}</strong> and <strong>{esc(run_b_date)}</strong> ({per_run_count} each).</p>
      <p class=\"small\"><strong>{esc(phase_name or "Phase lock")}</strong>: {esc(run_a_day_label or "Run A")} and {esc(run_b_day_label or "Run B")} anchors.</p>
      <p class=\"small\">Generated (UTC): <code>{esc(generated_at)}</code></p>
      <div class=\"chips\">
        <span class=\"chip\">Run A: {esc(run_a_date)} ({esc(run_a_day_label or "Anchor A")}) x {per_run_count}</span>
        <span class=\"chip\">Run B: {esc(run_b_date)} ({esc(run_b_day_label or "Anchor B")}) x {per_run_count}</span>
        <span class=\"chip\">Total photos: {len(photos)}</span>
      </div>
    </section>

    <section class=\"card toolbar\">
      <button id=\"prev-btn\">Previous</button>
      <button id=\"next-btn\">Next</button>
      <button class=\"good\" id=\"mark-reviewed\">Mark Reviewed + Next</button>
      <button id=\"jump-pending\">Jump To Next Pending</button>
      <button class=\"primary\" id=\"export-csv\">Export CSV (all photos)</button>
      <button id=\"export-json\">Export JSON</button>
      <button class=\"warn\" id=\"reset-local\">Reset Local</button>
      <span class=\"status\" id=\"status-line\">Loading...</span>
    </section>

    <section class=\"work\">
      <article class=\"card\">
        <div class=\"image-wrap\" id=\"image-wrap\">
          <img id=\"photo-image\" alt=\"photo\" />
        </div>
        <div class=\"meta-grid\">
          <div class=\"meta\" id=\"meta-progress\"></div>
          <div class=\"meta\" id=\"meta-run\"></div>
          <div class=\"meta\" id=\"meta-row\"></div>
          <div class=\"meta\" id=\"meta-asset\"></div>
        </div>
        <p class=\"small\">Photo URL: <a id=\"photo-url-link\" href=\"#\" target=\"_blank\" rel=\"noreferrer\">Open original</a></p>
      </article>

      <article class=\"card\">
        <h2 style=\"margin-top:0;\">Manual Tags</h2>
        <label>
          Pot ID
          <input id=\"pot-id-input\" type=\"text\" placeholder=\"Example: 12T\" />
        </label>
        <p class=\"field-help\">Prefilled from current mapping; edit if incorrect.</p>

        <label>
          Varietal ID
          <input id=\"varietal-id-input\" type=\"text\" placeholder=\"Example: 7\" />
        </label>
        <p class=\"field-help\">This is the packet/series number used as varietal ID.</p>

        <label>
          Suggested Variety Name (read-only)
          <input id=\"variety-name-input\" class=\"read-only\" type=\"text\" readonly />
        </label>

        <label>
          Notes (optional)
          <textarea id=\"notes-input\" placeholder=\"Optional note for this photo.\"></textarea>
        </label>

        <label style=\"display:flex;align-items:center;gap:8px;margin-top:10px;\">
          <input id=\"reviewed-input\" type=\"checkbox\" style=\"width:16px;height:16px;margin:0;\" />
          <span>Reviewed</span>
        </label>

        <p class=\"footer-note\">Arrow keys: left/right to navigate photos.</p>
      </article>
    </section>
  </main>

  <script>
    (() => {{
      const PHOTOS = {photos_json};
      const STORAGE_KEY = `manual_two_run_tagger_v1::${{(PHOTOS[0] && PHOTOS[0].run_date) || ""}}::${{(PHOTOS[PHOTOS.length - 1] && PHOTOS[PHOTOS.length - 1].run_date) || ""}}`;

      const prevBtn = document.getElementById("prev-btn");
      const nextBtn = document.getElementById("next-btn");
      const markReviewedBtn = document.getElementById("mark-reviewed");
      const jumpPendingBtn = document.getElementById("jump-pending");
      const exportCsvBtn = document.getElementById("export-csv");
      const exportJsonBtn = document.getElementById("export-json");
      const resetLocalBtn = document.getElementById("reset-local");
      const statusLine = document.getElementById("status-line");

      const imageWrap = document.getElementById("image-wrap");
      const photoImage = document.getElementById("photo-image");
      const metaProgress = document.getElementById("meta-progress");
      const metaRun = document.getElementById("meta-run");
      const metaRow = document.getElementById("meta-row");
      const metaAsset = document.getElementById("meta-asset");
      const photoUrlLink = document.getElementById("photo-url-link");

      const potIdInput = document.getElementById("pot-id-input");
      const varietalIdInput = document.getElementById("varietal-id-input");
      const varietyNameInput = document.getElementById("variety-name-input");
      const notesInput = document.getElementById("notes-input");
      const reviewedInput = document.getElementById("reviewed-input");

      const state = {{
        currentIndex: 0,
        edits: {{}}
      }};

      function asBool(value) {{
        return value === true || value === "true" || value === 1 || value === "1";
      }}

      function nowIso() {{
        return new Date().toISOString();
      }}

      function defaultEdit(photo) {{
        return {{
          pot_id: photo.suggested_pot_id || "",
          varietal_id: photo.suggested_varietal_id || "",
          notes: "",
          reviewed: false,
          last_edited_at: ""
        }};
      }}

      function getEdit(photo) {{
        if (!state.edits[photo.key]) {{
          state.edits[photo.key] = defaultEdit(photo);
        }}
        return state.edits[photo.key];
      }}

      function saveLocal() {{
        const payload = {{
          current_index: state.currentIndex,
          edits: state.edits,
          saved_at_utc: nowIso(),
          version: "manual-two-run-tagger-v1"
        }};
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      }}

      function loadLocal() {{
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        try {{
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {{
            if (parsed.edits && typeof parsed.edits === "object") {{
              Object.keys(parsed.edits).forEach((key) => {{
                state.edits[key] = parsed.edits[key];
              }});
            }}
            const idx = Number(parsed.current_index || 0);
            if (Number.isFinite(idx) && idx >= 0 && idx < PHOTOS.length) {{
              state.currentIndex = idx;
            }}
          }}
        }} catch (err) {{
          console.warn("Could not parse local tagger state", err);
        }}
      }}

      function escapeCsv(text) {{
        const value = text == null ? "" : String(text);
        if (value.includes(",") || value.includes('"') || value.includes("\\n")) {{
          return '"' + value.replaceAll('"', '""') + '"';
        }}
        return value;
      }}

      function refreshStatusLine() {{
        let reviewed = 0;
        PHOTOS.forEach((photo) => {{
          const edit = getEdit(photo);
          if (asBool(edit.reviewed)) reviewed += 1;
        }});
        const pending = PHOTOS.length - reviewed;
        statusLine.textContent = `Photo ${{state.currentIndex + 1}} / ${{PHOTOS.length}} | Reviewed: ${{reviewed}} | Pending: ${{pending}}`;
      }}

      function renderImage(photo) {{
        const source = (photo.local_image_src || "").trim() || (photo.photo_url || "").trim();
        if (!source) {{
          photoImage.style.display = "none";
          imageWrap.innerHTML = '<div class="image-missing">No image source available for this row.</div>';
          return;
        }}

        if (!imageWrap.contains(photoImage)) {{
          imageWrap.innerHTML = "";
          imageWrap.appendChild(photoImage);
        }}
        photoImage.style.display = "block";
        photoImage.src = source;
        photoImage.alt = `${{photo.run_date}} row ${{photo.row_index}}`;
      }}

      function render() {{
        if (!Array.isArray(PHOTOS) || PHOTOS.length === 0) {{
          statusLine.textContent = "No photos available.";
          return;
        }}

        const photo = PHOTOS[state.currentIndex];
        const edit = getEdit(photo);

        renderImage(photo);

        metaProgress.textContent = `Queue: ${{state.currentIndex + 1}} / ${{PHOTOS.length}}`;
        metaRun.textContent = `Run: ${{photo.run_date}}`;
        metaRow.textContent = `Row Index: ${{photo.row_index}}`;
        metaAsset.textContent = `Asset: ${{photo.source_asset_id}}`;

        if (photo.photo_url) {{
          photoUrlLink.href = photo.photo_url;
          photoUrlLink.textContent = "Open original";
        }} else {{
          photoUrlLink.href = "#";
          photoUrlLink.textContent = "No original URL";
        }}

        potIdInput.value = edit.pot_id || "";
        varietalIdInput.value = edit.varietal_id || "";
        notesInput.value = edit.notes || "";
        reviewedInput.checked = asBool(edit.reviewed);
        varietyNameInput.value = photo.suggested_variety_name || "";

        prevBtn.disabled = state.currentIndex <= 0;
        nextBtn.disabled = state.currentIndex >= PHOTOS.length - 1;

        refreshStatusLine();
      }}

      function persistFromInputs() {{
        const photo = PHOTOS[state.currentIndex];
        const edit = getEdit(photo);
        edit.pot_id = (potIdInput.value || "").trim();
        edit.varietal_id = (varietalIdInput.value || "").trim();
        edit.notes = (notesInput.value || "").trim();
        edit.reviewed = Boolean(reviewedInput.checked);
        edit.last_edited_at = nowIso();
        saveLocal();
        refreshStatusLine();
      }}

      function navigate(nextIndex) {{
        persistFromInputs();
        if (nextIndex < 0 || nextIndex >= PHOTOS.length) return;
        state.currentIndex = nextIndex;
        saveLocal();
        render();
      }}

      function jumpToNextPending() {{
        persistFromInputs();
        for (let i = 0; i < PHOTOS.length; i += 1) {{
          const idx = (state.currentIndex + 1 + i) % PHOTOS.length;
          const edit = getEdit(PHOTOS[idx]);
          if (!asBool(edit.reviewed)) {{
            state.currentIndex = idx;
            saveLocal();
            render();
            return;
          }}
        }}
      }}

      function buildExportRows() {{
        return PHOTOS.map((photo, index) => {{
          const edit = getEdit(photo);
          return {{
            queue_position: String(index + 1),
            run_date: photo.run_date || "",
            row_index: photo.row_index || "",
            source_asset_id: photo.source_asset_id || "",
            photo_url: photo.photo_url || "",
            local_image_src: photo.local_image_src || "",
            suggested_pot_id: photo.suggested_pot_id || "",
            suggested_varietal_id: photo.suggested_varietal_id || "",
            suggested_variety_name: photo.suggested_variety_name || "",
            confirmed_pot_id: edit.pot_id || "",
            confirmed_varietal_id: edit.varietal_id || "",
            reviewed: asBool(edit.reviewed) ? "1" : "0",
            notes: edit.notes || "",
            last_edited_at: edit.last_edited_at || ""
          }};
        }});
      }}

      function download(filename, mimeType, text) {{
        const blob = new Blob([text], {{ type: mimeType }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }}

      function exportCsv() {{
        persistFromInputs();
        const rows = buildExportRows();
        if (!rows.length) return;
        const headers = Object.keys(rows[0]);
        const lines = [headers.join(",")];
        rows.forEach((row) => {{
          lines.push(headers.map((h) => escapeCsv(row[h])).join(","));
        }});
        const now = nowIso().replaceAll(":", "-");
        download(`manual_two_run_tags_${{now}}.csv`, "text/csv;charset=utf-8", lines.join("\\n") + "\\n");
      }}

      function exportJson() {{
        persistFromInputs();
        const payload = {{
          version: "manual-two-run-tagger-v1",
          exported_at_utc: nowIso(),
          total_photos: PHOTOS.length,
          photos: buildExportRows()
        }};
        const now = nowIso().replaceAll(":", "-");
        download(
          `manual_two_run_tags_${{now}}.json`,
          "application/json;charset=utf-8",
          JSON.stringify(payload, null, 2)
        );
      }}

      function resetLocal() {{
        const confirmed = window.confirm("Reset all local edits for this page?");
        if (!confirmed) return;
        localStorage.removeItem(STORAGE_KEY);
        state.currentIndex = 0;
        state.edits = {{}};
        render();
      }}

      prevBtn.addEventListener("click", () => navigate(state.currentIndex - 1));
      nextBtn.addEventListener("click", () => navigate(state.currentIndex + 1));
      markReviewedBtn.addEventListener("click", () => {{
        reviewedInput.checked = true;
        persistFromInputs();
        if (state.currentIndex < PHOTOS.length - 1) {{
          navigate(state.currentIndex + 1);
        }} else {{
          render();
        }}
      }});
      jumpPendingBtn.addEventListener("click", jumpToNextPending);
      exportCsvBtn.addEventListener("click", exportCsv);
      exportJsonBtn.addEventListener("click", exportJson);
      resetLocalBtn.addEventListener("click", resetLocal);

      [potIdInput, varietalIdInput, notesInput].forEach((el) => {{
        el.addEventListener("input", persistFromInputs);
      }});
      reviewedInput.addEventListener("change", persistFromInputs);

      document.addEventListener("keydown", (event) => {{
        const tag = (document.activeElement && document.activeElement.tagName) || "";
        const editingField = tag === "INPUT" || tag === "TEXTAREA";
        if (editingField) return;
        if (event.key === "ArrowLeft") {{
          event.preventDefault();
          navigate(state.currentIndex - 1);
        }} else if (event.key === "ArrowRight") {{
          event.preventDefault();
          navigate(state.currentIndex + 1);
        }}
      }});

      if (!Array.isArray(PHOTOS) || PHOTOS.length === 0) {{
        statusLine.textContent = "No photos to review.";
        return;
      }}

      loadLocal();
      render();
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one-photo-at-a-time manual tagger page for two runs."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Input mixed labeled CSV.",
    )
    parser.add_argument(
        "--run-a-date",
        default="2026-02-27",
        help="First run date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--run-b-date",
        default="",
        help="Second run date (YYYY-MM-DD). Defaults to latest run in input CSV.",
    )
    parser.add_argument(
        "--per-run-count",
        type=int,
        default=32,
        help="Photos to include per run (default: 32).",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Local image directory.",
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
        help="Pot-level series overrides CSV.",
    )
    parser.add_argument(
        "--baseline-map-csv",
        type=Path,
        default=Path(
            "releases/v1.4-2026-02-28/data/intake/processed/tomato_pot_mapping_latest.csv"
        ),
        help="Baseline mapping CSV used by mapping resolver.",
    )
    parser.add_argument(
        "--expected-pots",
        type=int,
        default=32,
        help="Expected unique pots for each run.",
    )
    parser.add_argument(
        "--potting-date",
        default="2026-02-24",
        help="Potting date for day calculations.",
    )
    parser.add_argument(
        "--day-one-photo-date",
        default="2026-02-25",
        help="Day-one photo date for experiment day calculations.",
    )
    parser.add_argument(
        "--lifecycle-stage",
        default="sapling",
        help="Lifecycle stage label.",
    )
    parser.add_argument(
        "--baseline-reconcile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reconcile against baseline mapping.",
    )
    parser.add_argument(
        "--assume-sequential-pot-ids",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Infer missing pot IDs from row sequence.",
    )
    parser.add_argument(
        "--tomato-only-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat selected run rows as tomato-only.",
    )
    parser.add_argument(
        "--context-id",
        default="context_default",
        help="Mapping context id.",
    )
    parser.add_argument(
        "--phase-timeline-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_phase_timeline.csv"),
        help="Phase timeline CSV used for anchor labels.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/manual-two-run-tagger.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = pot_mapping.read_rows(args.input_csv)
    latest_run_date = derive_latest_run_date(rows)
    run_a_date = (args.run_a_date or "").strip()
    run_b_date = (args.run_b_date or latest_run_date).strip() or latest_run_date
    phase_timeline = pot_mapping.load_phase_timeline(args.phase_timeline_csv)

    series_variety_map = pot_mapping.load_series_variety_map(args.series_map_csv)
    pot_series_overrides = pot_mapping.load_pot_series_overrides(args.pot_series_overrides_csv)
    baseline_variety_map = pot_mapping.load_baseline_variety_map(args.baseline_map_csv)

    run_a_mapping, run_a_report = mapping_for_run(
        rows,
        run_a_date,
        args.expected_pots,
        args.potting_date,
        args.day_one_photo_date,
        args.lifecycle_stage,
        args.assume_sequential_pot_ids,
        args.tomato_only_run,
        series_variety_map,
        pot_series_overrides,
        baseline_variety_map,
        args.baseline_reconcile,
        args.context_id,
    )
    run_b_mapping, run_b_report = mapping_for_run(
        rows,
        run_b_date,
        args.expected_pots,
        args.potting_date,
        args.day_one_photo_date,
        args.lifecycle_stage,
        args.assume_sequential_pot_ids,
        args.tomato_only_run,
        series_variety_map,
        pot_series_overrides,
        baseline_variety_map,
        args.baseline_reconcile,
        args.context_id,
    )

    run_a_selected = ensure_count(run_a_mapping, run_a_date, args.per_run_count)
    run_b_selected = ensure_count(run_b_mapping, run_b_date, args.per_run_count)

    photos = build_photos_payload(
        run_a_selected,
        run_b_selected,
        args.image_dir,
        args.output_html.parent,
    )
    run_a_phase_name, run_a_day_label = phase_label_for_run(
        run_a_date, args.lifecycle_stage, phase_timeline
    )
    run_b_phase_name, run_b_day_label = phase_label_for_run(
        run_b_date, args.lifecycle_stage, phase_timeline
    )
    phase_name = run_b_phase_name or run_a_phase_name
    page = build_page(
        photos,
        run_a_date,
        run_b_date,
        run_a_day_label,
        run_b_day_label,
        phase_name,
        args.per_run_count,
        "__GENERATED_AT__",
    )

    page = stabilize_rendered_text(args.output_html, page)
    write_text_if_changed(args.output_html, page)

    print(f"input_csv={args.input_csv}")
    print(f"run_a_date={run_a_date} rows={len(run_a_selected)} report_selected={run_a_report.get('selected_rows', 0)}")
    print(f"run_b_date={run_b_date} rows={len(run_b_selected)} report_selected={run_b_report.get('selected_rows', 0)}")
    print(f"per_run_count={args.per_run_count}")
    print(f"total_photos={len(photos)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
