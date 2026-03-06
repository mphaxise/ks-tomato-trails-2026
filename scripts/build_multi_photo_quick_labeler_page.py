#!/usr/bin/env python3
"""Build a stacked multi-photo labeler page with one global save/export."""

from __future__ import annotations

import argparse
import csv
import json
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


def row_index_text(row: Dict[str, str], fallback_index: int) -> str:
    explicit = (row.get("row_index", "") or "").strip()
    if explicit:
        return explicit
    return str(fallback_index)


def pick_latest_images(
    mixed_csv: Path,
    image_dir: Path,
    max_images: int = 0,
) -> List[Dict[str, str]]:
    rows = read_rows(mixed_csv)
    latest_date = max(
        (
            (row.get("capture_date", "") or "").strip()
            for row in rows
            if (row.get("capture_date", "") or "").strip()
        ),
        default="",
    )
    if not latest_date:
        raise ValueError("No capture_date found in mixed CSV")

    selected: List[Dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        if (row.get("capture_date", "") or "").strip() != latest_date:
            continue
        asset = (row.get("source_asset_id", "") or "").strip()
        if not asset:
            continue
        image_path = image_dir / f"{idx:02d}_{asset}.jpg"
        if not image_path.exists():
            continue
        selected.append(
            {
                "capture_date": latest_date,
                "row_index": row_index_text(row, idx),
                "source_asset_id": asset,
                "image_src": f"../{image_path.as_posix()}",
                "photo_url": (row.get("photo_url", "") or "").strip(),
            }
        )

    selected.sort(key=lambda row: int((row.get("row_index", "") or "0")))
    if max_images > 0:
        selected = selected[:max_images]
    if not selected:
        raise ValueError(f"No local images found for latest capture_date={latest_date}")
    return selected


def build_page(photos: List[Dict[str, str]]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    capture_date = photos[0].get("capture_date", "") if photos else ""
    photos_json = json.dumps(photos, ensure_ascii=True)
    capture_date_esc = esc(capture_date)
    count_esc = esc(str(len(photos)))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Quick Multi Photo Labeler</title>
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
      gap: 12px;
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
    .small {{ font-size: 0.78rem; color: #5b6964; }}
    .status {{ font-size: 0.82rem; color: #4e5e58; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.76rem; }}
    .stack {{ display: grid; gap: 12px; }}
    .photo-row {{
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
      min-height: 300px;
      padding: 6px;
    }}
    .rows-wrap {{
      max-height: 520px;
      overflow: auto;
      border: 1px solid #ece4d3;
      border-radius: 8px;
    }}
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
    textarea {{
      border: 1px solid #d4cdbd;
      border-radius: 7px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 6px 8px;
      width: 100%;
      min-height: 76px;
      resize: vertical;
    }}
    .photo-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .photo-meta {{
      font-size: 0.8rem;
      color: #576763;
      margin-bottom: 8px;
    }}
    .notes-wrap {{
      display: grid;
      gap: 6px;
      margin-bottom: 8px;
    }}
    .notes-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    @media (max-width: 1080px) {{
      .photo-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Quick Multi Photo Labeler</h1>
      <p class="small">Latest run stacked labeling view (one global save/export).</p>
      <p class="small">capture_date=<strong>{capture_date_esc}</strong> | photos=<strong>{count_esc}</strong></p>
      <p class="small">Generated (UTC): <code>{esc(generated)}</code></p>
      <div class="btns">
        <button id="save-all" class="good">Save All Local</button>
        <button id="download-all" class="primary">Download JSON (all photos)</button>
      </div>
      <p id="global-status" class="status">Loading photos...</p>
    </section>

    <section id="photos-root" class="stack"></section>
  </main>

  <script>
  (() => {{
    const PHOTOS = {photos_json};
    const STORAGE_KEY = `quick_multi_labeler_v1::${{(PHOTOS[0] && PHOTOS[0].capture_date) || "unknown"}}`;
    const root = document.getElementById("photos-root");
    const globalStatus = document.getElementById("global-status");
    const saveAllBtn = document.getElementById("save-all");
    const downloadAllBtn = document.getElementById("download-all");

    if (!window.fabric) {{
      globalStatus.textContent = "Fabric.js failed to load.";
      return;
    }}

    const state = {{
      sessions: []
    }};

    const savedByKey = new Map();

    function setGlobalStatus(message) {{
      globalStatus.textContent = message;
    }}

    function keyFor(meta) {{
      return `${{meta.row_index}}::${{meta.source_asset_id}}`;
    }}

    function isAnno(obj) {{
      return obj && obj.type === "rect" && obj.quickAnno === true;
    }}

    function boxes(session) {{
      return session.canvas.getObjects()
        .filter(isAnno)
        .sort((a, b) => (a.annoId || 0) - (b.annoId || 0));
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

    function normCoords(session, obj) {{
      const x = (obj.left || 0) / session.displayScale;
      const y = (obj.top || 0) / session.displayScale;
      const w = obj.getScaledWidth() / session.displayScale;
      const h = obj.getScaledHeight() / session.displayScale;
      return {{
        x, y, w, h,
        x_norm: x / session.naturalWidth,
        y_norm: y / session.naturalHeight,
        w_norm: w / session.naturalWidth,
        h_norm: h / session.naturalHeight
      }};
    }}

    function normText(session, obj) {{
      if (!session.naturalWidth || !session.naturalHeight) return "-";
      const n = normCoords(session, obj);
      return `${{n.x_norm.toFixed(4)}},${{n.y_norm.toFixed(4)}},${{n.w_norm.toFixed(4)}},${{n.h_norm.toFixed(4)}}`;
    }}

    function renderTable(session) {{
      session.boxesBody.innerHTML = "";
      boxes(session).forEach((box) => {{
        const tr = document.createElement("tr");
        const desc = (box.annoDescription || "").replaceAll('"', "&quot;");
        tr.innerHTML = `
          <td><strong>#${{box.annoId}}</strong></td>
          <td><input data-id="${{box.annoId}}" data-field="description" value="${{desc}}" /></td>
          <td class="mono">${{normText(session, box)}}</td>
          <td><button data-id="${{box.annoId}}" data-action="delete">Delete</button></td>
        `;
        session.boxesBody.appendChild(tr);
      }});

      session.boxesBody.querySelectorAll("[data-id][data-field='description']").forEach((el) => {{
        el.addEventListener("input", () => {{
          const id = Number(el.getAttribute("data-id"));
          const box = boxes(session).find((b) => b.annoId === id);
          if (!box) return;
          box.annoDescription = el.value || "";
          saveAllLocal(true);
        }});
      }});

      session.boxesBody.querySelectorAll("[data-id][data-action='delete']").forEach((el) => {{
        el.addEventListener("click", () => {{
          const id = Number(el.getAttribute("data-id"));
          const box = boxes(session).find((b) => b.annoId === id);
          if (!box) return;
          session.canvas.remove(box);
          session.canvas.requestRenderAll();
          renderTable(session);
          saveAllLocal(true);
        }});
      }});
    }}

    function setDrawMode(session, enabled) {{
      session.drawMode = enabled;
      session.drawToggleBtn.textContent = `Draw Mode: ${{enabled ? "ON" : "OFF"}}`;
      session.drawToggleBtn.className = enabled ? "warn" : "good";
      session.canvas.selection = !enabled;
      session.canvas.forEachObject((obj) => {{
        if (isAnno(obj)) {{
          obj.selectable = !enabled;
          obj.evented = !enabled;
        }}
      }});
      session.canvas.requestRenderAll();
    }}

    function clearBoxes(session) {{
      boxes(session).forEach((b) => session.canvas.remove(b));
      session.nextId = 1;
      session.canvas.discardActiveObject();
      session.canvas.requestRenderAll();
      renderTable(session);
      saveAllLocal(true);
    }}

    function sessionPayload(session) {{
      const outBoxes = boxes(session).map((b) => {{
        const n = normCoords(session, b);
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
        row_index: session.meta.row_index,
        source_asset_id: session.meta.source_asset_id,
        capture_date: session.meta.capture_date,
        photo_url: session.meta.photo_url,
        review_notes: (session.notesInput.value || "").trim(),
        exclude_from_training: Boolean(session.excludeFromTraining),
        image_src: session.meta.image_src,
        image_width: session.naturalWidth,
        image_height: session.naturalHeight,
        boxes: outBoxes
      }};
    }}

    function payload() {{
      return {{
        version: "quick-multi-photo-v1",
        saved_at_utc: new Date().toISOString(),
        capture_date: (PHOTOS[0] && PHOTOS[0].capture_date) || "",
        photos: state.sessions.map(sessionPayload)
      }};
    }}

    function saveAllLocal(silent) {{
      try {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload()));
      }} catch (err) {{
        setGlobalStatus(`Local save failed: ${{err}}`);
        return;
      }}
      if (!silent) {{
        setGlobalStatus(`Saved all photos locally (${{state.sessions.length}} canvases).`);
      }}
    }}

    function parseSavedLocal() {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      try {{
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.photos)) return;
        parsed.photos.forEach((photo) => {{
          savedByKey.set(
            `${{photo.row_index || ""}}::${{photo.source_asset_id || ""}}`,
            photo
          );
        }});
      }} catch (_err) {{
        return;
      }}
    }}

    function restoreSessionBoxes(session) {{
      const saved = savedByKey.get(keyFor(session.meta));
      if (!saved || !Array.isArray(saved.boxes)) return false;
      session.notesInput.value = String(saved.review_notes || "");
      setDoNotUse(session, Boolean(saved.exclude_from_training));
      saved.boxes.forEach((b, idx) => {{
        const rect = makeRect({{
          left: Number(b.x || 0) * session.displayScale,
          top: Number(b.y || 0) * session.displayScale,
          width: Math.max(2, Number(b.w || 0) * session.displayScale),
          height: Math.max(2, Number(b.h || 0) * session.displayScale),
          annoId: Number(b.id || (idx + 1)),
          annoDescription: b.description || ""
        }});
        session.canvas.add(rect);
      }});
      const ids = boxes(session).map((b) => Number(b.annoId || 0));
      session.nextId = ids.length ? Math.max(...ids) + 1 : 1;
      renderTable(session);
      session.canvas.requestRenderAll();
      return true;
    }}

    function setDoNotUse(session, enabled) {{
      session.excludeFromTraining = Boolean(enabled);
      session.doNotUseBtn.textContent = `Do Not Use: ${{session.excludeFromTraining ? "ON" : "OFF"}}`;
      session.doNotUseBtn.className = session.excludeFromTraining ? "danger" : "warn";
    }}

    function loadImageFromSources(sources, index, onLoaded, onFail) {{
      if (index >= sources.length) {{
        onFail();
        return;
      }}
      const src = (sources[index] || "").trim();
      if (!src) {{
        loadImageFromSources(sources, index + 1, onLoaded, onFail);
        return;
      }}
      const imgEl = new Image();
      if (src.startsWith("http://") || src.startsWith("https://")) {{
        imgEl.crossOrigin = "anonymous";
      }}
      imgEl.onload = () => {{
        if (!imgEl.naturalWidth || !imgEl.naturalHeight) {{
          loadImageFromSources(sources, index + 1, onLoaded, onFail);
          return;
        }}
        onLoaded(src, imgEl);
      }};
      imgEl.onerror = () => {{
        loadImageFromSources(sources, index + 1, onLoaded, onFail);
      }};
      imgEl.src = src;
    }}

    function createPhotoSection(meta, index) {{
      const section = document.createElement("article");
      section.className = "card";
      section.innerHTML = `
        <div class="photo-head">
          <h2 style="margin:0;">Photo ${{index + 1}} — Row ${{meta.row_index}}</h2>
          <div class="btns">
            <button class="draw-toggle good">Draw Mode: OFF</button>
            <button class="delete-selected danger">Delete Selected</button>
            <button class="clear-boxes">Clear Boxes</button>
          </div>
        </div>
        <p class="photo-meta">asset=<strong>${{meta.source_asset_id}}</strong> | <a href="${{meta.photo_url}}" target="_blank" rel="noreferrer">Open photo_url</a></p>
        <div class="notes-wrap">
          <div class="notes-head">
            <strong>Image Notes</strong>
            <button class="do-not-use warn">Do Not Use: OFF</button>
          </div>
          <textarea class="photo-notes" placeholder="Write notes for this image (quality, occlusion, tag legibility, anything useful)."></textarea>
        </div>
        <div class="photo-row">
          <div class="card" style="padding:8px;">
            <div class="canvas-wrap"><canvas id="canvas-${{index}}" width="1200" height="800"></canvas></div>
            <p class="small">Turn Draw Mode ON to draw. OFF to select/move/resize.</p>
          </div>
          <div class="card" style="padding:8px;">
            <h3 style="margin-top:0;">Boxes + Description</h3>
            <div class="rows-wrap">
              <table>
                <thead>
                  <tr><th>ID</th><th>Description</th><th class="mono">Norm (x,y,w,h)</th><th>Action</th></tr>
                </thead>
                <tbody class="boxes-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      `;
      root.appendChild(section);

      const drawToggleBtn = section.querySelector(".draw-toggle");
      const deleteSelectedBtn = section.querySelector(".delete-selected");
      const clearBoxesBtn = section.querySelector(".clear-boxes");
      const doNotUseBtn = section.querySelector(".do-not-use");
      const notesInput = section.querySelector(".photo-notes");
      const boxesBody = section.querySelector(".boxes-body");
      const canvas = new fabric.Canvas(`canvas-${{index}}`, {{
        preserveObjectStacking: true,
        selection: true
      }});

      const session = {{
        meta,
        canvas,
        boxesBody,
        drawToggleBtn,
        deleteSelectedBtn,
        clearBoxesBtn,
        doNotUseBtn,
        notesInput,
        excludeFromTraining: false,
        drawMode: false,
        drawRect: null,
        drawStart: null,
        nextId: 1,
        naturalWidth: 0,
        naturalHeight: 0,
        displayScale: 1
      }};
      state.sessions.push(session);

      canvas.on("mouse:down", (opt) => {{
        if (!session.drawMode) return;
        const p = canvas.getPointer(opt.e);
        session.drawStart = p;
        session.drawRect = makeRect({{
          left: p.x,
          top: p.y,
          width: 1,
          height: 1,
          annoId: session.nextId,
          annoDescription: ""
        }});
        canvas.add(session.drawRect);
        canvas.setActiveObject(session.drawRect);
      }});

      canvas.on("mouse:move", (opt) => {{
        if (!session.drawMode || !session.drawRect || !session.drawStart) return;
        const p = canvas.getPointer(opt.e);
        session.drawRect.set({{
          left: Math.min(session.drawStart.x, p.x),
          top: Math.min(session.drawStart.y, p.y),
          width: Math.max(1, Math.abs(p.x - session.drawStart.x)),
          height: Math.max(1, Math.abs(p.y - session.drawStart.y))
        }});
        session.drawRect.setCoords();
        canvas.requestRenderAll();
      }});

      canvas.on("mouse:up", () => {{
        if (!session.drawMode || !session.drawRect) return;
        if (session.drawRect.width < 8 || session.drawRect.height < 8) {{
          canvas.remove(session.drawRect);
        }} else {{
          session.drawRect.annoId = session.nextId;
          session.nextId += 1;
        }}
        session.drawRect = null;
        session.drawStart = null;
        renderTable(session);
        saveAllLocal(true);
      }});

      canvas.on("object:modified", () => {{
        renderTable(session);
        saveAllLocal(true);
      }});

      drawToggleBtn.addEventListener("click", () => {{
        setDrawMode(session, !session.drawMode);
      }});
      deleteSelectedBtn.addEventListener("click", () => {{
        const active = canvas.getActiveObject();
        if (!active || !isAnno(active)) {{
          setGlobalStatus(`Row ${{meta.row_index}}: select a box first.`);
          return;
        }}
        canvas.remove(active);
        canvas.requestRenderAll();
        renderTable(session);
        saveAllLocal(true);
      }});
      clearBoxesBtn.addEventListener("click", () => {{
        clearBoxes(session);
        setGlobalStatus(`Row ${{meta.row_index}}: cleared all boxes.`);
      }});
      doNotUseBtn.addEventListener("click", () => {{
        setDoNotUse(session, !session.excludeFromTraining);
        saveAllLocal(true);
      }});
      notesInput.addEventListener("input", () => {{
        saveAllLocal(true);
      }});

      setDrawMode(session, false);
      setDoNotUse(session, false);

      loadImageFromSources(
        [meta.image_src || "", meta.photo_url || ""],
        0,
        (_source, imgEl) => {{
          const img = new fabric.Image(imgEl);
          canvas.clear();
          const maxW = Math.max(700, Math.min(window.innerWidth - 120, 1240));
          const scale = Math.min(1, maxW / img.width);
          session.displayScale = scale;
          session.naturalWidth = img.width;
          session.naturalHeight = img.height;
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
          renderTable(session);
          restoreSessionBoxes(session);
        }},
        () => {{
          setGlobalStatus(`Failed to load row ${{meta.row_index}} from all sources.`);
        }}
      );
    }}

    function downloadAll() {{
      const out = payload();
      const blob = new Blob([JSON.stringify(out, null, 2)], {{ type: "application/json;charset=utf-8" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `quick_seed_multi_${{(PHOTOS[0] && PHOTOS[0].capture_date) || "unknown"}}_${{new Date().toISOString().replaceAll(":", "-")}}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setGlobalStatus("Downloaded combined JSON.");
    }}

    parseSavedLocal();

    if (!Array.isArray(PHOTOS) || PHOTOS.length === 0) {{
      setGlobalStatus("No photos available for latest run.");
      return;
    }}
    PHOTOS.forEach((meta, index) => createPhotoSection(meta, index));

    saveAllBtn.addEventListener("click", () => saveAllLocal(false));
    downloadAllBtn.addEventListener("click", downloadAll);
    setGlobalStatus(`Loaded ${{PHOTOS.length}} photos for capture_date ${{PHOTOS[0].capture_date}}.`);
  }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a stacked multi-photo labeler page for latest run."
    )
    parser.add_argument(
        "--mixed-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Mixed labeled CSV used to pick latest run images.",
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
        default=Path("tracker/multi-photo-quick-labeler.html"),
        help="Output HTML path.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Optional max images to include (0 means all latest-run photos).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    photos = pick_latest_images(args.mixed_csv, args.image_dir, max_images=args.max_images)
    html = build_page(photos)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    print(f"capture_date={photos[0]['capture_date']}")
    print(f"photos={len(photos)}")
    print(f"first_row={photos[0]['row_index']} first_asset={photos[0]['source_asset_id']}")
    print(f"last_row={photos[-1]['row_index']} last_asset={photos[-1]['source_asset_id']}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
