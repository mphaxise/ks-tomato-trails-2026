#!/usr/bin/env python3
"""Build a one-photo seed labeler page using Fabric.js."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_IMAGE = (
    "../local/non_tomato_species/images/"
    "59_AF1QipPdG_T6UaPwBUD1RGWtW2icgq6HQUXJSBMzrBw0.jpg"
)


def esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def build_page(default_image: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    default_image_escaped = esc(default_image)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Single Photo Seed Labeler</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
  <style>
    :root {{
      --bg: #f2efe8;
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
      max-width: 1560px;
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
    .controls {{
      display: grid;
      grid-template-columns: 2.1fr 1fr 1fr 1fr;
      gap: 8px;
      align-items: end;
    }}
    .controls label, .notes label {{
      display: grid;
      gap: 4px;
      font-size: 0.82rem;
      color: #4e5e58;
    }}
    input, select, textarea, button {{
      border: 1px solid #d4cdbd;
      border-radius: 8px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 7px 9px;
    }}
    textarea {{ min-height: 70px; resize: vertical; }}
    .btn-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    button.primary {{
      background: var(--blue);
      color: #fff;
      border-color: var(--blue);
      font-weight: 700;
    }}
    button.good {{
      background: var(--green);
      color: #fff;
      border-color: var(--green);
      font-weight: 700;
    }}
    button.warn {{
      background: var(--amber);
      color: #fff;
      border-color: var(--amber);
      font-weight: 700;
    }}
    button.danger {{
      background: var(--red);
      color: #fff;
      border-color: var(--red);
      font-weight: 700;
    }}
    .work {{
      display: grid;
      grid-template-columns: 2.1fr 1fr;
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
    #fabric-canvas {{
      display: block;
      max-width: 100%;
      border-radius: 8px;
      background: #f7f2e7;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    th, td {{
      border-bottom: 1px solid #ece4d3;
      padding: 6px 4px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #f6f1e5;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    .rows-wrap {{
      max-height: 700px;
      overflow: auto;
      border: 1px solid #ece4d3;
      border-radius: 8px;
    }}
    .small {{
      font-size: 0.75rem;
      color: #5b6964;
    }}
    .status {{
      font-size: 0.82rem;
      color: #4e5e58;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.76rem;
    }}
    @media (max-width: 1020px) {{
      .controls {{ grid-template-columns: 1fr; }}
      .work {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Single Photo Seed Labeler</h1>
      <p class="small">Powered by <strong>Fabric.js</strong> for box creation, selection, move, and resize.</p>
      <p class="small">Generated (UTC): <code>{generated}</code></p>
    </section>

    <section class="card">
      <div class="controls">
        <label>Image Path (relative or URL)
          <input id="image-src" value="{default_image_escaped}" />
        </label>
        <label>Default New Box Label
          <select id="default-label">
            <option value="pot_label">pot_label</option>
            <option value="plant_region">plant_region</option>
            <option value="fruit_cluster">fruit_cluster</option>
            <option value="leaf_health_issue">leaf_health_issue</option>
            <option value="background_number">background_number</option>
            <option value="other">other</option>
          </select>
        </label>
        <label>Reviewer
          <input id="reviewer-name" placeholder="initials or name" />
        </label>
        <div class="btn-row">
          <button id="load-image" class="primary">Load Image</button>
          <button id="draw-mode" class="good">Draw Mode: OFF</button>
        </div>
      </div>

      <div class="notes" style="margin-top:8px;">
        <label>Global Description / Context
          <textarea id="global-description" placeholder="Describe this photo and your labeling intent."></textarea>
        </label>
      </div>

      <div class="btn-row" style="margin-top:8px;">
        <button id="save-local" class="good">Save Local State</button>
        <button id="export-json" class="primary">Export JSON</button>
        <button id="export-csv">Export CSV</button>
        <label style="display:inline-flex;align-items:center;gap:6px;">
          <span class="small">Import JSON</span>
          <input id="import-json" type="file" accept=".json,application/json" />
        </label>
        <button id="delete-selected" class="danger">Delete Selected Box</button>
        <button id="clear-boxes">Clear Boxes</button>
        <button id="reset-local" class="warn">Reset Local State</button>
      </div>
      <p id="status" class="status">Ready.</p>
    </section>

    <section class="work">
      <article class="card">
        <h2 style="margin-top:0;">Photo Canvas</h2>
        <div class="canvas-wrap">
          <canvas id="fabric-canvas" width="1200" height="800"></canvas>
        </div>
        <p class="small">
          Workflow: click <strong>Draw Mode</strong> ON, drag to create boxes, then turn it OFF to select/move/resize.
        </p>
      </article>

      <article class="card">
        <h2 style="margin-top:0;">Boxes</h2>
        <div class="small">Each box has a label and one text line. Coordinates are normalized to original image dimensions.</div>
        <div class="rows-wrap" style="margin-top:6px;">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Label</th>
                <th>Text Line</th>
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
    if (!window.fabric) {{
      document.getElementById("status").textContent = "Fabric.js failed to load. Check network access.";
      return;
    }}

    const STORAGE_PREFIX = "single_photo_seed_labeler_fabric_v1";
    const imageSrcInput = document.getElementById("image-src");
    const defaultLabelSelect = document.getElementById("default-label");
    const reviewerInput = document.getElementById("reviewer-name");
    const globalDesc = document.getElementById("global-description");
    const loadBtn = document.getElementById("load-image");
    const drawBtn = document.getElementById("draw-mode");
    const saveLocalBtn = document.getElementById("save-local");
    const exportJsonBtn = document.getElementById("export-json");
    const exportCsvBtn = document.getElementById("export-csv");
    const importJsonInput = document.getElementById("import-json");
    const deleteSelectedBtn = document.getElementById("delete-selected");
    const clearBtn = document.getElementById("clear-boxes");
    const resetLocalBtn = document.getElementById("reset-local");
    const statusEl = document.getElementById("status");
    const boxesBody = document.getElementById("boxes-body");

    const labelOptions = [
      "pot_label",
      "plant_region",
      "fruit_cluster",
      "leaf_health_issue",
      "background_number",
      "other"
    ];

    const state = {{
      imageSrc: "",
      naturalWidth: 0,
      naturalHeight: 0,
      displayScale: 1,
      nextId: 1,
      drawMode: false
    }};

    const canvas = new fabric.Canvas("fabric-canvas", {{
      preserveObjectStacking: true,
      selection: true
    }});

    let backgroundImage = null;
    let drawRect = null;
    let drawStart = null;

    function setStatus(msg) {{
      statusEl.textContent = msg;
    }}

    function storageKey(src) {{
      return `${{STORAGE_PREFIX}}::${{(src || "").trim() || "empty"}}`;
    }}

    function isAnnotationObject(obj) {{
      return obj && obj.type === "rect" && obj.seedAnno === true;
    }}

    function getBoxes() {{
      return canvas.getObjects().filter(isAnnotationObject);
    }}

    function sortBoxes(boxes) {{
      return [...boxes].sort((a, b) => (a.annoId || 0) - (b.annoId || 0));
    }}

    function scaledRectData(obj) {{
      const w = obj.getScaledWidth();
      const h = obj.getScaledHeight();
      const x = obj.left || 0;
      const y = obj.top || 0;
      return {{ x, y, w, h }};
    }}

    function toNativeCoords(obj) {{
      const d = scaledRectData(obj);
      return {{
        x: d.x / state.displayScale,
        y: d.y / state.displayScale,
        w: d.w / state.displayScale,
        h: d.h / state.displayScale
      }};
    }}

    function normString(obj) {{
      if (!state.naturalWidth || !state.naturalHeight) return "-";
      const n = toNativeCoords(obj);
      const nx = (n.x / state.naturalWidth).toFixed(4);
      const ny = (n.y / state.naturalHeight).toFixed(4);
      const nw = (n.w / state.naturalWidth).toFixed(4);
      const nh = (n.h / state.naturalHeight).toFixed(4);
      return `${{nx}},${{ny}},${{nw}},${{nh}}`;
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
        seedAnno: true,
        annoId: opts.annoId || 0,
        annoLabel: opts.annoLabel || "other",
        annoText: opts.annoText || ""
      }});
    }}

    function renderBoxesTable() {{
      boxesBody.innerHTML = "";
      const boxes = sortBoxes(getBoxes());
      boxes.forEach((box) => {{
        const tr = document.createElement("tr");
        const labelOptionsHtml = labelOptions.map((opt) => {{
          const selected = opt === box.annoLabel ? "selected" : "";
          return `<option value="${{opt}}" ${{selected}}>${{opt}}</option>`;
        }}).join("");
        const textSafe = (box.annoText || "").replaceAll('"', "&quot;");
        tr.innerHTML = `
          <td><strong>#${{box.annoId}}</strong></td>
          <td><select data-id="${{box.annoId}}" data-field="label">${{labelOptionsHtml}}</select></td>
          <td><input data-id="${{box.annoId}}" data-field="text" value="${{textSafe}}" /></td>
          <td class="mono">${{normString(box)}}</td>
          <td><button data-id="${{box.annoId}}" data-action="delete">Delete</button></td>
        `;
        boxesBody.appendChild(tr);
      }});

      boxesBody.querySelectorAll("[data-id][data-field]").forEach((el) => {{
        el.addEventListener("input", () => {{
          const id = Number(el.getAttribute("data-id"));
          const field = el.getAttribute("data-field");
          const box = getBoxes().find((b) => b.annoId === id);
          if (!box || !field) return;
          if (field === "label") box.annoLabel = el.value || "other";
          if (field === "text") box.annoText = el.value || "";
          saveLocalState();
          canvas.requestRenderAll();
        }});
        el.addEventListener("change", () => {{
          const id = Number(el.getAttribute("data-id"));
          const field = el.getAttribute("data-field");
          const box = getBoxes().find((b) => b.annoId === id);
          if (!box || !field) return;
          if (field === "label") box.annoLabel = el.value || "other";
          if (field === "text") box.annoText = el.value || "";
          saveLocalState();
          canvas.requestRenderAll();
        }});
      }});

      boxesBody.querySelectorAll("[data-action='delete']").forEach((el) => {{
        el.addEventListener("click", () => {{
          const id = Number(el.getAttribute("data-id"));
          const box = getBoxes().find((b) => b.annoId === id);
          if (!box) return;
          canvas.remove(box);
          saveLocalState();
          renderBoxesTable();
          canvas.requestRenderAll();
        }});
      }});
    }}

    function setDrawMode(enabled) {{
      state.drawMode = enabled;
      drawBtn.textContent = `Draw Mode: ${{enabled ? "ON" : "OFF"}}`;
      drawBtn.className = enabled ? "warn" : "good";
      canvas.selection = !enabled;
      canvas.forEachObject((obj) => {{
        if (isAnnotationObject(obj)) {{
          obj.selectable = !enabled;
          obj.evented = !enabled;
        }}
      }});
      canvas.requestRenderAll();
    }}

    function clearBoxes() {{
      getBoxes().forEach((box) => canvas.remove(box));
      state.nextId = 1;
      canvas.discardActiveObject();
      canvas.requestRenderAll();
      renderBoxesTable();
      saveLocalState();
    }}

    function payload() {{
      const boxes = sortBoxes(getBoxes()).map((box) => {{
        const n = toNativeCoords(box);
        return {{
          id: box.annoId,
          label: box.annoLabel || "other",
          text_line: box.annoText || "",
          x: Number(n.x.toFixed(2)),
          y: Number(n.y.toFixed(2)),
          w: Number(n.w.toFixed(2)),
          h: Number(n.h.toFixed(2)),
          x_norm: Number((n.x / state.naturalWidth).toFixed(6)),
          y_norm: Number((n.y / state.naturalHeight).toFixed(6)),
          w_norm: Number((n.w / state.naturalWidth).toFixed(6)),
          h_norm: Number((n.h / state.naturalHeight).toFixed(6))
        }};
      }});
      return {{
        version: "single-photo-seed-fabric-v1",
        saved_at_utc: new Date().toISOString(),
        image_src: state.imageSrc,
        image_width: state.naturalWidth,
        image_height: state.naturalHeight,
        reviewer: (reviewerInput.value || "").trim(),
        global_description: globalDesc.value || "",
        boxes
      }};
    }}

    function saveLocalState() {{
      if (!state.imageSrc) return;
      try {{
        localStorage.setItem(storageKey(state.imageSrc), JSON.stringify(payload()));
      }} catch (err) {{
        setStatus(`Local save failed: ${{err}}`);
        return;
      }}
      setStatus(`Saved locally (${{getBoxes().length}} boxes).`);
    }}

    function loadSavedState(src) {{
      const raw = localStorage.getItem(storageKey(src));
      if (!raw) return false;
      try {{
        const obj = JSON.parse(raw);
        if (!obj || !Array.isArray(obj.boxes)) return false;
        globalDesc.value = obj.global_description || "";
        reviewerInput.value = obj.reviewer || "";
        clearBoxes();
        obj.boxes.forEach((b, idx) => {{
          const left = Number(b.x || 0) * state.displayScale;
          const top = Number(b.y || 0) * state.displayScale;
          const width = Number(b.w || 0) * state.displayScale;
          const height = Number(b.h || 0) * state.displayScale;
          const rect = makeRect({{
            left,
            top,
            width: Math.max(2, width),
            height: Math.max(2, height),
            annoId: Number(b.id || (idx + 1)),
            annoLabel: b.label || "other",
            annoText: b.text_line || ""
          }});
          canvas.add(rect);
        }});
        const ids = getBoxes().map((b) => Number(b.annoId || 0));
        state.nextId = ids.length ? Math.max(...ids) + 1 : 1;
        renderBoxesTable();
        canvas.requestRenderAll();
        return true;
      }} catch (_err) {{
        return false;
      }}
    }}

    function removeAllObjects() {{
      canvas.getObjects().forEach((obj) => canvas.remove(obj));
    }}

    function loadImage(src, onDone) {{
      const trimmed = (src || "").trim();
      if (!trimmed) {{
        setStatus("Enter an image path.");
        return;
      }}
      fabric.Image.fromURL(trimmed, (img) => {{
        if (!img) {{
          setStatus("Failed to load image.");
          return;
        }}
        removeAllObjects();
        backgroundImage = img;
        const maxW = Math.max(700, Math.min(window.innerWidth - 500, 1160));
        const scale = Math.min(1, maxW / img.width);
        state.displayScale = scale;
        state.naturalWidth = img.width;
        state.naturalHeight = img.height;
        state.imageSrc = trimmed;
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
        const loaded = loadSavedState(trimmed);
        if (!loaded) {{
          renderBoxesTable();
          canvas.requestRenderAll();
          setStatus("Image loaded. Draw boxes to begin.");
        }} else {{
          setStatus("Image loaded with saved annotations.");
        }}
        if (onDone) onDone();
      }}, {{
        crossOrigin: "anonymous"
      }});
    }}

    function exportJson() {{
      if (!state.imageSrc) {{
        setStatus("Load an image first.");
        return;
      }}
      const out = payload();
      const blob = new Blob([JSON.stringify(out, null, 2)], {{ type: "application/json;charset=utf-8" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      const safe = (state.imageSrc.split("/").pop() || "image").replaceAll(".", "_");
      a.download = `seed_annotation_${{safe}}_${{new Date().toISOString().replaceAll(":", "-")}}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setStatus("Exported JSON.");
    }}

    function csvValue(v) {{
      const text = v == null ? "" : String(v);
      if (text.includes(",") || text.includes('"') || text.includes("\\n")) {{
        return `"${{text.replaceAll('"', '""')}}"`;
      }}
      return text;
    }}

    function exportCsv() {{
      if (!state.imageSrc) {{
        setStatus("Load an image first.");
        return;
      }}
      const data = payload();
      const headers = [
        "image_src", "reviewer", "global_description",
        "box_id", "label", "text_line",
        "x", "y", "w", "h", "x_norm", "y_norm", "w_norm", "h_norm"
      ];
      const lines = [headers.join(",")];
      data.boxes.forEach((box) => {{
        const row = {{
          image_src: data.image_src,
          reviewer: data.reviewer,
          global_description: data.global_description,
          box_id: box.id,
          label: box.label,
          text_line: box.text_line,
          x: box.x,
          y: box.y,
          w: box.w,
          h: box.h,
          x_norm: box.x_norm,
          y_norm: box.y_norm,
          w_norm: box.w_norm,
          h_norm: box.h_norm
        }};
        lines.push(headers.map((h) => csvValue(row[h])).join(","));
      }});
      const blob = new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv;charset=utf-8" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      const safe = (state.imageSrc.split("/").pop() || "image").replaceAll(".", "_");
      a.download = `seed_annotation_${{safe}}_${{new Date().toISOString().replaceAll(":", "-")}}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setStatus("Exported CSV.");
    }}

    function importJsonFile(file) {{
      const reader = new FileReader();
      reader.onload = () => {{
        try {{
          const obj = JSON.parse(String(reader.result || ""));
          if (!obj || !Array.isArray(obj.boxes) || !obj.image_src) {{
            throw new Error("Invalid annotation JSON.");
          }}
          imageSrcInput.value = obj.image_src;
          loadImage(obj.image_src, () => {{
            clearBoxes();
            obj.boxes.forEach((b, idx) => {{
              const rect = makeRect({{
                left: Number(b.x || 0) * state.displayScale,
                top: Number(b.y || 0) * state.displayScale,
                width: Math.max(2, Number(b.w || 0) * state.displayScale),
                height: Math.max(2, Number(b.h || 0) * state.displayScale),
                annoId: Number(b.id || (idx + 1)),
                annoLabel: b.label || "other",
                annoText: b.text_line || ""
              }});
              canvas.add(rect);
            }});
            const ids = getBoxes().map((b) => Number(b.annoId || 0));
            state.nextId = ids.length ? Math.max(...ids) + 1 : 1;
            globalDesc.value = obj.global_description || "";
            reviewerInput.value = obj.reviewer || "";
            canvas.requestRenderAll();
            renderBoxesTable();
            saveLocalState();
            setStatus("Imported JSON.");
          }});
        }} catch (err) {{
          setStatus(`Import failed: ${{err}}`);
        }}
      }};
      reader.readAsText(file);
    }}

    canvas.on("mouse:down", (opt) => {{
      if (!state.drawMode || !state.imageSrc) return;
      const pointer = canvas.getPointer(opt.e);
      drawStart = pointer;
      drawRect = makeRect({{
        left: pointer.x,
        top: pointer.y,
        width: 1,
        height: 1,
        annoId: state.nextId,
        annoLabel: defaultLabelSelect.value || "other",
        annoText: ""
      }});
      canvas.add(drawRect);
      canvas.setActiveObject(drawRect);
    }});

    canvas.on("mouse:move", (opt) => {{
      if (!state.drawMode || !drawRect || !drawStart) return;
      const pointer = canvas.getPointer(opt.e);
      const left = Math.min(drawStart.x, pointer.x);
      const top = Math.min(drawStart.y, pointer.y);
      const width = Math.abs(pointer.x - drawStart.x);
      const height = Math.abs(pointer.y - drawStart.y);
      drawRect.set({{ left, top, width: Math.max(1, width), height: Math.max(1, height) }});
      drawRect.setCoords();
      canvas.requestRenderAll();
    }});

    canvas.on("mouse:up", () => {{
      if (!state.drawMode || !drawRect) return;
      const tooSmall = drawRect.width < 8 || drawRect.height < 8;
      if (tooSmall) {{
        canvas.remove(drawRect);
      }} else {{
        drawRect.annoId = state.nextId;
        state.nextId += 1;
      }}
      drawRect = null;
      drawStart = null;
      renderBoxesTable();
      saveLocalState();
    }});

    canvas.on("object:modified", () => {{
      renderBoxesTable();
      saveLocalState();
    }});

    canvas.on("object:removed", () => {{
      renderBoxesTable();
    }});

    loadBtn.addEventListener("click", () => loadImage(imageSrcInput.value));
    drawBtn.addEventListener("click", () => setDrawMode(!state.drawMode));
    saveLocalBtn.addEventListener("click", saveLocalState);
    exportJsonBtn.addEventListener("click", exportJson);
    exportCsvBtn.addEventListener("click", exportCsv);

    deleteSelectedBtn.addEventListener("click", () => {{
      const active = canvas.getActiveObject();
      if (!active || !isAnnotationObject(active)) {{
        setStatus("Select a box first.");
        return;
      }}
      canvas.remove(active);
      saveLocalState();
      renderBoxesTable();
      canvas.requestRenderAll();
    }});

    clearBtn.addEventListener("click", () => {{
      clearBoxes();
      setStatus("All boxes cleared.");
    }});

    resetLocalBtn.addEventListener("click", () => {{
      const src = (imageSrcInput.value || "").trim();
      if (!src) {{
        setStatus("Image path is empty.");
        return;
      }}
      if (!confirm("Delete local saved annotation state for this image?")) return;
      localStorage.removeItem(storageKey(src));
      setStatus("Local state deleted for this image.");
    }});

    importJsonInput.addEventListener("change", (evt) => {{
      const file = evt.target.files && evt.target.files[0];
      if (!file) return;
      importJsonFile(file);
      evt.target.value = "";
    }});

    globalDesc.addEventListener("input", () => {{
      if (state.imageSrc) saveLocalState();
    }});
    reviewerInput.addEventListener("input", () => {{
      if (state.imageSrc) saveLocalState();
    }});

    setDrawMode(false);
    loadImage(imageSrcInput.value);
  }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one-photo seed labeler HTML page."
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/single-photo-seed-labeler.html"),
        help="Output HTML path.",
    )
    parser.add_argument(
        "--default-image",
        default=DEFAULT_IMAGE,
        help="Default image path/URL shown on page load.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    html = build_page(args.default_image)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    print(f"default_image={args.default_image}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
