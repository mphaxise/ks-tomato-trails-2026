# V1 Baseline Intake (Google Photos Manual Link)

Updated: 2026-02-25

## Goal

Convert manual Google Photos rows into normalized baseline records for V1.

## Input format

Files:
- `data/intake/google_photos/manual_baseline.csv` (live intake sheet)
- `data/intake/google_photos/manual_baseline_sample.csv` (demo data)
- `data/intake/google_photos/album_url.txt` (shared album URL for fallback)

Minimum required per row:
- `caption` in this exact shape:
  - `<variety> | <plant/pot id> | <seed source or unknown>`

Photo URL behavior:
- preferred: provide `photo_url` per row
- fallback: leave `photo_url` blank and run with `--album-url` (shared album URL used for that row)

Optional:
- `capture_date` (`YYYY-MM-DD`)
- `captured_at`, `uploaded_at`, `timezone`, `latitude`, `longitude`, `device_model`, `notes`

If `capture_date` is blank, intake derives it from `captured_at` or `uploaded_at`.

## Run intake

```bash
python3 scripts/google_photos_manual_intake.py \
  --input data/intake/google_photos/manual_baseline.csv \
  --output data/intake/processed/baseline_observations.csv \
  --album-url "$(cat data/intake/google_photos/album_url.txt)"

# demo
python3 scripts/google_photos_manual_intake.py \
  --input data/intake/google_photos/manual_baseline_sample.csv \
  --output data/intake/processed/baseline_observations_sample.csv
```

## Output

Output CSV includes V1 required baseline fields plus source metadata:
- `variety_name`
- `plant_id_or_pot_id`
- `photo`
- `capture_date`
- `seed_source_or_packet_name`
- `notes`
- and Google Photos traceability fields (`source_*`, timestamps, device/geotag when present)

## Validation rules

- Variety in caption must match `data/varieties.json` (`id` or name).
- Caption must include 3 parts separated by `|`.
- Missing `photo_url` or missing capture date signal causes a row error.
- Missing `photo_url` is allowed only when `--album-url` is provided.
