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
│   ├── download_google_photos_images.py ← Download run-date photos to local image cache
│   ├── extract_packet_crops.py ← Seed-packet crop extractor from album photos
│   ├── label_non_tomato_from_images.py ← OCR species labeler for mixed album photos
│   ├── merge_label_overrides.py ← Merge web editor corrections into canonical overrides
│   ├── build_experiment_trails_page.py ← Build view-only HTML catalog
│   ├── build_tomato_trails_page.py ← Build tomato-only view page
│   ├── build_non_tomato_snapshot_page.py ← Build non-tomato snapshot archive page
│   ├── build_experiment_trails_label_editor_page.py ← Build editable correction HTML
│   ├── build_tomato_pot_mapping.py ← Build tomato pot-id mapping + verifier report
│   └── non_tomato_species_catalog.py ← Separate non-tomato species cataloger
├── tests/                  ← Unit tests for extraction/labeling/merge/catalog scripts
├── logs/
│   └── README.md           ← Field notes and freeform observations
├── releases/               ← Versioned snapshots (data + tracker pages per release)
└── tracker/
    ├── tomato-trails-view.html ← Tomato-only view catalog (primary)
    ├── non-tomato-snapshot.html ← View-only non-tomato archive snapshot
    ├── experiment-trails-view.html ← Full mixed catalog (reference)
    ├── experiment-trails-label-editor.html ← Editable label workspace
    ├── version-archive.html ← Version browser for release snapshots
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
python3 scripts/download_google_photos_images.py
python3 scripts/extract_packet_crops.py
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

The tomato pot mapping output now includes lifecycle timing fields:
- `potting_date` (current pots date)
- `day_one_photo_date` (baseline day-1 photo date)
- `day_since_potting`
- `experiment_day` (day-one indexed, first photo set = 1)

Tomato run label rules: `nT` is pot ID, `n` is tomato variety series number (repeating).  
Series mapping is stored at `data/intake/google_photos/manual_tomato_series_map.csv` (no `2` entry because those seedlings did not sprout).
Pot-level correction overrides are stored at `data/intake/google_photos/manual_tomato_pot_series_overrides.csv`.

If you want hard verification before merge, run:

```bash
python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --strict
```

6. Open:
  - `tracker/tomato-trails-view.html`
  - `tracker/pot-intake-history.html`
  - `tracker/pot-run-comparison.html`
  - `tracker/hard-row-reviewer.html`
  - `tracker/non-tomato-snapshot.html`
  - `tracker/experiment-trails-view.html`
  - `tracker/experiment-trails-label-editor.html`
  - `tracker/v1-4-cv-research.html`
  - `tracker/version-archive.html`
7. Start weekly logs in `data/observations/`
8. End-of-season scoring in `docs/SUCCESS_METRICS.md`

## Live Deployment (Cloudflare Pages)

Live site:
- https://ks-tomato-trails-2026.pages.dev/
- https://ks-tomato-trails-2026.pages.dev/tomato-trails-view
- https://ks-tomato-trails-2026.pages.dev/pot-intake-history
- https://ks-tomato-trails-2026.pages.dev/pot-run-comparison
- https://ks-tomato-trails-2026.pages.dev/hard-row-reviewer
- https://ks-tomato-trails-2026.pages.dev/non-tomato-snapshot
- https://ks-tomato-trails-2026.pages.dev/experiment-trails-view
- https://ks-tomato-trails-2026.pages.dev/experiment-trails-label-editor
- https://ks-tomato-trails-2026.pages.dev/v1-4-cv-research
- https://ks-tomato-trails-2026.pages.dev/version-archive

## Versioned Releases

- Archive root: `releases/`
- Manifest: `releases/manifest.json`
- Release notes: `releases/RELEASE_NOTES.md`
- Snapshot script: `scripts/create_version_snapshot.py`
- Guard script: `scripts/verify_release_snapshot_guard.py`
- Version/tag format: `v<major>.<minor>-YYYY-MM-DD` (example: `v1.3-2026-02-28`)

Create/update a release snapshot:

```bash
python3 scripts/create_version_snapshot.py \
  --version-id v1.3-2026-02-28 \
  --source-ref WORKTREE \
  --release-date 2026-02-28 \
  --notes "Tomato-only workflow release"
```

Run merge guard before opening/merging a PR to `master`:

```bash
npm run check:release-guard
```

After merging to `master`, create/push an annotated git tag with the same version id:

```bash
git tag -a v1.3-2026-02-28 -m "Release v1.3-2026-02-28"
git push origin v1.3-2026-02-28
```

Local deploy commands (using existing `wrangler` login credentials):

```bash
npm run cf:whoami
npm run deploy:cloudflare
```

CI pipeline:
- GitHub Actions workflow: `.github/workflows/deploy-cloudflare-pages.yml`
- Auto-deploys on push to `master` when tracker/build inputs change.
- Required GitHub repository secrets:
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`

## V1.4 CV Research Track (Isolated)

V1.4 is an isolated computer-vision research stream. It does **not** modify production tracker pages or the existing local non-tomato DB.

Run the v1.4 research pipeline:

```bash
python3 scripts/v14_cv_research_pipeline.py

# Optional: compare predictions against manually reviewed subset
python3 scripts/v14_cv_calibration_check.py

# Build visual research page
python3 scripts/build_v14_cv_research_page.py
```

Default outputs:
- Research DB (separate): `local/cv_research/v1_4_cv_research.db`
- Research artifacts: `data/research/v1_4/`
  - `cv_experiment_results.csv`
  - `pot_recommendations.csv`
  - `algorithm_assessment.csv`
  - `research_summary.json`
  - `manual_calibration_subset.csv`
  - `calibration_report.md`
  - `calibration_summary.json`
- Mergeable research doc: `docs/V1.4-CV-RESEARCH.md`
- Visual research page: `tracker/v1-4-cv-research.html`

Default input set:
- 32-pot mapping CSV: `data/intake/processed/tomato_pot_mapping_latest.csv`
- Local image cache: `local/non_tomato_species/images`
- Baseline references: `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`

## V1.6 Random Intake Research Track (Isolated)

V1.6 focuses on batch drift and robust intake sequencing when fresh Google Photos uploads are unlabeled/noisy.

Run:

```bash
python3 scripts/v16_random_intake_research.py
```

Default outputs:
- Batch drift summary CSV: `data/research/v1_6/batch_drift_summary.csv`
- Routine plan JSON: `data/research/v1_6/intake_pipeline_plan.json`
- Research doc: `docs/V1.6-RANDOM-INTAKE-PIPELINE.md`

## V1.6 OCR Recovery + Comparison Review Track

V1.6 also includes a focused recovery experiment and review surfaces for weak-photo runs (`2026-02-28` and `2026-03-01`):

```bash
python3 scripts/v16_ocr_recovery_experiment.py \
  --run-dates 2026-02-28,2026-03-01 \
  --visual-baseline-run-date 2026-02-27

python3 scripts/build_hard_row_reviewer_page.py
python3 scripts/build_pot_run_comparison_page.py \
  --run-a 2026-02-28 \
  --run-b 2026-03-01
```

Default outputs:
- OCR/visual summaries + manual queue: `data/research/v1_6/ocr_recovery/`
- Experiment doc: `docs/V1.6-LABEL-RECOVERY-EXPERIMENT.md`
- Reviewer page: `tracker/hard-row-reviewer.html`
- Side-by-side continuity check page: `tracker/pot-run-comparison.html`

---

*Built with 🌫️ for growers where the fog never really lifts.*
