# Google Photos Public Extraction

Updated: 2026-02-27

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

## Downstream Pipeline

After extraction:

```bash
python3 scripts/extract_packet_crops.py
python3 scripts/label_non_tomato_from_images.py \
  --mixed-csv data/intake/google_photos/manual_mixed_photos.csv \
  --output-csv data/intake/google_photos/manual_mixed_photos_labeled_v3.csv \
  --non-tomato-csv data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --overrides-csv data/intake/google_photos/manual_label_overrides_v1.csv

python3 scripts/build_experiment_trails_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```

Generated tracker outputs:
- `tracker/experiment-trails-view.html`
- `tracker/experiment-trails-label-editor.html`
