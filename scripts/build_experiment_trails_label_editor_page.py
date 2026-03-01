#!/usr/bin/env python3
"""Build an editable label-correction page for experiment trail photos."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


VARIETY_PROFILES: Dict[str, Dict[str, str]] = {
    "oakleaf lettuce (rouxai f1)": {
        "variety_name": "Oakleaf Lettuce (Rouxai F1)",
        "species_scientific_name": "Lactuca sativa",
        "specific_note": (
            "Deep cherry-red oakleaf with bright green inner contrast and good texture. "
            "Uniform plants hold quality across spring, summer, and fall harvest windows."
        ),
        "weather_hypothesis": (
            "In cool, foggy conditions with mild days and nights, this oakleaf type should stay tender and resist bolting longer than in hot inland areas. "
            "Expect good leaf quality even when other lettuce varieties might show stress."
        ),
        "expected_harvest_window": (
            "~ 6-10 weeks after planting, continuing into late spring and again in fall if succession sown."
        ),
    },
    "savoyed spinach (tundra f1 og)": {
        "variety_name": "Savoyed Spinach (Tundra F1 OG)",
        "species_scientific_name": "Spinacia oleracea",
        "specific_note": (
            "Organic semi-savoy spinach with glossy dark-green leaves and upright habit. "
            "Performs well in cool seasons and carries strong downy mildew resistance."
        ),
        "weather_hypothesis": (
            "The foggy Bay Area climate is ideal for spinach; expect vigorous growth with tender leaves. "
            "Downy mildew resistance will help maintain quality during damp periods."
        ),
        "expected_harvest_window": (
            "~ 45-60 days after sowing, with repeat cuttings possible into mild winter."
        ),
    },
    "bloomsdale spinach": {
        "variety_name": "Bloomsdale Spinach",
        "species_scientific_name": "Spinacia oleracea",
        "specific_note": (
            "Classic heirloom spinach with dark green, deeply savoyed leaves and rich flavor. "
            "Known for relatively slow bolting and dependable cool-season performance."
        ),
        "weather_hypothesis": (
            "Bloomsdale tends to thrive in cooler, fog-influenced climates with minimal heat, extending its harvest window relative to hotter regions."
        ),
        "expected_harvest_window": (
            "~ 40-50 days after sowing, potentially into early summer and again in fall."
        ),
    },
    "smooth leaf spinach (tadorna og)": {
        "variety_name": "Smooth Leaf Spinach (Tadorna OG)",
        "species_scientific_name": "Spinacia oleracea",
        "specific_note": (
            "Smooth-leaf spinach types are easier to wash and handle post-harvest than savoyed types. "
            "They are typically selected for a balance of flavor, clean leaves, and bolt tolerance."
        ),
        "weather_hypothesis": (
            "Expect steady, upright growth with tender leaves that are easy to clean and harvest; cool temperatures help maintain leaf sweetness."
        ),
        "expected_harvest_window": (
            "~ 45-60+ days after sowing, with multiple pickings possible."
        ),
    },
    "shelling pea (maxigol)": {
        "variety_name": "Shelling Pea (Maxigol)",
        "species_scientific_name": "Pisum sativum",
        "specific_note": (
            "Late shelling pea that keeps sweetness over a wider harvest window than many varieties. "
            "Productive vines set broad pods with plump peas and good flavor."
        ),
        "weather_hypothesis": (
            "Cooler spring and early summer conditions tend to preserve pea sweetness and slow down bolting, leading to longer harvest windows."
        ),
        "expected_harvest_window": (
            "~ 60-70 days after sowing, likely mid-late spring into early summer."
        ),
    },
    "collards (flash f1)": {
        "variety_name": "Collards (Flash F1)",
        "species_scientific_name": "Brassica oleracea (Acephala Group)",
        "specific_note": (
            "Vates-type hybrid collard with smooth dark-green leaves and very high yield potential. "
            "Notable for slow bolting and repeat harvest ability."
        ),
        "weather_hypothesis": (
            "Collards prefer cool weather and can handle mild winter chills; foggy coastal conditions should keep them producing strong foliage over an extended season."
        ),
        "expected_harvest_window": (
            "~ 55-75 days, with leaf harvests continuing through fall and mild winter."
        ),
    },
    "leek (tadorna og)": {
        "variety_name": "Leek (Tadorna OG)",
        "species_scientific_name": "Allium ampeloprasum var. porrum",
        "specific_note": (
            "Organic leek selected for dependable field performance and harvest around the 100-day class. "
            "Best quality comes from fertile soil and blanching methods that lengthen the edible shank."
        ),
        "weather_hypothesis": (
            "Mild temperatures and steady moisture favor steady leek growth; blanching later in the season should produce long, tender shanks."
        ),
        "expected_harvest_window": (
            "~ 90-120+ days, placing harvest in late fall into winter."
        ),
    },
    "kale (white russian og)": {
        "variety_name": "Kale (White Russian OG)",
        "species_scientific_name": "Brassica oleracea (Acephala Group)",
        "specific_note": (
            "Cold-tolerant kale with blue-green leaves and distinctive white ribs/petioles. "
            "Flavor improves after frost, making it strong for cool-season production."
        ),
        "weather_hypothesis": (
            "Foggy conditions enhance kale's texture and sweetness; expect robust winter growth with minimal bolting."
        ),
        "expected_harvest_window": (
            "~ 50-70 days, harvestable into winter."
        ),
    },
    "red cabbage (ruby perfection f1)": {
        "variety_name": "Red Cabbage (Ruby Perfection F1)",
        "species_scientific_name": "Brassica oleracea var. capitata",
        "specific_note": (
            "A proven mid-late red storage type with dense, uniform heads and good field holding. "
            "Commonly used for late summer to fall harvest and medium-term storage."
        ),
        "weather_hypothesis": (
            "Extended cool seasons help cabbage head formation; mild foggy climates reduce stress during head development."
        ),
        "expected_harvest_window": (
            "~ 85-100+ days, harvest late summer through fall."
        ),
    },
    "turnip (purple top white globe)": {
        "variety_name": "Turnip (Purple Top White Globe)",
        "species_scientific_name": "Brassica rapa subsp. rapa",
        "specific_note": (
            "Traditional heirloom turnip with smooth round roots: white below soil and purple above. "
            "Roots are mild and best at smaller size, and tops are suitable for cooked greens."
        ),
        "weather_hypothesis": (
            "Cool soils and gentle fog help keep roots sweet and tender, with greens remaining flavorful."
        ),
        "expected_harvest_window": (
            "~ 45-60 days, harvest into late spring/summer and again in fall if succession-sown."
        ),
    },
    "san francisco fog": {
        "variety_name": "San Francisco Fog",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Mid-season red heirloom bred for cool, overcast coastal conditions. "
            "Indeterminate plants set abundant clustered fruit with complex flavor for fresh use or canning."
        ),
        "weather_hypothesis": (
            "Particularly suited to foggy summer climates; sets fruit where heat-loving varieties may struggle."
        ),
        "expected_harvest_window": (
            "~ 65-80+ days from transplant, harvest mid-summer into fall."
        ),
    },
    "iles yellow latvian": {
        "variety_name": "Iles Yellow Latvian",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Likely aligned with TomatoFest's Yellow Latvian selection: yellow-orange fruit with balanced sweetness and meaty walls suited to sauce, salsa, and slicing in cooler regions."
        ),
        "weather_hypothesis": (
            "Cooler nights slow ripening, but sweetness accumulates over long mild days."
        ),
        "expected_harvest_window": (
            "~ 70-85 days, harvest late summer into fall."
        ),
    },
    "taxi": {
        "variety_name": "Taxi",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Early determinate yellow tomato producing meaty, round fruit with low-acid sweetness. "
            "Reliable in diverse climates, including hot/humid summers."
        ),
        "weather_hypothesis": (
            "Early yields are likely before peak fog returns; good for containers or sunny beds."
        ),
        "expected_harvest_window": (
            "~ 60-75 days, harvest early to mid-summer."
        ),
    },
    "nikolayev yellow cherry": {
        "variety_name": "Nikolayev Yellow Cherry",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Russian yellow cherry type producing heavy trusses of small bright fruit. "
            "Noted for good performance in cooler growing regions and steady production."
        ),
        "weather_hypothesis": (
            "Small fruit set readily even in cooler, foggy conditions; frequent trusses expected."
        ),
        "expected_harvest_window": (
            "~ 60-75 days, harvest summer into fall."
        ),
    },
    "japanese black trifele": {
        "variety_name": "Japanese Black Trifele",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Russian heirloom with distinctive pear-shaped mahogany fruit and meaty texture. "
            "Flavor is rich and complex, and fruit is known for good crack resistance."
        ),
        "weather_hypothesis": (
            "Likely to set fruit even without full heat; darker fruit may take longer to fully ripen in fog."
        ),
        "expected_harvest_window": (
            "~ 70-90 days, harvest late summer into fall."
        ),
    },
    "sunset's red horizon": {
        "variety_name": "Sunset's Red Horizon",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Southern Russian heirloom selected for very large, meaty red fruit and strong old-fashioned tomato flavor. "
            "Has shown long production and resilience in cooler coastal/short-season conditions."
        ),
        "weather_hypothesis": (
            "Resilient under mild conditions; plant where afternoon sun is strongest for best development."
        ),
        "expected_harvest_window": (
            "~ 75-95 days, late summer through fall."
        ),
    },
    "waimea wild cherry": {
        "variety_name": "Waimea Wild Cherry",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Very vigorous wild-cherry type producing large trusses of scarlet fruit. "
            "Fruit is bold, fruity, and excellent for snacking or salads."
        ),
        "weather_hypothesis": (
            "Vigorous growth suits cooler climates; heavy trusses expected even with fog returns."
        ),
        "expected_harvest_window": (
            "~ 60-80 days, harvest mid-summer into fall."
        ),
    },
    "sasha altai": {
        "variety_name": "Sasha Altai",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Early Russian heirloom valued for dependable set in cooler conditions and high elevations. "
            "Produces bright-red, slightly flattened fruit with notable balanced flavor."
        ),
        "weather_hypothesis": (
            "Performs well in mild weather; expect reliable fruit set even with limited heat."
        ),
        "expected_harvest_window": (
            "~ 65-80 days, harvest summer into fall."
        ),
    },
    "azoychka": {
        "variety_name": "Azoychka",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Productive Russian heirloom yielding yellow-orange meaty fruit with citrusy sweetness. "
            "Unlike many yellow tomatoes, it keeps a useful acid balance for complex flavor."
        ),
        "weather_hypothesis": (
            "Balanced acidity develops nicely with mild night temperatures."
        ),
        "expected_harvest_window": (
            "~ 65-80+ days, late summer through fall."
        ),
    },
    "heinz 9129": {
        "variety_name": "Heinz 9129",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Determinate Heinz-bred line developed for Eastern Canada/Northeast style conditions. "
            "Hearty plants set large crops of red round fruit suited to canning, sauce, and fresh use."
        ),
        "weather_hypothesis": (
            "Strong performance in cool climates; excellent for containers or rows with good sun exposure."
        ),
        "expected_harvest_window": (
            "~ 65-85 days, summer into fall."
        ),
    },
    "gold dust": {
        "variety_name": "Gold Dust",
        "species_scientific_name": "Solanum lycopersicum",
        "specific_note": (
            "Extra-early determinate type (University of New Hampshire lineage) with firm golden fruit. "
            "Valued for uniform ripening, crack resistance, and reliable early harvest."
        ),
        "weather_hypothesis": (
            "Particularly good for early summer harvest before fog thickens; consistent ripening expected."
        ),
        "expected_harvest_window": (
            "~ 55-70 days, early to mid-summer."
        ),
    },
}

VARIETY_ALIASES: Dict[str, str] = {
    "oakleaf lettuce (rouxai mto)": "oakleaf lettuce (rouxai f1)",
    "shelling pea (maxigolt)": "shelling pea (maxigol)",
    "walmea wild cherry": "waimea wild cherry",
    "sasha's altai": "sasha altai",
}


def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def normalize_key(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def resolve_variety_key(variety_name: str) -> str:
    key = normalize_key(variety_name)
    return VARIETY_ALIASES.get(key, key)


def get_variety_profile(variety_name: str) -> Dict[str, str]:
    return VARIETY_PROFILES.get(resolve_variety_key(variety_name), {})


def derive_variety_name(row: Dict[str, str]) -> str:
    caption = (row.get("caption") or "").strip()
    variety_name = caption.split("|", 1)[0].strip() if "|" in caption else (row.get("variety_name") or "").strip()
    profile = get_variety_profile(variety_name)
    return profile.get("variety_name", variety_name)


def derive_specific_note(row: Dict[str, str], variety_name: str) -> str:
    profile = get_variety_profile(variety_name)
    if profile.get("specific_note"):
        return profile["specific_note"]
    explicit = (row.get("specific_note") or "").strip()
    if explicit:
        return explicit
    return ""


def derive_scientific_name(row: Dict[str, str], variety_name: str) -> str:
    profile = get_variety_profile(variety_name)
    if profile.get("species_scientific_name"):
        return profile["species_scientific_name"]
    return (row.get("species_scientific_name") or "").strip()


def derive_weather_hypothesis(row: Dict[str, str], variety_name: str) -> str:
    profile = get_variety_profile(variety_name)
    if profile.get("weather_hypothesis"):
        return profile["weather_hypothesis"]
    return (row.get("weather_hypothesis") or "").strip()


def derive_expected_harvest_window(row: Dict[str, str], variety_name: str) -> str:
    profile = get_variety_profile(variety_name)
    if profile.get("expected_harvest_window"):
        return profile["expected_harvest_window"]
    return (row.get("expected_harvest_window") or "").strip()


def build_editor_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    editor_rows: List[Dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        variety_name = derive_variety_name(row)
        editor_rows.append(
            {
                "row_index": str(idx),
                "source_asset_id": (row.get("source_asset_id") or "").strip(),
                "photo_url": (row.get("photo_url") or "").strip(),
                "capture_date": (row.get("capture_date") or "").strip(),
                "classification_label": (row.get("classification_label") or "unknown").strip() or "unknown",
                "species_common_name": (row.get("species_common_name") or "").strip(),
                "variety_name": variety_name,
                "species_scientific_name": derive_scientific_name(row, variety_name),
                "specific_note": derive_specific_note(row, variety_name),
                "weather_hypothesis": derive_weather_hypothesis(row, variety_name),
                "expected_harvest_window": derive_expected_harvest_window(row, variety_name),
                "confidence": (row.get("confidence") or "").strip(),
                "labeling_method": (row.get("labeling_method") or "").strip(),
                "caption": (row.get("caption") or "").strip(),
                "final_status": (row.get("final_status") or "").strip(),
                "review_stage": (row.get("review_stage") or "").strip(),
                "resolution_source": (row.get("resolution_source") or "").strip(),
                "review_status_label": (row.get("review_status_label") or "").strip(),
                "context_id": (row.get("context_id") or "").strip(),
                "notes_append": "",
                "pot_tag": "",
                "packet_tag": "",
            }
        )
    return editor_rows


def build_page(rows: List[Dict[str, str]], source_csv: Path) -> str:
    now_iso = datetime.now(timezone.utc).isoformat()
    rows_json = json.dumps(build_editor_rows(rows), ensure_ascii=True)

    template = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>K's Experiment Trails - Label Editor</title>
  <style>
    :root {
      --bg: #f5f2e6;
      --card: #fffdf7;
      --ink: #1f2a28;
      --muted: #5f6d68;
      --line: #d7cfbe;
      --tomato: #8b2d2a;
      --leaf: #2f6c4a;
      --warn: #8d5f1f;
      --focus: #1f64a7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 400px at 110% -10%, #dfd8c4 0%, transparent 65%),
        radial-gradient(900px 400px at -10% 110%, #e7dcc5 0%, transparent 65%),
        linear-gradient(145deg, #f3f0e3, #ece5d4);
    }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 16px 14px 34px; }
    .hero {
      background: linear-gradient(120deg, rgba(47,108,74,0.12), rgba(139,45,42,0.08));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 10px;
    }
    h1 { margin: 0 0 4px; font-family: "Iowan Old Style", "Palatino Linotype", serif; font-size: clamp(1.2rem, 2.8vw, 2rem); }
    .sub { margin: 0; color: var(--muted); }
    .meta { margin-top: 8px; color: #4d5c57; font-size: 0.86rem; }

    .toolbar {
      position: sticky;
      top: 8px;
      z-index: 8;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 10px;
    }
    .toolbar input[type=\"search\"], .toolbar select {
      border: 1px solid #cdc5b4;
      border-radius: 8px;
      padding: 8px 10px;
      font: inherit;
      background: #fffef9;
      color: var(--ink);
    }
    .toolbar input[type=\"search\"] { flex: 1; min-width: 220px; }
    .btn {
      border: 1px solid #cbc3b1;
      background: #fffef9;
      color: #334743;
      border-radius: 999px;
      padding: 7px 11px;
      font: inherit;
      font-size: 0.82rem;
      cursor: pointer;
    }
    .btn.primary { background: #365f56; color: #fff; border-color: #365f56; }
    .btn.warn { background: #8a5d20; color: #fff; border-color: #8a5d20; }
    .stats { margin-left: auto; font-size: 0.84rem; color: #4a5b56; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 10px; }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      display: grid;
      grid-template-columns: 42% 58%;
      min-height: 230px;
    }
    .card.hidden { display: none; }
    .photo { background: #ebe5d7; min-height: 210px; }
    .photo.has-image { cursor: zoom-in; }
    .photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .photo .missing { height: 100%; display: grid; place-items: center; color: #6c7a74; font-size: 0.85rem; padding: 12px; }

    .form { padding: 10px; display: grid; gap: 7px; }
    .head { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; }
    .badge { border-radius: 999px; padding: 2px 7px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
    .badge.tomato { background: #f9e5e2; color: #7f2325; border: 1px solid #edc6bf; }
    .badge.non_tomato { background: #e6f3e9; color: #1d5c37; border: 1px solid #c9e3d0; }
    .badge.unknown { background: #faecd5; color: #764813; border: 1px solid #efce9b; }
    .dirty { font-size: 0.75rem; color: var(--warn); display: none; }
    .dirty.show { display: inline; }

    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
    .field { display: grid; gap: 3px; }
    .field.full { grid-column: 1 / -1; }
    label { font-size: 0.72rem; color: #5e6c67; text-transform: uppercase; letter-spacing: 0.05em; }
    input, textarea, select {
      width: 100%;
      border: 1px solid #cfc7b6;
      border-radius: 7px;
      background: #fffef9;
      color: var(--ink);
      font: inherit;
      padding: 6px 8px;
    }
    input:focus, textarea:focus, select:focus {
      outline: 2px solid var(--focus);
      outline-offset: 1px;
      border-color: var(--focus);
    }
    textarea { min-height: 50px; resize: vertical; }
    .note { font-size: 0.75rem; color: #667670; }

    .lightbox {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 18px;
      background: rgba(9, 13, 12, 0.86);
      z-index: 40;
    }
    .lightbox.open { display: flex; }
    .lightbox-inner {
      position: relative;
      width: min(96vw, 1680px);
      height: min(94vh, 940px);
      max-height: 94vh;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      gap: 10px;
    }
    .lightbox-panel {
      display: grid;
      grid-template-columns: minmax(420px, 58%) minmax(320px, 42%);
      background: var(--card);
      border: 1px solid #d8cfbb;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 20px 46px rgba(0, 0, 0, 0.44);
      min-height: 0;
      height: 100%;
    }
    .lightbox-photo {
      background: #111312;
      display: grid;
      place-items: center;
      min-height: 0;
      padding: 8px;
    }
    .lightbox-img {
      width: 100%;
      height: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
    }
    .lightbox-form {
      max-height: none;
      min-height: 0;
      height: 100%;
      overflow: auto;
      padding: 12px;
      background: #fffdf7;
      display: grid;
      gap: 7px;
      align-content: start;
    }
    .lightbox-nav {
      margin-top: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    .lightbox-nav-btn {
      border: 1px solid #d7cfbe;
      border-radius: 999px;
      background: #f7f4ec;
      color: #1f2a28;
      font: inherit;
      font-size: 0.84rem;
      padding: 7px 12px;
      cursor: pointer;
    }
    .lightbox-nav-btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .lightbox-nav-status {
      color: #f5f3ea;
      font-size: 0.86rem;
      min-width: 120px;
      text-align: center;
    }
    .lightbox-close {
      position: absolute;
      top: -10px;
      right: -10px;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      border: 1px solid #f0e9d7;
      background: #183b33;
      color: #ffffff;
      font-size: 1.2rem;
      line-height: 1;
      cursor: pointer;
    }

    @media (max-width: 920px) {
      .card { grid-template-columns: 1fr; }
      .photo { max-height: 240px; }
      .toolbar { position: static; }
      .lightbox { padding: 10px; }
      .lightbox-inner { height: min(94vh, 760px); }
      .lightbox-panel {
        grid-template-columns: 1fr;
        grid-template-rows: minmax(0, 1fr) auto;
      }
      .lightbox-photo { min-height: 0; }
      .lightbox-img {
        height: auto;
        max-height: min(50vh, 420px);
      }
      .lightbox-form {
        height: auto;
        max-height: min(38vh, 320px);
      }
      .lightbox-nav { margin-top: 8px; }
      .lightbox-nav-btn { padding: 7px 10px; font-size: 0.8rem; }
      .lightbox-nav-status { min-width: 100px; font-size: 0.82rem; }
      .lightbox-close {
        top: 8px;
        right: 8px;
      }
    }
  </style>
</head>
<body>
  <main class=\"wrap\">
    <header class=\"hero\">
      <h1>K's Experiment Trails 2026: Editable Label Corrections</h1>
      <p class=\"sub\">Edit plant identification directly next to each photo, then export corrections CSV.</p>
      <div class=\"meta\">Generated (UTC): <strong>__NOW__</strong> | Source: <strong>__SOURCE__</strong></div>
    </header>

    <div class=\"toolbar\">
      <input id=\"search\" type=\"search\" placeholder=\"Search species, caption, asset, or row number...\" />
      <select id=\"filter\" aria-label=\"Label filter\">
        <option value=\"all\">All Labels</option>
        <option value=\"tomato\">Tomato</option>
        <option value=\"non_tomato\">Non-Tomato</option>
        <option value=\"unknown\">Needs Review</option>
      </select>
      <button id=\"saveLocal\" class=\"btn\">Save in Browser</button>
      <button id=\"loadLocal\" class=\"btn\">Load Saved</button>
      <button id=\"resetLocal\" class=\"btn warn\">Reset Saved</button>
      <button id=\"exportCsv\" class=\"btn primary\">Download Corrections CSV</button>
      <div class=\"stats\">Visible: <strong id=\"visibleCount\">0</strong> | Changed: <strong id=\"changedCount\">0</strong></div>
    </div>

    <section class=\"note\" style=\"margin:0 0 10px; padding:10px 12px; border:1px solid var(--line); border-radius:10px; background:var(--card);\">
      Canonical defaults are prefilled for <strong>Variety</strong>, <strong>Scientific Name</strong>, <strong>Specific Note</strong>, <strong>Weather Hypothesis</strong>, and <strong>Expected Harvest Window</strong>. Pot number info is useful too. <strong>Pot Tag</strong> and <strong>Packet Tag</strong> are exported in <code>notes_append</code> for mapping and inference.
      <details style=\"margin-top:8px;\">
        <summary style=\"cursor:pointer; color:#3d4f49; font-weight:600;\">General Bay Area weather notes</summary>
        <ul style=\"margin:8px 0 0 16px; padding:0;\">
          <li>Foggy, cool coastal climate is strongest for cool-season greens, brassicas, and peas; tomatoes benefit most from maximized sun exposure.</li>
          <li>Mild winters can extend harvest windows for many cool-season crops and support long fall production.</li>
          <li>Heat stress is usually lower than inland zones, so bolting and bitterness are often reduced.</li>
        </ul>
      </details>
    </section>

    <div id=\"cards\" class=\"grid\"></div>
  </main>
  <div id=\"lightbox\" class=\"lightbox\" aria-hidden=\"true\" role=\"dialog\" aria-modal=\"true\" aria-label=\"Full photo preview\">
    <div class=\"lightbox-inner\">
      <button id=\"lightboxClose\" class=\"lightbox-close\" type=\"button\" aria-label=\"Close full photo\">&times;</button>
      <div class=\"lightbox-panel\">
        <div class=\"lightbox-photo\">
          <img id=\"lightboxImg\" class=\"lightbox-img\" src=\"\" alt=\"\" />
        </div>
        <div id=\"lightboxForm\" class=\"lightbox-form\"></div>
      </div>
      <div class=\"lightbox-nav\" aria-label=\"Photo navigation\">
        <button id=\"lightboxPrev\" class=\"lightbox-nav-btn\" type=\"button\" aria-label=\"Previous photo\">&larr; Previous</button>
        <div id=\"lightboxNavStatus\" class=\"lightbox-nav-status\"></div>
        <button id=\"lightboxNext\" class=\"lightbox-nav-btn\" type=\"button\" aria-label=\"Next photo\">Next &rarr;</button>
      </div>
    </div>
  </div>

  <script>
    (() => {
      const STORAGE_KEY = "tomato_trails_label_editor_v1";
      const INITIAL_ROWS = __ROWS_JSON__;
      let rows = INITIAL_ROWS.map((row) => ({ ...row }));

      const cardsHost = document.getElementById("cards");
      const searchInput = document.getElementById("search");
      const filterSelect = document.getElementById("filter");
      const visibleCount = document.getElementById("visibleCount");
      const changedCount = document.getElementById("changedCount");
      const lightbox = document.getElementById("lightbox");
      const lightboxClose = document.getElementById("lightboxClose");
      const lightboxImg = document.getElementById("lightboxImg");
      const lightboxForm = document.getElementById("lightboxForm");
      const lightboxPrev = document.getElementById("lightboxPrev");
      const lightboxNext = document.getElementById("lightboxNext");
      const lightboxNavStatus = document.getElementById("lightboxNavStatus");
      let lightboxRowIndex = null;

      const editKeys = [
        "classification_label",
        "species_common_name",
        "variety_name",
        "species_scientific_name",
        "specific_note",
        "weather_hypothesis",
        "expected_harvest_window",
        "confidence",
        "labeling_method",
        "caption",
        "notes_append",
        "pot_tag",
        "packet_tag",
      ];

      const esc = (value) => String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");

      const labelTitle = (value) => {
        if (value === "tomato") return "Tomato";
        if (value === "non_tomato") return "Non-Tomato";
        return "Needs Review";
      };

      const isRowChanged = (row) => {
        const original = INITIAL_ROWS[Number(row.row_index) - 1];
        return editKeys.some((key) => (row[key] || "") !== (original[key] || ""));
      };

      const updateDirtyBadge = (card, row) => {
        const dirty = card.querySelector(".dirty");
        if (!dirty) return;
        dirty.classList.toggle("show", isRowChanged(row));
      };

      const updateChangedCount = () => {
        const changed = rows.filter(isRowChanged).length;
        changedCount.textContent = String(changed);
      };

      const getNavigableRowIndices = () => {
        const visible = Array.from(cardsHost.querySelectorAll(".card:not(.hidden)"))
          .map((card) => Number(card.dataset.rowIndex))
          .filter((rowIndex) => Boolean((rows[rowIndex - 1]?.photo_url || "").trim()));
        if (visible.length > 0) return visible;
        return rows
          .filter((row) => Boolean((row.photo_url || "").trim()))
          .map((row) => Number(row.row_index));
      };

      const updateLightboxNav = () => {
        if (!lightbox.classList.contains("open") || lightboxRowIndex === null) return;
        const indices = getNavigableRowIndices();
        const position = indices.indexOf(Number(lightboxRowIndex));
        lightboxPrev.disabled = position <= 0;
        lightboxNext.disabled = position < 0 || position >= indices.length - 1;
        lightboxNavStatus.textContent = position >= 0
          ? `Image ${position + 1} of ${indices.length}`
          : `${indices.length} images`;
      };

      const syncMainCardField = (row, key, value) => {
        const card = cardsHost.querySelector(`.card[data-row-index="${row.row_index}"]`);
        const field = card?.querySelector(`[data-key="${key}"]`);
        if (!field) {
          row[key] = value;
          updateChangedCount();
          applyFilters();
          return;
        }
        if (field.value !== value) field.value = value;
        field.dispatchEvent(new Event("input", { bubbles: true }));
      };

      const renderLightboxForm = (row) => `
        <div class=\"head\">
          <span class=\"badge ${esc(row.classification_label || "unknown")}\" data-lightbox-badge>${esc(labelTitle(row.classification_label))}</span>
          <strong>Row ${esc(row.row_index)}</strong>
          <span class=\"note\">${esc(row.capture_date || "")}</span>
          <span class=\"note\">${esc((row.source_asset_id || "").slice(0, 12))}...</span>
          <span class=\"dirty${isRowChanged(row) ? " show" : ""}\" data-lightbox-dirty>edited</span>
        </div>
        <div class=\"row\">
          <div class=\"field\">
            <label>Classification</label>
            <select data-lightbox-key=\"classification_label\">
              <option value=\"tomato\" ${row.classification_label === "tomato" ? "selected" : ""}>tomato</option>
              <option value=\"non_tomato\" ${row.classification_label === "non_tomato" ? "selected" : ""}>non_tomato</option>
              <option value=\"unknown\" ${row.classification_label === "unknown" ? "selected" : ""}>unknown</option>
            </select>
          </div>
          <div class=\"field\">
            <label>Confidence (0-1)</label>
            <input data-lightbox-key=\"confidence\" value=\"${esc(row.confidence)}\" placeholder=\"0.99\" />
          </div>
        </div>
        <div class=\"row\">
          <div class=\"field\">
            <label>Common Name</label>
            <input data-lightbox-key=\"species_common_name\" value=\"${esc(row.species_common_name)}\" />
          </div>
          <div class=\"field\">
            <label>Variety</label>
            <input data-lightbox-key=\"variety_name\" value=\"${esc(row.variety_name)}\" placeholder=\"e.g. Bloomsdale Long Standing\" />
          </div>
        </div>
        <div class=\"field full\">
          <label>Scientific Name</label>
          <input data-lightbox-key=\"species_scientific_name\" value=\"${esc(row.species_scientific_name)}\" />
        </div>
        <div class=\"field full\">
          <label>Specific Note</label>
          <textarea data-lightbox-key=\"specific_note\" placeholder=\"what is distinctive about this type\">${esc(row.specific_note)}</textarea>
        </div>
        <div class=\"field full\">
          <label>Weather Hypothesis (Sausalito)</label>
          <textarea data-lightbox-key=\"weather_hypothesis\" placeholder=\"how this variety may perform in Sausalito microclimate\">${esc(row.weather_hypothesis)}</textarea>
        </div>
        <div class=\"field full\">
          <label>Expected Harvest Window</label>
          <input data-lightbox-key=\"expected_harvest_window\" value=\"${esc(row.expected_harvest_window)}\" placeholder=\"~ 60-75 days, harvest early to mid-summer\" />
        </div>
        <div class=\"row\">
          <div class=\"field\">
            <label>Pot Tag (optional)</label>
            <input data-lightbox-key=\"pot_tag\" value=\"${esc(row.pot_tag)}\" placeholder=\"e.g. 7\" />
          </div>
          <div class=\"field\">
            <label>Packet Tag (optional)</label>
            <input data-lightbox-key=\"packet_tag\" value=\"${esc(row.packet_tag)}\" placeholder=\"e.g. 7\" />
          </div>
        </div>
        <div class=\"field full\">
          <label>Caption</label>
          <input data-lightbox-key=\"caption\" value=\"${esc(row.caption)}\" />
        </div>
        <div class=\"field full\">
          <label>Labeling Method</label>
          <input data-lightbox-key=\"labeling_method\" value=\"${esc(row.labeling_method)}\" placeholder=\"manual_packet_label\" />
        </div>
        <div class=\"field full\">
          <label>Notes Append</label>
          <textarea data-lightbox-key=\"notes_append\" placeholder=\"extra notes for this correction\">${esc(row.notes_append)}</textarea>
        </div>
      `;

      const refreshLightboxMeta = (row) => {
        const badge = lightboxForm.querySelector("[data-lightbox-badge]");
        if (badge) {
          badge.textContent = labelTitle(row.classification_label);
          badge.className = `badge ${row.classification_label}`;
        }
        const dirty = lightboxForm.querySelector("[data-lightbox-dirty]");
        if (dirty) dirty.classList.toggle("show", isRowChanged(row));
      };

      const wireLightboxForm = (row) => {
        lightboxForm.querySelectorAll("[data-lightbox-key]").forEach((input) => {
          input.addEventListener("input", () => {
            const key = input.dataset.lightboxKey;
            syncMainCardField(row, key, input.value);
            refreshLightboxMeta(row);
          });
        });
      };

      const openLightbox = (row) => {
        if (!row.photo_url) return;
        lightboxRowIndex = Number(row.row_index);
        const altText = row.species_common_name || row.caption || "plant photo";
        lightboxImg.src = row.photo_url;
        lightboxImg.alt = altText;
        lightboxForm.innerHTML = renderLightboxForm(row);
        wireLightboxForm(row);
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        updateLightboxNav();
      };

      const moveLightbox = (delta) => {
        if (!lightbox.classList.contains("open") || lightboxRowIndex === null) return;
        const indices = getNavigableRowIndices();
        const currentPosition = indices.indexOf(Number(lightboxRowIndex));
        if (currentPosition < 0) return;
        const targetPosition = currentPosition + delta;
        if (targetPosition < 0 || targetPosition >= indices.length) return;
        const targetRow = rows[indices[targetPosition] - 1];
        if (!targetRow) return;
        openLightbox(targetRow);
      };

      const closeLightbox = () => {
        if (!lightbox.classList.contains("open")) return;
        lightbox.classList.remove("open");
        lightbox.setAttribute("aria-hidden", "true");
        lightboxImg.removeAttribute("src");
        lightboxImg.alt = "";
        lightboxForm.innerHTML = "";
        lightboxNavStatus.textContent = "";
        lightboxRowIndex = null;
        document.body.style.overflow = "";
      };

      const createCard = (row) => {
        const card = document.createElement("article");
        card.className = "card";
        card.dataset.rowIndex = row.row_index;

        const badgeClass = esc(row.classification_label || "unknown");
        const photo = row.photo_url
          ? `<img src=\"${esc(row.photo_url)}\" alt=\"${esc(row.species_common_name || "plant photo")}\" loading=\"lazy\" />`
          : `<div class=\"missing\">No photo URL</div>`;

        card.innerHTML = `
          <div class=\"photo\">${photo}</div>
          <div class=\"form\">
            <div class=\"head\">
              <span class=\"badge ${badgeClass}\">${esc(labelTitle(row.classification_label))}</span>
              <strong>Row ${esc(row.row_index)}</strong>
              <span class=\"note\">${esc(row.capture_date || "")}</span>
              <span class=\"note\">${esc((row.source_asset_id || "").slice(0, 12))}...</span>
              <span class=\"dirty\">edited</span>
            </div>
            <div class=\"row\">
              <div class=\"field\">
                <label>Classification</label>
                <select data-key=\"classification_label\">
                  <option value=\"tomato\" ${row.classification_label === "tomato" ? "selected" : ""}>tomato</option>
                  <option value=\"non_tomato\" ${row.classification_label === "non_tomato" ? "selected" : ""}>non_tomato</option>
                  <option value=\"unknown\" ${row.classification_label === "unknown" ? "selected" : ""}>unknown</option>
                </select>
              </div>
              <div class=\"field\">
                <label>Confidence (0-1)</label>
                <input data-key=\"confidence\" value=\"${esc(row.confidence)}\" placeholder=\"0.99\" />
              </div>
            </div>
            <div class=\"row\">
              <div class=\"field\">
                <label>Common Name</label>
                <input data-key=\"species_common_name\" value=\"${esc(row.species_common_name)}\" />
              </div>
              <div class=\"field\">
                <label>Variety</label>
                <input data-key=\"variety_name\" value=\"${esc(row.variety_name)}\" placeholder=\"e.g. Bloomsdale Long Standing\" />
              </div>
            </div>
            <div class=\"field full\">
              <label>Scientific Name</label>
              <input data-key=\"species_scientific_name\" value=\"${esc(row.species_scientific_name)}\" />
            </div>
            <div class=\"field full\">
              <label>Specific Note</label>
              <textarea data-key=\"specific_note\" placeholder=\"what is distinctive about this type\">${esc(row.specific_note)}</textarea>
            </div>
            <div class=\"field full\">
              <label>Weather Hypothesis (Sausalito)</label>
              <textarea data-key=\"weather_hypothesis\" placeholder=\"how this variety may perform in Sausalito microclimate\">${esc(row.weather_hypothesis)}</textarea>
            </div>
            <div class=\"field full\">
              <label>Expected Harvest Window</label>
              <input data-key=\"expected_harvest_window\" value=\"${esc(row.expected_harvest_window)}\" placeholder=\"~ 60-75 days, harvest early to mid-summer\" />
            </div>
            <div class=\"row\">
              <div class=\"field\">
                <label>Pot Tag (optional)</label>
                <input data-key=\"pot_tag\" value=\"${esc(row.pot_tag)}\" placeholder=\"e.g. 7\" />
              </div>
              <div class=\"field\">
                <label>Packet Tag (optional)</label>
                <input data-key=\"packet_tag\" value=\"${esc(row.packet_tag)}\" placeholder=\"e.g. 7\" />
              </div>
            </div>
            <div class=\"field full\">
              <label>Caption</label>
              <input data-key=\"caption\" value=\"${esc(row.caption)}\" />
            </div>
            <div class=\"field full\">
              <label>Labeling Method</label>
              <input data-key=\"labeling_method\" value=\"${esc(row.labeling_method)}\" placeholder=\"manual_packet_label\" />
            </div>
            <div class=\"field full\">
              <label>Notes Append</label>
              <textarea data-key=\"notes_append\" placeholder=\"extra notes for this correction\">${esc(row.notes_append)}</textarea>
            </div>
          </div>
        `;

        const photoWrap = card.querySelector(".photo");
        if (row.photo_url && photoWrap) {
          photoWrap.classList.add("has-image");
          photoWrap.tabIndex = 0;
          photoWrap.setAttribute("role", "button");
          photoWrap.setAttribute("aria-label", `Open full photo for row ${row.row_index}`);
          const openPhoto = () => {
            openLightbox(row);
          };
          photoWrap.addEventListener("click", openPhoto);
          photoWrap.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              openPhoto();
            }
          });
        }

        card.querySelectorAll("[data-key]").forEach((input) => {
          input.addEventListener("input", () => {
            const key = input.dataset.key;
            row[key] = input.value;
            if (key === "classification_label") {
              const badge = card.querySelector(".badge");
              badge.textContent = labelTitle(input.value);
              badge.className = `badge ${input.value}`;
            }
            updateDirtyBadge(card, row);
            updateChangedCount();
            applyFilters();
          });
        });

        updateDirtyBadge(card, row);
        return card;
      };

      const renderCards = () => {
        cardsHost.innerHTML = "";
        rows.forEach((row) => cardsHost.appendChild(createCard(row)));
        applyFilters();
        updateChangedCount();
      };

      const applyFilters = () => {
        const query = (searchInput.value || "").trim().toLowerCase();
        const label = filterSelect.value;
        let visible = 0;

        cardsHost.querySelectorAll(".card").forEach((card) => {
          const index = Number(card.dataset.rowIndex) - 1;
          const row = rows[index];
          const matchesLabel = label === "all" || row.classification_label === label;
          const haystack = [
            row.row_index,
            row.source_asset_id,
            row.species_common_name,
            row.variety_name,
            row.species_scientific_name,
            row.specific_note,
            row.weather_hypothesis,
            row.expected_harvest_window,
            row.caption,
            row.labeling_method,
            row.pot_tag,
            row.packet_tag,
          ]
            .join(" ")
            .toLowerCase();
          const matchesSearch = !query || haystack.includes(query);
          const show = matchesLabel && matchesSearch;
          card.classList.toggle("hidden", !show);
          if (show) visible += 1;
        });

        visibleCount.textContent = String(visible);
        if (lightbox.classList.contains("open")) updateLightboxNav();
      };

      const saveLocal = () => {
        const rowsByAsset = {};
        const rowsByIndex = {};
        rows.forEach((row) => {
          const rowIndex = String(row.row_index || "").trim();
          const assetId = String(row.source_asset_id || "").trim();
          if (rowIndex) rowsByIndex[rowIndex] = row;
          if (assetId) rowsByAsset[assetId] = row;
        });
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            version: 2,
            rows_by_asset: rowsByAsset,
            rows_by_index: rowsByIndex,
          })
        );
      };

      const loadLocal = () => {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        try {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed)) {
            if (parsed.length !== INITIAL_ROWS.length) return;
            rows = parsed.map((row, index) => {
              const base = INITIAL_ROWS[index];
              return { ...base, ...row };
            });
            return;
          }
          if (!parsed || typeof parsed !== "object") return;
          const rowsByAsset = parsed.rows_by_asset && typeof parsed.rows_by_asset === "object"
            ? parsed.rows_by_asset
            : {};
          const rowsByIndex = parsed.rows_by_index && typeof parsed.rows_by_index === "object"
            ? parsed.rows_by_index
            : {};
          rows = INITIAL_ROWS.map((base) => {
            const rowIndex = String(base.row_index || "").trim();
            const assetId = String(base.source_asset_id || "").trim();
            const byAsset = assetId ? rowsByAsset[assetId] : null;
            if (byAsset && typeof byAsset === "object") return { ...base, ...byAsset };
            const byIndex = rowIndex ? rowsByIndex[rowIndex] : null;
            if (byIndex && typeof byIndex === "object") return { ...base, ...byIndex };
            return { ...base };
          });
        } catch (_err) {
          return;
        }
      };

      const resetLocal = () => {
        localStorage.removeItem(STORAGE_KEY);
        rows = INITIAL_ROWS.map((row) => ({ ...row }));
        renderCards();
      };

      const toCsv = (records, columns) => {
        const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
        const lines = [columns.join(",")];
        records.forEach((record) => {
          lines.push(columns.map((col) => quote(record[col] || "")).join(","));
        });
        return lines.join("\\n");
      };

      const downloadText = (filename, content) => {
        const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      };

      const exportCorrections = () => {
        const changed = rows.filter(isRowChanged).map((row) => {
          const noteParts = [];
          if ((row.notes_append || "").trim()) noteParts.push((row.notes_append || "").trim());
          if ((row.variety_name || "").trim()) noteParts.push(`variety_name=${(row.variety_name || "").trim()}`);
          if ((row.specific_note || "").trim()) noteParts.push(`specific_note=${(row.specific_note || "").trim()}`);
          if ((row.weather_hypothesis || "").trim()) noteParts.push(`weather_hypothesis=${(row.weather_hypothesis || "").trim()}`);
          if ((row.expected_harvest_window || "").trim()) noteParts.push(`expected_harvest_window=${(row.expected_harvest_window || "").trim()}`);
          if ((row.pot_tag || "").trim()) noteParts.push(`pot_tag=${(row.pot_tag || "").trim()}`);
          if ((row.packet_tag || "").trim()) noteParts.push(`packet_tag=${(row.packet_tag || "").trim()}`);
          const notesAppend = noteParts.join("; ");

          return {
            row_index: row.row_index,
            source_asset_id: row.source_asset_id,
            classification_label: row.classification_label,
            species_common_name: row.species_common_name,
            variety_name: row.variety_name,
            species_scientific_name: row.species_scientific_name,
            specific_note: row.specific_note,
            weather_hypothesis: row.weather_hypothesis,
            expected_harvest_window: row.expected_harvest_window,
            confidence: row.confidence,
            labeling_method: row.labeling_method || "manual_web_edit",
            caption: row.caption,
            notes_append: notesAppend,
            ocr_excerpt: "",
          };
        });

        const csv = toCsv(changed, [
          "row_index",
          "source_asset_id",
          "classification_label",
          "species_common_name",
          "variety_name",
          "species_scientific_name",
          "specific_note",
          "weather_hypothesis",
          "expected_harvest_window",
          "confidence",
          "labeling_method",
          "caption",
          "notes_append",
          "ocr_excerpt",
        ]);

        const stamp = new Date().toISOString().slice(0, 19).replaceAll(":", "-");
        downloadText(`manual_label_overrides_web_${stamp}.csv`, csv);
      };

      searchInput.addEventListener("input", applyFilters);
      filterSelect.addEventListener("change", applyFilters);
      lightboxClose.addEventListener("click", closeLightbox);
      lightboxPrev.addEventListener("click", () => moveLightbox(-1));
      lightboxNext.addEventListener("click", () => moveLightbox(1));
      lightbox.addEventListener("click", (event) => {
        if (event.target === lightbox) closeLightbox();
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeLightbox();
          return;
        }
        if (!lightbox.classList.contains("open")) return;
        const target = event.target;
        const typingContext = target instanceof HTMLElement
          && (target.matches("input, textarea, select") || target.isContentEditable);
        if (typingContext) return;
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          moveLightbox(-1);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          moveLightbox(1);
        }
      });
      document.getElementById("saveLocal").addEventListener("click", saveLocal);
      document.getElementById("loadLocal").addEventListener("click", () => {
        loadLocal();
        renderCards();
      });
      document.getElementById("resetLocal").addEventListener("click", resetLocal);
      document.getElementById("exportCsv").addEventListener("click", exportCorrections);

      loadLocal();
      renderCards();
    })();
  </script>
</body>
</html>
"""

    return (
        template.replace("__ROWS_JSON__", rows_json)
        .replace("__NOW__", html_escape(now_iso))
        .replace("__SOURCE__", html_escape(str(source_csv)))
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an editable label-correction web page for experiment trails photos."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Input labeled CSV",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/experiment-trails-label-editor.html"),
        help="Output editor HTML page",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.input_csv)
    page = build_page(rows, args.input_csv)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page, encoding="utf-8")

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
