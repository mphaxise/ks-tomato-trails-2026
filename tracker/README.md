# Tracker Pages

This folder contains the generated HTML pages used to review and correct current OCR/classification output.

## Pages

- `tracker/experiment-trails-view.html`: view-only catalog
- `tracker/experiment-trails-label-editor.html`: editable correction workspace

## View Page Features

- Search + filter (`All`, `Tomato`, `Non-Tomato`, `Needs Review`)
- Gallery cards and detailed table view
- Click any photo (card or table thumbnail) to open full-photo lightbox
- Lightbox includes full metadata panel:
  - common name
  - variety
  - scientific name
  - specific note
  - weather hypothesis
  - expected harvest window
- Lightbox navigation:
  - Previous/Next controls at bottom
  - keyboard support: `ArrowLeft`, `ArrowRight`, `Escape`

## Label Editor Features

- Editable per-photo fields:
  - classification label
  - common name
  - variety
  - scientific name
  - specific note
  - weather hypothesis
  - expected harvest window
  - confidence / method / caption
  - optional `pot_tag` and `packet_tag`
- Full-photo lightbox with same field editing
- Save/load in browser local storage
- Export changed rows as corrections CSV

## Build Commands

```bash
python3 scripts/build_experiment_trails_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```

## Correction Merge Workflow

1. Open `tracker/experiment-trails-label-editor.html`.
2. Edit rows and click `Download Corrections CSV`.
3. Merge export into canonical overrides:

```bash
python3 scripts/merge_label_overrides.py \
  --incoming /path/to/manual_label_overrides_web_YYYY-MM-DDTHH-MM-SS.csv
```

4. Re-run OCR labeling + rebuild pages:

```bash
python3 scripts/label_non_tomato_from_images.py \
  --mixed-csv data/intake/google_photos/manual_mixed_photos.csv \
  --output-csv data/intake/google_photos/manual_mixed_photos_labeled_v3.csv \
  --non-tomato-csv data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --overrides-csv data/intake/google_photos/manual_label_overrides_v1.csv

python3 scripts/build_experiment_trails_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```
