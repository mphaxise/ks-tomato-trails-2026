# Google Photos Public Extraction

Updated: 2026-02-28

## Purpose

Extract a public shared Google Photos album into structured local CSV files.

## Input

- Shared album URL from `photos.app.goo.gl` or `photos.google.com/share/...`
- Recommended source file:
  - `data/intake/google_photos/album_url.txt`

## Run

```bash
python3 scripts/extract_google_photos_public_album.py \
  --album-url "$(cat data/intake/google_photos/album_url.txt)"
```

Default outputs:
- `data/intake/google_photos/album_manifest.csv` (detailed metadata per photo)
- `data/intake/google_photos/manual_mixed_photos.csv` (prefill for mixed-photo intake)
- `data/intake/google_photos/raw_album_page.html` (raw fetched page for traceability)

## Notes

- `manual_mixed_photos.csv` leaves `caption` blank by default. Add caption when available.
- This extraction does not require API credentials; it parses the public album page payload.
- If the album link is not public, extraction fails because the share page data is unavailable.

## Run-Date Rule (Watering-Day Uploads)

- Use one shared album URL for the full 2026 season.
- Treat each watering-day upload as one run, keyed by `capture_date`.
- By default, scripts select the latest `capture_date` as the active run.
- Current active run expectation: 32 tomato pot photos (one per pot for this run).
- Label semantics for tomato-only runs:
  - `nT` = pot ID (unique per pot photo for the run)
  - `n` = tomato variety series number (repeats across pots)
- One-time series map file:
  - `data/intake/google_photos/manual_tomato_series_map.csv`
  - Current map intentionally has no `2` entry (those seedlings did not sprout).
- Pot-level override file (manual corrections by `pot_id`):
  - `data/intake/google_photos/manual_tomato_pot_series_overrides.csv`
- Lifecycle indexing defaults:
  - `potting_date=2026-02-24` (Tuesday transplant to current pots)
  - `day_one_photo_date=2026-02-25` (Wednesday first baseline photos)
  - `experiment_day` is computed from `day_one_photo_date` with day one = 1.

## Downstream Pipeline

After extraction:

```bash
python3 scripts/download_google_photos_images.py
python3 scripts/extract_packet_crops.py
python3 scripts/label_non_tomato_from_images.py \
  --mixed-csv data/intake/google_photos/manual_mixed_photos.csv \
  --output-csv data/intake/google_photos/manual_mixed_photos_labeled_v3.csv \
  --non-tomato-csv data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --overrides-csv data/intake/google_photos/manual_label_overrides_v1.csv

python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --no-strict
python3 scripts/build_tomato_trails_page.py
python3 scripts/build_non_tomato_snapshot_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```

Optional: build explicit day-one baseline mapping snapshot:

```bash
python3 scripts/build_tomato_pot_mapping.py \
  --run-date 2026-02-25 \
  --expected-pots 14 \
  --no-assume-sequential-pot-ids \
  --no-tomato-only-run \
  --series-map-csv /tmp/no_series_map.csv \
  --pot-series-overrides-csv /tmp/no_pot_overrides.csv \
  --output-csv data/intake/processed/tomato_pot_mapping_day1_2026-02-25.csv \
  --report-json data/intake/processed/tomato_pot_mapping_day1_2026-02-25_report.json \
  --no-strict
```

Strict verification mode (non-zero on unresolved mapping issues):

```bash
python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --strict
```

Generated tracker outputs:
- `tracker/tomato-trails-view.html` (primary tomato-only page)
- `tracker/non-tomato-snapshot.html` (archived non-tomato snapshot)
- `tracker/experiment-trails-view.html`
- `tracker/experiment-trails-label-editor.html`

## Release Snapshot (Before Merge)

To preserve this run as a versioned artifact set:

```bash
python3 scripts/create_version_snapshot.py \
  --version-id v1.2-2026-02-28 \
  --source-ref WORKTREE \
  --release-date 2026-02-28 \
  --notes "Tomato-only workflow release"
```

Artifacts are saved under:
- `releases/<version-id>/data/...`
- `releases/<version-id>/tracker/...`
- `releases/manifest.json`
- `releases/RELEASE_NOTES.md`

Then run merge guard:

```bash
python3 scripts/verify_release_snapshot_guard.py --base-ref origin/master --head-ref HEAD --include-working-tree
```
