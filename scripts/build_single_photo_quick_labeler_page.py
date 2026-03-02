#!/usr/bin/env python3
"""Build a minimal one-photo box+description labeler page."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


def esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing CSV header")
        return list(reader)


def pick_latest_image(mixed_csv: Path, image_dir: Path) -> Dict[str, str]:
    rows = read_rows(mixed_csv)
    latest_date = max(
        ((row.get("capture_date", "") or "").strip() for row in rows if (row.get("capture_date", "") or "").strip()),
        default="",
    )
    if not latest_date:
        raise ValueError("No capture_date found in mixed CSV")

    for idx, row in enumerate(rows, start=1):
        if (row.get("capture_date", "") or "").strip() != latest_date:
            continue
        asset = (row.get("source_asset_id", "") or "").strip()
        if not asset:
            continue
        image_path = image_dir / f"{idx:02d}_{asset}.jpg"
        if image_path.exists():
            return {
                "capture_date": latest_date,
                "row_index": str(idx),
                "source_asset_id": asset,
                "image_src": f"../{image_path.as_posix()}",
                "image_file_path": str(image_path),
                "photo_url": (row.get("photo_url", "") or "").strip(),
            }
    raise ValueError(f"No local image found for latest capture_date={latest_date}")


def copy_default_image_for_tracker(
    defaults: Dict[str, str], output_html: Path
) -> Dict[str, str]:
    source = Path((defaults.get("image_file_path", "") or "").strip())
    if not source.exists():
        return defaults

    assets_dir = output_html.parent / "assets" / "single-photo-quick-labeler"
    assets_dir.mkdir(parents=True, exist_ok=True)

    capture_date = (defaults.get("capture_date", "") or "").strip().replace("-", "_")
    row_index = (defaults.get("row_index", "") or "").strip()
    source_asset_id = (defaults.get("source_asset_id", "") or "").strip()[:12]
    suffix = source.suffix if source.suffix else ".jpg"
    target_name = f"{capture_date}_{row_index}_{source_asset_id}{suffix}"
    target = assets_dir / target_name
    shutil.copy2(source, target)

    rel = Path(os.path.relpath(target, output_html.parent)).as_posix()
    if not rel.startswith("."):
        rel = f"./{rel}"

    enriched = dict(defaults)
    enriched["image_src"] = rel
    enriched["copied_image_path"] = str(target)
    return enriched


def build_page(defaults: Dict[str, str]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    image_src = esc(defaults.get("image_src", ""))
    capture_date = esc(defaults.get("capture_date", ""))
    source_asset_id = esc(defaults.get("source_asset_id", ""))
    row_index = esc(defaults.get("row_index", ""))
    photo_url = esc(defaults.get("photo_url", ""))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Quick Single Photo Labeler</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
  <style>
    :root {{
      --bg: #f3efe6;
      --card: #fffdf7;
      --line: #d8d1c2;
      --ink: #1f2b29;
      --blue: #35597f;
      --green: #2f6947;
      --amber: #8a5c23;
      --red: #8a2f2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
    }}
    .wrap {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 14px;
      display: grid;
      gap: 10px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
    }}
    .btns {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
    }}
    button {{
      border: 1px solid #d4cdbd;
      border-radius: 8px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 7px 9px;
    }}
    .primary {{ background: var(--blue); color: #fff; border-color: var(--blue); font-weight: 700; }}
    .good {{ background: var(--green); color: #fff; border-color: var(--green); font-weight: 700; }}
    .warn {{ background: var(--amber); color: #fff; border-color: var(--amber); font-weight: 700; }}
    .danger {{ background: var(--red); color: #fff; border-color: var(--red); font-weight: 700; }}
    .work {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 10px;
      align-items: start;
    }}
    .canvas-wrap {{
      border: 1px solid #d8d0c1;
      border-radius: 10px;
      overflow: auto;
      background: #ece4d3;
      min-height: 420px;
      padding: 6px;
    }}
    #canvas {{ display: block; max-width: 100%; border-radius: 8px; background: #f7f2e7; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
    th, td {{ border-bottom: 1px solid #ece4d3; padding: 6px 4px; vertical-align: top; text-align: left; }}
    th {{ background: #f6f1e5; position: sticky; top: 0; z-index: 2; }}
    input {{
      border: 1px solid #d4cdbd;
      border-radius: 7px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 6px 8px;
      width: 100%;
    }}
    .rows-wrap {{ max-height: 700px; overflow: auto; border: 1px solid #ece4d3; border-radius: 8px; }}
    .small {{ font-size: 0.76rem; color: #5b6964; }}
    .status {{ font-size: 0.82rem; color: #4e5e58; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.76rem; }}
    @media (max-width: 980px) {{
      .work {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Quick Single Photo Labeler</h1>
      <p class="small">Preselected from latest run in this branch.</p>
      <p class="small">capture_date=<strong>{capture_date}</strong> | row_index=<strong>{row_index}</strong> | asset=<strong>{source_asset_id}</strong></p>
      <p class="small">Generated (UTC): <code>{generated}</code></p>
      <p class="small">photo_url: <a href="{photo_url}" target="_blank" rel="noreferrer">{photo_url}</a></p>
      <div class="btns">
        <button id="draw-toggle" class="good">Draw Mode: OFF</button>
        <button id="delete-selected" class="danger">Delete Selected</button>
        <button id="clear-all">Clear All Boxes</button>
        <button id="save-local" class="good">Save Local</button>
        <button id="download-json" class="primary">Download JSON (all together)</button>
      </div>
      <p id="status" class="status">Ready.</p>
    </section>

    <section class="work">
      <article class="card">
        <h2 style="margin-top:0;">Image</h2>
        <div class="canvas-wrap">
          <canvas id="canvas" width="1200" height="800"></canvas>
        </div>
        <p class="small">Turn Draw Mode ON, drag to create boxes. Turn OFF to select/move/resize.</p>
      </article>
      <article class="card">
        <h2 style="margin-top:0;">Boxes + Description</h2>
        <div class="rows-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Description</th>
                <th class="mono">Norm (x,y,w,h)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="boxes-body"></tbody>
          </table>
        </div>
      </article>
    </section>
  </main>

  <script>
  (() => {{
    const DEFAULT_IMAGE = "{image_src}";
    const META = {{
      capture_date: "{capture_date}",
      row_index: "{row_index}",
      source_asset_id: "{source_asset_id}",
      photo_url: "{photo_url}"
    }};

    const STORAGE_KEY = `quick_labeler_v1::${{META.capture_date}}::${{META.source_asset_id}}`;
    const drawToggleBtn = document.getElementById("draw-toggle");
    const deleteSelectedBtn = document.getElementById("delete-selected");
    const clearAllBtn = document.getElementById("clear-all");
    const saveLocalBtn = document.getElementById("save-local");
    const downloadJsonBtn = document.getElementById("download-json");
    const statusEl = document.getElementById("status");
    const boxesBody = document.getElementById("boxes-body");

    if (!window.fabric) {{
      statusEl.textContent = "Fabric.js failed to load.";
      return;
    }}

    const state = {{
      imageSrc: DEFAULT_IMAGE,
      naturalWidth: 0,
      naturalHeight: 0,
      displayScale: 1,
      nextId: 1,
      drawMode: false
    }};

    const canvas = new fabric.Canvas("canvas", {{
      preserveObjectStacking: true,
      selection: true
    }});

    let drawRect = null;
    let drawStart = null;

    function setStatus(message) {{
      statusEl.textContent = message;
    }}

    function isAnno(obj) {{
      return obj && obj.type === "rect" && obj.quickAnno === true;
    }}

    function boxes() {{
      return canvas.getObjects().filter(isAnno).sort((a, b) => (a.annoId || 0) - (b.annoId || 0));
    }}

    function normCoords(obj) {{
      const x = (obj.left || 0) / state.displayScale;
      const y = (obj.top || 0) / state.displayScale;
      const w = obj.getScaledWidth() / state.displayScale;
      const h = obj.getScaledHeight() / state.displayScale;
      return {{
        x, y, w, h,
        x_norm: x / state.naturalWidth,
        y_norm: y / state.naturalHeight,
        w_norm: w / state.naturalWidth,
        h_norm: h / state.naturalHeight
      }};
    }}

    function normText(obj) {{
      if (!state.naturalWidth || !state.naturalHeight) return "-";
      const n = normCoords(obj);
      return `${{n.x_norm.toFixed(4)}},${{n.y_norm.toFixed(4)}},${{n.w_norm.toFixed(4)}},${{n.h_norm.toFixed(4)}}`;
    }}

    function makeRect(opts) {{
      return new fabric.Rect({{
        left: opts.left || 0,
        top: opts.top || 0,
        width: opts.width || 1,
        height: opts.height || 1,
        fill: "rgba(43,122,75,0.12)",
        stroke: "#2b7a4b",
        strokeWidth: 2,
        strokeUniform: true,
        transparentCorners: false,
        cornerColor: "#35597f",
        cornerStyle: "circle",
        cornerStrokeColor: "#ffffff",
        objectCaching: false,
        lockRotation: true,
        hasRotatingPoint: false,
        quickAnno: true,
        annoId: opts.annoId || 0,
        annoDescription: opts.annoDescription || ""
      }});
    }}

    function payload() {{
      const outBoxes = boxes().map((b) => {{
        const n = normCoords(b);
        return {{
          id: b.annoId,
          description: b.annoDescription || "",
          x: Number(n.x.toFixed(2)),
          y: Number(n.y.toFixed(2)),
          w: Number(n.w.toFixed(2)),
          h: Number(n.h.toFixed(2)),
          x_norm: Number(n.x_norm.toFixed(6)),
          y_norm: Number(n.y_norm.toFixed(6)),
          w_norm: Number(n.w_norm.toFixed(6)),
          h_norm: Number(n.h_norm.toFixed(6))
        }};
      }});
      return {{
        version: "quick-single-photo-v1",
        saved_at_utc: new Date().toISOString(),
        image_src: state.imageSrc,
        image_width: state.naturalWidth,
        image_height: state.naturalHeight,
        capture_date: META.capture_date,
        row_index: META.row_index,
        source_asset_id: META.source_asset_id,
        photo_url: META.photo_url,
        boxes: outBoxes
      }};
    }}

    function saveLocal() {{
      try {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload()));
      }} catch (err) {{
        setStatus(`Local save failed: ${{err}}`);
        return;
      }}
      setStatus(`Saved locally (${{boxes().length}} boxes).`);
    }}

    function renderTable() {{
      boxesBody.innerHTML = "";
      boxes().forEach((box) => {{
        const tr = document.createElement("tr");
        const desc = (box.annoDescription || "").replaceAll('"', "&quot;");
        tr.innerHTML = `
          <td><strong>#${{box.annoId}}</strong></td>
          <td><input data-id="${{box.annoId}}" data-field="description" value="${{desc}}" /></td>
          <td class="mono">${{normText(box)}}</td>
          <td><button data-id="${{box.annoId}}" data-action="delete">Delete</button></td>
        `;
        boxesBody.appendChild(tr);
      }});

      boxesBody.querySelectorAll("[data-id][data-field='description']").forEach((el) => {{
        el.addEventListener("input", () => {{
          const id = Number(el.getAttribute("data-id"));
          const box = boxes().find((b) => b.annoId === id);
          if (!box) return;
          box.annoDescription = el.value || "";
          saveLocal();
        }});
      }});

      boxesBody.querySelectorAll("[data-id][data-action='delete']").forEach((el) => {{
        el.addEventListener("click", () => {{
          const id = Number(el.getAttribute("data-id"));
          const box = boxes().find((b) => b.annoId === id);
          if (!box) return;
          canvas.remove(box);
          renderTable();
          saveLocal();
          canvas.requestRenderAll();
        }});
      }});
    }}

    function setDrawMode(enabled) {{
      state.drawMode = enabled;
      drawToggleBtn.textContent = `Draw Mode: ${{enabled ? "ON" : "OFF"}}`;
      drawToggleBtn.className = enabled ? "warn" : "good";
      canvas.selection = !enabled;
      canvas.forEachObject((obj) => {{
        if (isAnno(obj)) {{
          obj.selectable = !enabled;
          obj.evented = !enabled;
        }}
      }});
      canvas.requestRenderAll();
    }}

    function clearBoxes() {{
      boxes().forEach((b) => canvas.remove(b));
      state.nextId = 1;
      canvas.discardActiveObject();
      canvas.requestRenderAll();
      renderTable();
      saveLocal();
    }}

    function loadSavedBoxes() {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      try {{
        const obj = JSON.parse(raw);
        if (!obj || !Array.isArray(obj.boxes)) return false;
        clearBoxes();
        obj.boxes.forEach((b, idx) => {{
          const rect = makeRect({{
            left: Number(b.x || 0) * state.displayScale,
            top: Number(b.y || 0) * state.displayScale,
            width: Math.max(2, Number(b.w || 0) * state.displayScale),
            height: Math.max(2, Number(b.h || 0) * state.displayScale),
            annoId: Number(b.id || (idx + 1)),
            annoDescription: b.description || ""
          }});
          canvas.add(rect);
        }});
        const ids = boxes().map((b) => Number(b.annoId || 0));
        state.nextId = ids.length ? Math.max(...ids) + 1 : 1;
        renderTable();
        canvas.requestRenderAll();
        return true;
      }} catch (_err) {{
        return false;
      }}
    }}

    function loadImage() {{
      fabric.Image.fromURL(state.imageSrc, (img) => {{
        if (!img) {{
          setStatus("Failed to load default image.");
          return;
        }}
        canvas.clear();
        const maxW = Math.max(720, Math.min(window.innerWidth - 480, 1160));
        const scale = Math.min(1, maxW / img.width);
        state.displayScale = scale;
        state.naturalWidth = img.width;
        state.naturalHeight = img.height;
        canvas.setWidth(Math.round(img.width * scale));
        canvas.setHeight(Math.round(img.height * scale));
        img.set({{
          left: 0,
          top: 0,
          selectable: false,
          evented: false,
          scaleX: scale,
          scaleY: scale
        }});
        canvas.add(img);
        canvas.sendToBack(img);
        state.nextId = 1;
        const loaded = loadSavedBoxes();
        if (loaded) {{
          setStatus("Loaded latest image with saved local annotations.");
        }} else {{
          renderTable();
          setStatus("Loaded latest image. Start drawing boxes.");
        }}
      }}, {{
        crossOrigin: "anonymous"
      }});
    }}

    function downloadJson() {{
      const out = payload();
      const blob = new Blob([JSON.stringify(out, null, 2)], {{ type: "application/json;charset=utf-8" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `quick_seed_${{META.capture_date}}_${{META.row_index}}_${{new Date().toISOString().replaceAll(":", "-")}}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setStatus("Downloaded JSON.");
    }}

    canvas.on("mouse:down", (opt) => {{
      if (!state.drawMode) return;
      const p = canvas.getPointer(opt.e);
      drawStart = p;
      drawRect = makeRect({{
        left: p.x,
        top: p.y,
        width: 1,
        height: 1,
        annoId: state.nextId,
        annoDescription: ""
      }});
      canvas.add(drawRect);
      canvas.setActiveObject(drawRect);
    }});

    canvas.on("mouse:move", (opt) => {{
      if (!state.drawMode || !drawRect || !drawStart) return;
      const p = canvas.getPointer(opt.e);
      drawRect.set({{
        left: Math.min(drawStart.x, p.x),
        top: Math.min(drawStart.y, p.y),
        width: Math.max(1, Math.abs(p.x - drawStart.x)),
        height: Math.max(1, Math.abs(p.y - drawStart.y))
      }});
      drawRect.setCoords();
      canvas.requestRenderAll();
    }});

    canvas.on("mouse:up", () => {{
      if (!state.drawMode || !drawRect) return;
      if (drawRect.width < 8 || drawRect.height < 8) {{
        canvas.remove(drawRect);
      }} else {{
        drawRect.annoId = state.nextId;
        state.nextId += 1;
      }}
      drawRect = null;
      drawStart = null;
      renderTable();
      saveLocal();
    }});

    canvas.on("object:modified", () => {{
      renderTable();
      saveLocal();
    }});

    drawToggleBtn.addEventListener("click", () => setDrawMode(!state.drawMode));
    deleteSelectedBtn.addEventListener("click", () => {{
      const active = canvas.getActiveObject();
      if (!active || !isAnno(active)) {{
        setStatus("Select a box first.");
        return;
      }}
      canvas.remove(active);
      renderTable();
      saveLocal();
      canvas.requestRenderAll();
    }});
    clearAllBtn.addEventListener("click", () => {{
      clearBoxes();
      setStatus("Cleared all boxes.");
    }});
    saveLocalBtn.addEventListener("click", saveLocal);
    downloadJsonBtn.addEventListener("click", downloadJson);

    setDrawMode(false);
    loadImage();
  }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build minimal one-photo box+description labeler page."
    )
    parser.add_argument(
        "--mixed-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Mixed labeled CSV used to pick latest run image.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Local image directory.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/single-photo-quick-labeler.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    defaults = pick_latest_image(args.mixed_csv, args.image_dir)
    defaults = copy_default_image_for_tracker(defaults, args.output_html)
    html = build_page(defaults)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    print(f"latest_capture_date={defaults['capture_date']}")
    print(f"row_index={defaults['row_index']}")
    print(f"source_asset_id={defaults['source_asset_id']}")
    print(f"default_image={defaults['image_src']}")
    if defaults.get("copied_image_path", ""):
        print(f"copied_image_path={defaults['copied_image_path']}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
