#!/usr/bin/env python3
"""Build a focused reviewer page for hard OCR rows."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency for overlay only
    cv2 = None


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def html_escape(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def slugify(text: str) -> str:
    output = []
    for char in (text or "").strip().lower():
        if char.isalnum():
            output.append(char)
        else:
            output.append("_")
    compact = "".join(output)
    while "__" in compact:
        compact = compact.replace("__", "_")
    return compact.strip("_")


def parse_int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def parse_pot_number_from_id(pot_id: str) -> int:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return 0
    return int(matched.group(1))


def parse_detected_numbers(value: str) -> List[int]:
    numbers: List[int] = []
    seen = set()
    for token in re.findall(r"\b([0-9]{1,3})\b", value or ""):
        num = int(token)
        if num <= 0 or num > 99 or num in seen:
            continue
        numbers.append(num)
        seen.add(num)
    return numbers


def classify_signal_tier(
    *,
    matched_variant_count: int,
    suggested_pot_id: str,
    ensemble_numbers_detected: str,
) -> Tuple[str, str, int]:
    if matched_variant_count <= 0:
        return (
            "TYPE_III",
            "No signal - sequential guess",
            3,
        )

    pot_number = parse_pot_number_from_id(suggested_pot_id)
    numbers = set(parse_detected_numbers(ensemble_numbers_detected))
    if pot_number > 0 and pot_number in numbers:
        return (
            "TYPE_I",
            "OCR match",
            1,
        )

    return (
        "TYPE_II",
        "Weak OCR",
        2,
    )


def extract_label_ocr_boxes(label_path: Path) -> List[Dict[str, object]]:
    if cv2 is None:
        return []
    if not label_path.exists():
        return []

    image = cv2.imread(str(label_path))
    if image is None:
        return []
    height, width = image.shape[:2]
    if height <= 0 or width <= 0:
        return []

    try:
        result = subprocess.run(
            [
                "tesseract",
                str(label_path),
                "stdout",
                "--psm",
                "11",
                "tsv",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    lines = (result.stdout or "").splitlines()
    if not lines:
        return []

    boxes: List[Dict[str, object]] = []
    seen = set()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        raw_text = (parts[11] or "").strip()
        if not raw_text:
            continue
        token_match = re.fullmatch(r".*?([0-9]{1,3}).*", raw_text)
        if not token_match:
            continue
        num = int(token_match.group(1))
        if num <= 0 or num > 40:
            continue
        left = parse_int(parts[6], default=0)
        top = parse_int(parts[7], default=0)
        box_w = parse_int(parts[8], default=0)
        box_h = parse_int(parts[9], default=0)
        if box_w <= 0 or box_h <= 0:
            continue
        key = (num, left, top, box_w, box_h)
        if key in seen:
            continue
        seen.add(key)
        boxes.append(
            {
                "text": str(num),
                "left_pct": round((left / width) * 100.0, 2),
                "top_pct": round((top / height) * 100.0, 2),
                "width_pct": round((box_w / width) * 100.0, 2),
                "height_pct": round((box_h / height) * 100.0, 2),
            }
        )

    return boxes


def load_latest_variety_by_pot(mapping_csv: Path) -> Dict[str, str]:
    if not mapping_csv.exists():
        return {}
    rows = read_csv_rows(mapping_csv)
    run_dates = sorted(
        {
            (row.get("run_date", "") or "").strip()
            for row in rows
            if (row.get("run_date", "") or "").strip()
        }
    )
    latest = run_dates[-1] if run_dates else ""
    mapping: Dict[str, str] = {}
    for row in rows:
        if latest and (row.get("run_date", "") or "").strip() != latest:
            continue
        pot_id = (row.get("pot_id", "") or "").strip()
        variety = (row.get("variety_name", "") or "").strip()
        if pot_id and variety:
            mapping[pot_id] = variety
    return mapping


def copy_queue_images(
    queue_rows: List[Dict[str, str]],
    assets_dir: Path,
    page_dir: Path,
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    by_row: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row in queue_rows:
        run_date = (row.get("run_date", "") or "").strip()
        row_index = (row.get("row_index", "") or "").strip()
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        row_key = (run_date, row_index, source_asset_id)
        prefix = f"{slugify(run_date)}_{slugify(row_index)}_{slugify(source_asset_id[:12])}"

        copied: Dict[str, str] = {}
        for source_field, suffix in (
            ("full_crop_path", "full"),
            ("center_crop_path", "center"),
            ("label_crop_path", "label"),
        ):
            source_path = Path((row.get(source_field, "") or "").strip())
            if not source_path.exists():
                copied[source_field] = ""
                continue
            target_name = f"{prefix}_{suffix}{source_path.suffix or '.jpg'}"
            target_path = assets_dir / target_name
            shutil.copy2(source_path, target_path)
            relative_url = Path(os.path.relpath(target_path, page_dir)).as_posix()
            if not relative_url.startswith("."):
                relative_url = f"./{relative_url}"
            copied[source_field] = relative_url
            copied[f"{source_field}_target_path"] = str(target_path)

        by_row[row_key] = copied
    return by_row


def build_enriched_rows(
    queue_rows: List[Dict[str, str]],
    variety_by_pot: Dict[str, str],
    assets_by_row: Dict[Tuple[str, str, str], Dict[str, str]],
) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    for row in queue_rows:
        run_date = (row.get("run_date", "") or "").strip()
        row_index = (row.get("row_index", "") or "").strip()
        source_asset_id = (row.get("source_asset_id", "") or "").strip()
        pot_id = (row.get("pot_id", "") or "").strip()
        matched_variant_count = parse_int(row.get("matched_variant_count", "") or "0", default=0)
        ensemble_numbers_detected = (row.get("ensemble_numbers_detected", "") or "").strip()
        row_key = (run_date, row_index, source_asset_id)
        copied = assets_by_row.get(row_key, {})
        signal_tier, signal_label, signal_rank = classify_signal_tier(
            matched_variant_count=matched_variant_count,
            suggested_pot_id=pot_id,
            ensemble_numbers_detected=ensemble_numbers_detected,
        )
        label_target_raw = copied.get("label_crop_path_target_path", "")
        label_ocr_boxes = (
            extract_label_ocr_boxes(Path(label_target_raw)) if label_target_raw else []
        )

        output.append(
            {
                "run_date": run_date,
                "row_index": row_index,
                "source_asset_id": source_asset_id,
                "suggested_pot_id": pot_id,
                "suggested_variety_name": variety_by_pot.get(pot_id, ""),
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "matched_variant_count": str(matched_variant_count),
                "ensemble_numbers_detected": ensemble_numbers_detected,
                "full_crop_url": copied.get("full_crop_path", ""),
                "center_crop_url": copied.get("center_crop_path", ""),
                "label_crop_url": copied.get("label_crop_path", ""),
                "signal_tier": signal_tier,
                "signal_label": signal_label,
                "signal_rank": str(signal_rank),
                "label_ocr_boxes": label_ocr_boxes,
            }
        )
    output.sort(
        key=lambda row: (
            parse_int(row.get("signal_rank", "9"), default=9),
            (row.get("run_date", "") or "").strip(),
            parse_int(row.get("row_index", "9999"), default=9999),
        )
    )
    return output


def build_summary(enriched_rows: List[Dict[str, str]]) -> Dict[str, object]:
    run_counts = Counter((row.get("run_date", "") or "").strip() for row in enriched_rows)
    variant_match_counts = Counter(
        (row.get("matched_variant_count", "") or "").strip() for row in enriched_rows
    )
    signal_tier_counts = Counter(
        (row.get("signal_tier", "") or "").strip() for row in enriched_rows
    )
    return {
        "total_rows": len(enriched_rows),
        "run_counts": dict(run_counts),
        "variant_match_counts": dict(variant_match_counts),
        "signal_tier_counts": dict(signal_tier_counts),
    }


def build_page(
    queue_csv: Path,
    enriched_rows: List[Dict[str, str]],
    summary: Dict[str, object],
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    rows_json = json.dumps(enriched_rows, ensure_ascii=True)
    run_counts = summary.get("run_counts", {})
    if not isinstance(run_counts, dict):
        run_counts = {}
    signal_tier_counts = summary.get("signal_tier_counts", {})
    if not isinstance(signal_tier_counts, dict):
        signal_tier_counts = {}
    run_badges = "".join(
        f"<span class='run-chip'>{html_escape(run)}: <strong>{count}</strong></span>"
        for run, count in sorted(run_counts.items())
    )
    signal_badges = "".join(
        f"<span class='signal-chip {html_escape((tier or '').lower())}'>"
        f"{html_escape(tier)}: <strong>{count}</strong></span>"
        for tier, count in sorted(signal_tier_counts.items())
    )

    cards: List[str] = []
    for index, row in enumerate(enriched_rows, start=1):
        run_date = html_escape(row["run_date"])
        row_index = html_escape(row["row_index"])
        source_asset_id = html_escape(row["source_asset_id"])
        suggested_pot_id = html_escape(row["suggested_pot_id"])
        suggested_variety = html_escape(row["suggested_variety_name"])
        photo_url = html_escape(row["photo_url"])
        full_crop_url = html_escape(row["full_crop_url"])
        center_crop_url = html_escape(row["center_crop_url"])
        label_crop_url = html_escape(row["label_crop_url"])
        matched_variant_count = html_escape(row["matched_variant_count"])
        ensemble_numbers = html_escape(row["ensemble_numbers_detected"])
        signal_tier = html_escape(row.get("signal_tier", ""))
        signal_label = html_escape(row.get("signal_label", ""))
        signal_tier_key = ((row.get("signal_tier", "") or "").strip().lower()) or "unknown"
        label_boxes_raw = row.get("label_ocr_boxes", [])
        label_boxes: List[Dict[str, object]] = (
            label_boxes_raw if isinstance(label_boxes_raw, list) else []
        )
        row_id = f"review-{index:03d}"
        no_signal = signal_tier_key == "type_iii"

        def img(url: str, alt: str) -> str:
            if not url:
                return "<div class='img-missing'>No image</div>"
            return (
                "<button class='img-btn' data-open-lightbox='true' "
                f"data-full='{url}' data-alt='{html_escape(alt)}'>"
                f"<img src='{url}' alt='{html_escape(alt)}' loading='lazy' />"
                "</button>"
            )

        def label_img(url: str, alt: str) -> str:
            if not url:
                return "<div class='img-missing'>No image</div>"
            box_markup: List[str] = []
            for box in label_boxes:
                left = float(box.get("left_pct", 0.0) or 0.0)
                top = float(box.get("top_pct", 0.0) or 0.0)
                box_w = float(box.get("width_pct", 0.0) or 0.0)
                box_h = float(box.get("height_pct", 0.0) or 0.0)
                text = html_escape(str(box.get("text", "") or ""))
                if box_w <= 0 or box_h <= 0:
                    continue
                box_markup.append(
                    "<span class='ocr-box' "
                    f"style='left:{left:.2f}%;top:{top:.2f}%;width:{box_w:.2f}%;height:{box_h:.2f}%;'>"
                    f"<span>{text}</span>"
                    "</span>"
                )

            return (
                "<button class='img-btn img-btn-label' data-open-lightbox='true' "
                f"data-full='{url}' data-alt='{html_escape(alt)}'>"
                "<span class='img-stack'>"
                f"<img src='{url}' alt='{html_escape(alt)}' loading='lazy' />"
                "<span class='ocr-overlay'>"
                + "".join(box_markup)
                + "</span>"
                "</span>"
                "</button>"
            )

        suggested_pot_line = (
            f"Unverified placeholder: <strong>{suggested_pot_id}</strong> "
            "(based on sequence position only)"
            if no_signal
            else f"Suggested Pot: <strong>{suggested_pot_id}</strong>"
        )

        cards.append(
            f"<article class='card' data-row-id='{row_id}' data-run-date='{run_date}' data-signal-tier='{signal_tier_key}'>"
            "<header class='card-head'>"
            f"<h3>{html_escape(suggested_pot_id)} <span>{run_date}</span></h3>"
            f"<p>row={row_index} | asset={source_asset_id}</p>"
            f"<p class='signal-line'><span class='signal-badge {signal_tier_key}'>{signal_label}</span> <code>{signal_tier}</code></p>"
            "</header>"
            "<div class='images'>"
            f"<figure><figcaption>Label Crop (OCR overlays)</figcaption>{label_img(label_crop_url, f'{suggested_pot_id} label')}</figure>"
            f"<figure><figcaption>Center Crop</figcaption>{img(center_crop_url, f'{suggested_pot_id} center')}</figure>"
            f"<figure><figcaption>Full Crop</figcaption>{img(full_crop_url, f'{suggested_pot_id} full')}</figure>"
            "</div>"
            "<div class='meta'>"
            f"<p>{suggested_pot_line}</p>"
            f"<p>Suggested Variety: <strong>{suggested_variety or 'unknown'}</strong></p>"
            f"<p>OCR Match Variants: <strong>{matched_variant_count or '0'}</strong></p>"
            f"<p>OCR Numbers Detected: <code>{ensemble_numbers or 'none'}</code></p>"
            f"<p>Signal Tier: <strong>{signal_tier}</strong> ({signal_label})</p>"
            f"<p><a href='{photo_url}' target='_blank' rel='noreferrer'>Open Original Photo URL</a></p>"
            "</div>"
            "<div class='form'>"
            "<label>Verdict"
            f"<select data-field='verdict' data-row-id='{row_id}'>"
            "<option value='pending' selected>Pending</option>"
            "<option value='confirm'>Confirm suggested mapping</option>"
            "<option value='correct'>Correct mapping</option>"
            "<option value='uncertain'>Uncertain (needs follow-up)</option>"
            "<option value='no_basis'>No basis - cannot verify from this photo</option>"
            "</select>"
            "</label>"
            "<label>Confirmed Pot ID"
            f"<input type='text' data-field='confirmed_pot_id' data-row-id='{row_id}' value='{suggested_pot_id}' />"
            "</label>"
            "<label>Confirmed Variety"
            f"<input type='text' data-field='confirmed_variety_name' data-row-id='{row_id}' value='{suggested_variety}' />"
            "</label>"
            "<label>Reviewer Notes"
            f"<textarea data-field='notes' data-row-id='{row_id}' rows='2' placeholder='Optional note'></textarea>"
            "</label>"
            "</div>"
            "</article>"
        )

    card_html = "\n".join(cards) if cards else "<p class='empty'>No queue rows found.</p>"
    total_rows = int(summary.get("total_rows", 0) or 0)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hard Row Reviewer</title>
  <style>
    :root {{
      --bg: #f4f0e3;
      --card: #fffdf7;
      --ink: #1f2b29;
      --line: #d8d1c2;
      --leaf: #2f6947;
      --amber: #8a5c23;
      --sky: #35597f;
      --danger: #8a2d2b;
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
      max-width: 1340px;
      margin: 0 auto;
      padding: 18px 14px 30px;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 12px;
      background: linear-gradient(145deg, rgba(53, 89, 127, 0.12), rgba(47, 105, 71, 0.1));
    }}
    h1 {{
      margin: 0 0 8px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.3rem, 3vw, 2rem);
    }}
    .hero p {{ margin: 4px 0; color: #4f5f5a; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }}
    .run-chip {{
      border: 1px solid #d5ccbb;
      border-radius: 999px;
      background: #fffef9;
      padding: 4px 9px;
      font-size: 0.8rem;
    }}
    .signal-chip {{
      border: 1px solid #d5ccbb;
      border-radius: 999px;
      background: #fffef9;
      padding: 4px 9px;
      font-size: 0.8rem;
    }}
    .signal-chip.type_i {{ border-color: #3d8a59; color: #245736; }}
    .signal-chip.type_ii {{ border-color: #b58d47; color: #6b4f20; }}
    .signal-chip.type_iii {{ border-color: #b95a53; color: #5e2926; }}
    .toolbar {{
      position: sticky;
      top: 8px;
      z-index: 6;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--card);
      padding: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .toolbar button, .toolbar select {{
      border: 1px solid #d5ccbb;
      border-radius: 8px;
      background: #fffef9;
      color: #2a3a37;
      padding: 6px 10px;
      font: inherit;
    }}
    .toolbar .primary {{
      background: #35597f;
      color: #fff;
      border-color: #35597f;
      font-weight: 700;
    }}
    .toolbar .danger {{
      background: #8a2d2b;
      color: #fff;
      border-color: #8a2d2b;
      font-weight: 700;
    }}
    .status {{
      margin-left: auto;
      font-size: 0.85rem;
      color: #4e5e58;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 10px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--card);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto auto auto auto;
    }}
    .card-head {{
      padding: 9px 10px;
      border-bottom: 1px solid #ebe4d4;
      background: #f7f2e6;
    }}
    .card-head h3 {{
      margin: 0 0 2px;
      font-size: 1rem;
    }}
    .card-head h3 span {{
      font-size: 0.82rem;
      color: #5d6d68;
      font-weight: 500;
      margin-left: 5px;
    }}
    .card-head p {{
      margin: 0;
      color: #5d6d68;
      font-size: 0.78rem;
    }}
    .signal-line {{
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .signal-badge {{
      border: 1px solid #d2cab9;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.72rem;
      font-weight: 700;
      background: #faf5e8;
      color: #385148;
    }}
    .signal-badge.type_i {{ border-color: #3d8a59; color: #245736; background: #e8f4eb; }}
    .signal-badge.type_ii {{ border-color: #b58d47; color: #6b4f20; background: #f8f0de; }}
    .signal-badge.type_iii {{ border-color: #b95a53; color: #5e2926; background: #f8e9e7; }}
    .images {{
      padding: 8px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 6px;
    }}
    figure {{
      margin: 0;
      border: 1px solid #e4dccb;
      border-radius: 8px;
      overflow: hidden;
      background: #f0eadb;
    }}
    figcaption {{
      padding: 4px 6px;
      font-size: 0.74rem;
      color: #586965;
      border-bottom: 1px solid #e4dccb;
      background: #faf6ec;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .img-btn {{
      width: 100%;
      border: 0;
      padding: 0;
      margin: 0;
      aspect-ratio: 1 / 1;
      cursor: zoom-in;
      background: #ece4d3;
    }}
    .img-btn img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .img-btn-label {{
      aspect-ratio: auto;
      background: #ece4d3;
    }}
    .img-btn-label img {{
      height: auto;
      object-fit: contain;
    }}
    .img-stack {{
      display: block;
      position: relative;
      width: 100%;
      line-height: 0;
    }}
    .ocr-overlay {{
      position: absolute;
      inset: 0;
      pointer-events: none;
    }}
    .ocr-box {{
      position: absolute;
      border: 2px solid rgba(225, 73, 62, 0.95);
      box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.65) inset;
    }}
    .ocr-box span {{
      position: absolute;
      top: -18px;
      left: -2px;
      background: rgba(225, 73, 62, 0.95);
      color: #fff;
      font-size: 0.66rem;
      line-height: 1;
      padding: 2px 4px;
      border-radius: 4px;
    }}
    .img-missing {{
      min-height: 110px;
      display: grid;
      place-items: center;
      color: #6c7a74;
      font-size: 0.78rem;
      padding: 8px;
      text-align: center;
    }}
    .meta {{
      padding: 8px 10px;
      border-top: 1px solid #ece4d3;
      border-bottom: 1px solid #ece4d3;
      display: grid;
      gap: 4px;
    }}
    .meta p {{
      margin: 0;
      font-size: 0.79rem;
      color: #4f5f5a;
    }}
    .meta code {{
      background: #f0ead9;
      padding: 1px 4px;
      border-radius: 4px;
    }}
    .form {{
      padding: 9px 10px 10px;
      display: grid;
      gap: 7px;
    }}
    label {{
      display: grid;
      gap: 4px;
      font-size: 0.78rem;
      color: #4f5f5a;
    }}
    input, select, textarea {{
      border: 1px solid #d7cebe;
      border-radius: 7px;
      background: #fffef9;
      color: #1f2b29;
      font: inherit;
      padding: 6px 8px;
    }}
    textarea {{ resize: vertical; min-height: 54px; }}
    .hidden {{ display: none !important; }}
    .lightbox {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(9, 12, 11, 0.85);
      z-index: 30;
      padding: 12px;
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-inner {{
      width: min(95vw, 1200px);
      max-height: 94vh;
      border: 1px solid rgba(255, 255, 255, 0.25);
      border-radius: 10px;
      overflow: hidden;
      background: #101312;
    }}
    .lightbox-main {{
      display: grid;
      place-items: center;
      max-height: 86vh;
      overflow: auto;
    }}
    .lightbox-main img {{
      max-width: 100%;
      max-height: 84vh;
      object-fit: contain;
      display: block;
    }}
    .lightbox-foot {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.2);
      color: #e5eeeb;
      font-size: 0.82rem;
      background: #171d1b;
    }}
    .lightbox-foot button {{
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 7px;
      background: transparent;
      color: #f3f8f6;
      font: inherit;
      padding: 5px 9px;
    }}
    @media (max-width: 900px) {{
      .images {{ grid-template-columns: 1fr; }}
      .status {{ width: 100%; margin-left: 0; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Hard Row Reviewer (OCR Recovery Queue)</h1>
      <p>Focused human labeling for difficult rows only. This page is generated from <code>{html_escape(str(queue_csv))}</code>.</p>
      <p>Total queue rows: <strong>{total_rows}</strong></p>
      <div class="chips">{run_badges}</div>
      <div class="chips">{signal_badges}</div>
      <p>Generated (UTC): <code>{html_escape(generated_at)}</code></p>
    </section>

    <section class="toolbar">
      <label>Run Date
        <select id="run-filter">
          <option value="all">All</option>
        </select>
      </label>
      <label>Signal Tier
        <select id="signal-filter">
          <option value="all">All</option>
          <option value="type_i">TYPE_I (OCR match)</option>
          <option value="type_ii">TYPE_II (weak OCR)</option>
          <option value="type_iii">TYPE_III (no signal)</option>
        </select>
      </label>
      <button id="next-pending">Jump To Next Pending</button>
      <button class="primary" id="export-reviewed">Export Reviewed CSV</button>
      <button class="danger" id="reset-local">Reset Local Edits</button>
      <span class="status" id="status-line">Pending: 0</span>
    </section>

    <section class="grid" id="card-grid">
      {card_html}
    </section>
  </main>

  <div class="lightbox" id="lightbox" aria-hidden="true">
    <div class="lightbox-inner" role="dialog" aria-modal="true" aria-label="Crop preview">
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
      const STORAGE_KEY = "hard_row_reviewer_v2";
      const rows = {rows_json};
      const rowById = {{}};
      rows.forEach((row, index) => {{
        row._rowId = `review-${{String(index + 1).padStart(3, "0")}}`;
        rowById[row._rowId] = row;
      }});

      const runFilter = document.getElementById("run-filter");
      const signalFilter = document.getElementById("signal-filter");
      const statusLine = document.getElementById("status-line");
      const grid = document.getElementById("card-grid");
      const nextPendingButton = document.getElementById("next-pending");
      const exportButton = document.getElementById("export-reviewed");
      const resetButton = document.getElementById("reset-local");
      const lightbox = document.getElementById("lightbox");
      const lightboxImage = document.getElementById("lightbox-image");
      const lightboxCaption = document.getElementById("lightbox-caption");
      const lightboxClose = document.getElementById("lightbox-close");

      const state = {{}};
      const savedRaw = localStorage.getItem(STORAGE_KEY);
      if (savedRaw) {{
        try {{
          const parsed = JSON.parse(savedRaw);
          Object.keys(parsed || {{}}).forEach((key) => {{
            state[key] = parsed[key];
          }});
        }} catch (err) {{
          console.warn("Unable to parse saved hard-row reviewer state", err);
        }}
      }}

      function writeStorage() {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }}

      function getRowState(rowId) {{
        const row = rowById[rowId];
        if (!row) return null;
        if (!state[rowId]) {{
          state[rowId] = {{
            verdict: "pending",
            confirmed_pot_id: row.suggested_pot_id || "",
            confirmed_variety_name: row.suggested_variety_name || "",
            notes: "",
          }};
        }}
        return state[rowId];
      }}

      function applyStateToInputs() {{
        document.querySelectorAll("[data-row-id]").forEach((el) => {{
          const rowId = el.getAttribute("data-row-id");
          const field = el.getAttribute("data-field");
          const rowState = getRowState(rowId);
          if (!rowState || !field) return;
          if (el.tagName === "SELECT" || el.tagName === "INPUT" || el.tagName === "TEXTAREA") {{
            el.value = rowState[field] ?? "";
          }}
        }});
      }}

      function refreshStatus() {{
        let pending = 0;
        let reviewed = 0;
        rows.forEach((row) => {{
          const rowState = getRowState(row._rowId);
          if (!rowState) return;
          if (rowState.verdict === "pending") pending += 1;
          else reviewed += 1;
        }});
        const visible = Array.from(grid.querySelectorAll(".card:not(.hidden)")).length;
        statusLine.textContent = `Visible: ${{visible}} | Reviewed: ${{reviewed}} | Pending: ${{pending}}`;
      }}

      function applyFilter() {{
        const selectedRun = runFilter.value || "all";
        const selectedSignal = signalFilter.value || "all";
        document.querySelectorAll(".card").forEach((card) => {{
          const runDate = card.getAttribute("data-run-date") || "";
          const signalTier = card.getAttribute("data-signal-tier") || "";
          const runMatch = selectedRun === "all" || runDate === selectedRun;
          const signalMatch = selectedSignal === "all" || signalTier === selectedSignal;
          const show = runMatch && signalMatch;
          card.classList.toggle("hidden", !show);
        }});
        refreshStatus();
      }}

      function initializeRunFilter() {{
        const runDates = Array.from(new Set(rows.map((row) => row.run_date))).sort();
        runDates.forEach((runDate) => {{
          const option = document.createElement("option");
          option.value = runDate;
          option.textContent = runDate;
          runFilter.appendChild(option);
        }});
        runFilter.addEventListener("change", applyFilter);
        signalFilter.addEventListener("change", applyFilter);
      }}

      function bindInputs() {{
        document.querySelectorAll("[data-field][data-row-id]").forEach((el) => {{
          el.addEventListener("input", () => {{
            const rowId = el.getAttribute("data-row-id");
            const field = el.getAttribute("data-field");
            const rowState = getRowState(rowId);
            if (!rowState || !field) return;
            rowState[field] = el.value;
            writeStorage();
            refreshStatus();
          }});
          if (el.tagName === "SELECT") {{
            el.addEventListener("change", () => {{
              const rowId = el.getAttribute("data-row-id");
              const field = el.getAttribute("data-field");
              const rowState = getRowState(rowId);
              if (!rowState || !field) return;
              rowState[field] = el.value;
              writeStorage();
              refreshStatus();
            }});
          }}
        }});
      }}

      function jumpToNextPending() {{
        const selectedRun = runFilter.value || "all";
        const selectedSignal = signalFilter.value || "all";
        const cards = Array.from(document.querySelectorAll(".card"));
        for (const card of cards) {{
          if (card.classList.contains("hidden")) continue;
          const runDate = card.getAttribute("data-run-date") || "";
          const signalTier = card.getAttribute("data-signal-tier") || "";
          if (selectedRun !== "all" && runDate !== selectedRun) continue;
          if (selectedSignal !== "all" && signalTier !== selectedSignal) continue;
          const rowId = card.getAttribute("data-row-id");
          const rowState = getRowState(rowId);
          if (rowState && rowState.verdict === "pending") {{
            card.scrollIntoView({{ behavior: "smooth", block: "start" }});
            return;
          }}
        }}
      }}

      function toCsvValue(value) {{
        const text = value == null ? "" : String(value);
        if (text.includes(",") || text.includes("\"") || text.includes("\\n")) {{
          return "\"" + text.replaceAll("\"", "\"\"") + "\"";
        }}
        return text;
      }}

      function buildReviewedRows() {{
        const out = [];
        rows.forEach((row) => {{
          const rowState = getRowState(row._rowId);
          if (!rowState) return;
          const changed =
            rowState.verdict !== "pending" ||
            (rowState.confirmed_pot_id || "") !== (row.suggested_pot_id || "") ||
            (rowState.confirmed_variety_name || "") !== (row.suggested_variety_name || "") ||
            Boolean((rowState.notes || "").trim());
          if (!changed) return;
          out.push({{
            run_date: row.run_date || "",
            row_index: row.row_index || "",
            source_asset_id: row.source_asset_id || "",
            suggested_pot_id: row.suggested_pot_id || "",
            suggested_variety_name: row.suggested_variety_name || "",
            confirmed_pot_id: rowState.confirmed_pot_id || "",
            confirmed_variety_name: rowState.confirmed_variety_name || "",
            verdict: rowState.verdict || "pending",
            notes: rowState.notes || "",
            signal_tier: row.signal_tier || "",
            signal_label: row.signal_label || "",
            matched_variant_count: row.matched_variant_count || "",
            ensemble_numbers_detected: row.ensemble_numbers_detected || "",
            photo_url: row.photo_url || "",
          }});
        }});
        return out;
      }}

      function exportReviewedCsv() {{
        const reviewed = buildReviewedRows();
        if (!reviewed.length) {{
          alert("No reviewed/changed rows yet.");
          return;
        }}
        const headers = Object.keys(reviewed[0]);
        const lines = [headers.join(",")];
        reviewed.forEach((row) => {{
          lines.push(headers.map((header) => toCsvValue(row[header])).join(","));
        }});
        const blob = new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv;charset=utf-8" }});
        const now = new Date().toISOString().replaceAll(":", "-");
        const name = `hard_row_review_${{now}}.csv`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }}

      function resetLocalState() {{
        if (!confirm("Reset all local edits for this page?")) return;
        localStorage.removeItem(STORAGE_KEY);
        location.reload();
      }}

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

      function bindLightbox() {{
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
      }}

      initializeRunFilter();
      applyStateToInputs();
      bindInputs();
      bindLightbox();
      applyFilter();

      nextPendingButton.addEventListener("click", jumpToNextPending);
      exportButton.addEventListener("click", exportReviewedCsv);
      resetButton.addEventListener("click", resetLocalState);
    }})();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build hard-row reviewer page from OCR recovery queue."
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/manual_label_queue.csv"),
        help="Manual queue CSV generated by OCR recovery experiment.",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
        help="Latest mapping CSV used for suggested variety names by pot.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("tracker/assets/hard-row-reviewer"),
        help="Directory for copied queue crop images (web-accessible).",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/hard-row-reviewer.html"),
        help="Output HTML path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    queue_rows: List[Dict[str, str]] = []
    if args.queue_csv.exists():
        queue_rows = read_csv_rows(args.queue_csv)

    variety_by_pot = load_latest_variety_by_pot(args.mapping_csv)
    assets_by_row = (
        copy_queue_images(queue_rows, args.assets_dir, args.output_html.parent)
        if queue_rows
        else {}
    )
    enriched_rows = build_enriched_rows(queue_rows, variety_by_pot, assets_by_row)
    summary = build_summary(enriched_rows)
    page = build_page(args.queue_csv, enriched_rows, summary)

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"queue_csv={args.queue_csv}")
    print(f"rows={len(queue_rows)}")
    print(f"assets_dir={args.assets_dir}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
