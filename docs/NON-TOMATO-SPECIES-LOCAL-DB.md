# Non-Tomato Species Local DB

Updated: 2026-02-27

## Purpose

Catalog non-tomato photos in a separate local database, outside Tomato Trails baseline records.

## Input file

- `data/intake/google_photos/manual_mixed_photos.csv` (live file)
- `data/intake/google_photos/manual_mixed_photos_sample.csv` (demo)

Required fields per row:
- `photo_url` (or `source_url`)
- `caption`
- `capture_date` (or `captured_at` / `uploaded_at`)

## Run

```bash
# 1) Extract packet crops from downloaded images
python3 scripts/extract_packet_crops.py

# 2) Label rows using OCR from packet crops
python3 scripts/label_non_tomato_from_images.py

# Optional: apply/maintain manual per-row overrides from verified packet photos
# default file:
# data/intake/google_photos/manual_label_overrides_v1.csv

# 3) Persist only non-tomato labeled rows to local DB
python3 scripts/non_tomato_species_catalog.py \
  --input data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --db-path local/non_tomato_species/non_tomato_species.db
```

## Behavior

- Tomato photos are filtered out using:
  - explicit `classification_label=tomato` rows
  - caption tomato keyword match
  - known tomato variety IDs/names from `data/varieties.json` when caption includes variety
- Non-tomato rows are labeled as `classification_label=non_tomato`.
- Species is inferred from caption/notes keywords (for example: marigold, basil, pepper, cucumber).
- Unknown species is stored as `species_common_name=unknown` with low confidence for manual follow-up.
- If curated fields are present in the input CSV, the catalog preserves them:
  - `species_common_name`
  - `variety_name`
  - `species_scientific_name`
  - `specific_note`
  - `weather_hypothesis`
  - `expected_harvest_window`
  - `confidence`
  - `labeling_method`

OCR labeling outputs:
- `data/intake/google_photos/manual_mixed_photos_labeled.csv` (all rows with OCR labels)
- `data/intake/google_photos/manual_non_tomato_labeled.csv` (only non-tomato rows)
- `data/intake/google_photos/manual_label_overrides_v1.csv` (manual verified packet-label overrides)
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv` (current validated run)
- `data/intake/google_photos/manual_non_tomato_labeled_v3.csv` (current validated run)

## Local DB Schema Notes

SQLite table: `non_tomato_observations`

Core identity and traceability:
- `record_hash` (unique upsert key)
- `source_platform`, `source_url`, `source_asset_id`
- `caption`, `capture_date`, `captured_at`, `uploaded_at`
- `timezone`, `latitude`, `longitude`, `device_model`

Classification fields:
- `classification_label`
- `species_common_name`
- `variety_name`
- `species_scientific_name`
- `specific_note`
- `weather_hypothesis`
- `expected_harvest_window`
- `confidence`
- `labeling_method`
- `notes`

Audit fields:
- `created_at`
- `updated_at`

## Storage

Local DB path:
- `local/non_tomato_species/non_tomato_species.db`

This DB is kept local and excluded from git tracking.
