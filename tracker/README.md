# Tracker Pages

This folder contains the generated HTML pages used to review and correct current OCR/classification output.

## Pages

- `tracker/tomato-trails-view.html`: tomato-only view catalog (primary)
- `tracker/pot-intake-history.html`: pot-by-pot photo timeline across intake runs
- `tracker/pot-run-comparison.html`: side-by-side pot comparison (`2026-02-28` vs `2026-03-01`)
- `tracker/hard-row-reviewer.html`: focused reviewer for difficult OCR rows (manual queue)
- `tracker/non-tomato-snapshot.html`: non-tomato snapshot archive
- `tracker/experiment-trails-view.html`: full mixed view catalog (reference)
- `tracker/experiment-trails-label-editor.html`: editable correction workspace
- `tracker/new-batch-reviewer.html`: focused low-confidence reviewer for newest batch rows
- `tracker/version-archive.html`: versioned release browser (v1.1, v1.2, v1.3, ...)
- `tracker/v1-4-cv-research.html`: v1.4 computer-vision research viewer (local/generated)

Live URLs:
- https://ks-tomato-trails-2026.pages.dev/
- https://ks-tomato-trails-2026.pages.dev/tomato-trails-view
- https://ks-tomato-trails-2026.pages.dev/pot-intake-history
- https://ks-tomato-trails-2026.pages.dev/pot-run-comparison
- https://ks-tomato-trails-2026.pages.dev/hard-row-reviewer
- https://ks-tomato-trails-2026.pages.dev/non-tomato-snapshot
- https://ks-tomato-trails-2026.pages.dev/experiment-trails-view
- https://ks-tomato-trails-2026.pages.dev/experiment-trails-label-editor
- https://ks-tomato-trails-2026.pages.dev/new-batch-reviewer
- https://ks-tomato-trails-2026.pages.dev/version-archive
- https://ks-tomato-trails-2026.pages.dev/v1-4-cv-research

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
python3 scripts/build_pot_intake_history_page.py
python3 scripts/build_pot_run_comparison_page.py
python3 scripts/build_hard_row_reviewer_page.py
python3 scripts/build_tomato_trails_page.py
python3 scripts/build_non_tomato_snapshot_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
python3 scripts/build_new_batch_reviewer_page.py
python3 scripts/build_v14_cv_research_page.py
```

## Deploy Commands

```bash
npm run cf:whoami
npm run deploy:cloudflare
```

Cloudflare configuration files:
- `wrangler.jsonc`
- `.github/workflows/deploy-cloudflare-pages.yml`

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
python3 scripts/download_google_photos_images.py
python3 scripts/label_non_tomato_from_images.py \
  --mixed-csv data/intake/google_photos/manual_mixed_photos.csv \
  --output-csv data/intake/google_photos/manual_mixed_photos_labeled_v3.csv \
  --non-tomato-csv data/intake/google_photos/manual_non_tomato_labeled_v3.csv \
  --overrides-csv data/intake/google_photos/manual_label_overrides_v1.csv
python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --no-strict

python3 scripts/build_experiment_trails_page.py
python3 scripts/build_tomato_trails_page.py
python3 scripts/build_non_tomato_snapshot_page.py
python3 scripts/build_experiment_trails_label_editor_page.py
```

Use strict verification (non-zero exit) when you want merge-gating checks:

```bash
python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --strict
```

Tomato-only label conventions for run-day photos:
- `nT`: unique pot ID
- `n`: tomato variety series number (can repeat)
- One-time series map source: `data/intake/google_photos/manual_tomato_series_map.csv` (`2` intentionally absent)
- Pot-level override source: `data/intake/google_photos/manual_tomato_pot_series_overrides.csv`
- Lifecycle timeline defaults in mapping:
  - `potting_date=2026-02-24`
  - `day_one_photo_date=2026-02-25`
  - `experiment_day` day-one indexing for progress tracking

## Version Archive Workflow

Create a release snapshot (data + pages) before merge or deployment:

```bash
python3 scripts/create_version_snapshot.py \
  --version-id v1.3-2026-02-28 \
  --source-ref WORKTREE \
  --release-date 2026-02-28 \
  --notes "Tomato-only workflow release"
```

Archive metadata is tracked in:
- `releases/manifest.json`
- `releases/<version-id>/metadata.json`
- `releases/RELEASE_NOTES.md`

Merge guard command (must pass before merge to `master`):

```bash
npm run check:release-guard
```
