# Release Notes

## Format

- Section header: `## v<major>.<minor>-YYYY-MM-DD`
- Required bullets:
  - `Release date`
  - `Snapshot folder`
  - `Highlights`
  - `Validation`

## v1.1-2026-02-25

- Release date: 2026-02-25
- Snapshot folder: `releases/v1.1-2026-02-25`
- Highlights:
  - Legacy baseline prior to tomato-only mapping upgrade.
  - Includes mixed tracker pages (`index`, `experiment-trails-view`, `experiment-trails-label-editor`).
  - Preserves baseline intake labeling files.
- Validation:
  - Historical baseline snapshot retained for comparison and audit.

## v1.2-2026-02-28

- Release date: 2026-02-28
- Snapshot folder: `releases/v1.2-2026-02-28`
- Highlights:
  - Tomato-only workflow with verified 32-pot mapping.
  - Manual tomato series mapping and pot-level overrides applied.
  - Lifecycle indexing added (`potting_date`, `day_one_photo_date`, `experiment_day`).
  - New pages added: `tomato-trails-view.html`, `non-tomato-snapshot.html`, `version-archive.html`.
- Validation:
  - `python3 -m unittest discover -s tests` passed.
  - `npm run build:tracker` passed.

## v1.3-2026-02-28

- Release date: 2026-02-28
- Snapshot folder: `releases/v1.3-2026-02-28`
- Highlights:
  - Canonicalized tomato name aliases:
    - `Bes Yellow Latvian` -> `Iles Yellow Latvian`
    - `Walmea Wild Cherry` -> `Waimea Wild Cherry`
  - Updated tomato view to use `Common Name = Tomato` and keep variety only in the variety field.
  - Regenerated tracker pages and mapping outputs with corrected naming.
- Validation:
  - `python3 -m unittest discover -s tests` passed.
  - `npm run build:tracker` passed.

## v1.4-2026-02-28

- Release date: 2026-02-28
- Snapshot folder: `releases/v1.4-2026-02-28`
- Highlights:
  - Started isolated computer-vision research track with no production view or production DB changes.
  - Added independent research pipeline:
    - `scripts/v14_cv_research_pipeline.py`
    - separate DB path: `local/cv_research/v1_4_cv_research.db`
    - separate artifact folder: `data/research/v1_4/`
  - Ran 32-photo pot experiment and generated mergeable research brief:
    - `docs/V1.4-CV-RESEARCH.md`
    - includes algorithm utility assessment, growth/health/survival hypotheses, and per-pot next-action suggestions.
  - Added visual research viewer page:
    - `scripts/build_v14_cv_research_page.py`
    - generated page: `tracker/v1-4-cv-research.html`
  - Added manual calibration subset + checker:
    - `data/research/v1_4/manual_calibration_subset.csv`
    - `scripts/v14_cv_calibration_check.py`
    - calibration summary: survival accuracy `91.7%`, action accuracy `83.3%` on the reviewed subset.
- Validation:
  - `python3 -m unittest discover -s tests` passed.
  - `python3 scripts/v14_cv_research_pipeline.py --run-id v1_4_20260228T045200Z` passed.
  - `python3 scripts/v14_cv_calibration_check.py` passed.

## v1.5-2026-03-01

- Release date: 2026-03-01
- Snapshot folder: `releases/v1.5-2026-03-01`
- Highlights:
  - Fixed lightbox clipping and navigation visibility in tracker pages.
  - Added zoom controls and interaction to the v1.4 research lightbox.
  - Corrected v1.4 pipeline run-date scoping to process only latest capture-date rows.
  - Refined plant-count estimation heuristic to avoid impossible over-counts.
  - Added explicit pot ID in v1.4 details panel.
  - Hardened label-editor saved-state loading with stable key mapping.
  - Added regression tests for tracker pages, tomato view generation, and v1.4 pipeline/page behavior.
- Validation:
  - `python3 -m unittest discover -s tests -p 'test_*.py'` passed.
  - `python3 scripts/v14_cv_research_pipeline.py` passed.
  - `python3 scripts/build_v14_cv_research_page.py` passed.
