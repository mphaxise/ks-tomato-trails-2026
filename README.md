# 🍅 K's Tomato Trails 2026

_Former working name: Fog Tomato Trials (legacy reference only)._

**A citizen science project tracking which tomato varieties thrive in Sausalito's coastal fog belt.**

Sausalito sits in one of the Bay Area's most challenging microclimates for tomatoes — persistent summer fog, cool temperatures, and high humidity create conditions that most tomato varieties struggle with. This project systematically tests 12 varieties head-to-head to find the ones that actually produce.

---

## What This Is

A structured observation system for a backyard grower in Sausalito to:
- Track growth, health, and fruit production across 12 tomato varieties
- Identify which varieties succeed in low-heat, high-fog conditions
- Build a reusable data set future growers in similar microclimates can learn from

## Repository Structure

```
ks-tomato-trails-2026/
├── README.md               ← You are here
├── docs/
│   ├── STRATEGY.md         ← Overall project approach and goals
│   ├── VARIETIES.md        ← The 12 varieties being tested + fog-belt suitability profiles
│   ├── DATA_SCHEMA.md      ← What to measure, how often, and why
│   ├── CLIMATE_RESEARCH.md ← Fog-belt tomato science (why fog is hard, what helps)
│   ├── SUCCESS_METRICS.md  ← How we define "winner" at season's end
│   ├── V1-BASELINE-INTAKE.md ← Manual-link Google Photos baseline intake workflow
│   ├── GOOGLE-PHOTOS-PUBLIC-EXTRACTION.md ← Public-album metadata extraction workflow
│   └── NON-TOMATO-SPECIES-LOCAL-DB.md ← Separate local catalog for non-tomato photos
├── data/
│   ├── varieties.json      ← Machine-readable variety registry
│   ├── intake/             ← Manual/public intake files + labeled outputs
│   └── observations/       ← Weekly observation logs (CSV per variety)
├── scripts/
│   ├── google_photos_manual_intake.py ← V1 baseline intake normalizer
│   ├── extract_google_photos_public_album.py ← Public album metadata extractor
│   ├── extract_packet_crops.py ← Seed-packet crop extractor from album photos
│   ├── label_non_tomato_from_images.py ← OCR species labeler for mixed album photos
│   ├── merge_label_overrides.py ← Merge web editor corrections into canonical overrides
│   ├── build_experiment_trails_page.py ← Build view-only HTML catalog
│   ├── build_experiment_trails_label_editor_page.py ← Build editable correction HTML
│   └── non_tomato_species_catalog.py ← Separate non-tomato species cataloger
├── tests/                  ← Unit tests for extraction/labeling/merge/catalog scripts
├── logs/
│   └── README.md           ← Field notes and freeform observations
└── tracker/
    ├── experiment-trails-view.html ← View-only photo catalog
    ├── experiment-trails-label-editor.html ← Editable label workspace
    └── README.md
```

## Season Overview

| Parameter | Value |
|---|---|
| Location | Sausalito, CA (fog belt) |
| Varieties | 12 (see VARIETIES.md) |
| Season start | Spring 2026 (transplant after last frost) |
| Data collection | Weekly, May–October |
| Primary goal | Identify top 3 fog-belt performers |

## Quick Start

1. Read `docs/STRATEGY.md` for the overall plan
2. Register your 12 varieties in `data/varieties.json`
3. Set shared album URL in `data/intake/google_photos/album_url.txt`
4. Run baseline photo intake workflow in `docs/V1-BASELINE-INTAKE.md`
5. For public album extraction + OCR labeling, run:

```bash
python3 scripts/extract_google_photos_public_album.py --album-url "$(cat data/intake/google_photos/album_url.txt)"
python3 scripts/extract_packet_crops.py
python3 scripts/label_non_tomato_from_images.py \
  --mixed-csv data/intake/google_photos/manual_mixed_photos.csv \
  --output-csv data/intake/google_photos/manual_mixed_photos_labeled_v3.csv \
  --non-tomato-csv data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --overrides-csv data/intake/google_photos/manual_label_overrides_v1.csv
python3 scripts/build_experiment_trails_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```

6. Open:
  - `tracker/experiment-trails-view.html`
  - `tracker/experiment-trails-label-editor.html`
7. Start weekly logs in `data/observations/`
8. End-of-season scoring in `docs/SUCCESS_METRICS.md`

---

*Built with 🌫️ for growers where the fog never really lifts.*
