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
  - Refreshed the shared Google Photos intake from the same season album URL.
  - Pulled and identified the latest upload set (`uploaded_at=2026-03-01`, `capture_date=2026-02-28`, 33 photos).
  - Regenerated labeled intake outputs and tomato pot mapping artifacts for the latest run.
  - Added pot-level series overrides for drifted pot assignments (`1T`, `2T`, `3T`, `7T`, `12T`, `28T`, `29T`, `31T`, `32T`) based on prior stable mapping.
  - Hardened mapping logic to skip extra unlabeled context rows beyond expected pot count and to let manual pot overrides take precedence for series-to-variety reconciliation.
  - Added automated v1.4-baseline reconciliation in tomato pot mapping:
    - `--baseline-map-csv` (defaulting to `releases/v1.4-2026-02-28/.../tomato_pot_mapping_latest.csv`)
    - `--baseline-reconcile` enabled by default
    - report metrics: `baseline_variety_map_size`, `baseline_applied_rows`
  - Added regression tests for baseline map loading and automatic baseline correction paths.
  - Refined end-user status communication for tomato runs:
    - mapping output now includes `context_id`, `final_status`, `review_stage`, `resolution_source`, and `review_status_label`
    - tomato page badges now reflect resolved pipeline state (`Ready (Auto-Resolved)` / targeted review states) instead of raw OCR-only uncertainty
    - unmapped context frames are excluded from tomato-pot view to avoid false review flags
  - Rebuilt all tracker pages and refreshed the version archive snapshot metadata.
- Validation:
  - `python3 scripts/extract_google_photos_public_album.py --html-input data/intake/google_photos/raw_album_page.html ...` passed.
  - `python3 scripts/download_google_photos_images.py --run-date 2026-02-28` passed (`downloaded_rows=33`).
  - `python3 scripts/label_non_tomato_from_images.py ...` passed.
  - `python3 scripts/build_tomato_pot_mapping.py --expected-pots 32 --strict` passed.
  - `python3 -m unittest discover -s tests -p 'test_*.py'` passed.
  - `npm run build:tracker` passed.

## v1.6-2026-03-02

- Release date: 2026-03-02
- Snapshot folder: `releases/v1.6-2026-03-02`
- Highlights:
  - Pulled one more Google Photos intake batch and confirmed a new run:
    - upload date `2026-03-02` (UTC)
    - capture date `2026-03-01`
    - `32` new photos
  - Refreshed end-to-end intake artifacts for the new run:
    - `album_manifest.csv` now includes `123` total album photos.
    - latest mapping run moved to `run_date=2026-03-01`.
  - Added v1.6 random-intake experiment track to handle non-baseline photo behavior:
    - new script: `scripts/v16_random_intake_research.py`
    - new outputs:
      - `data/research/v1_6/batch_drift_summary.csv`
      - `data/research/v1_6/intake_pipeline_plan.json`
      - `docs/V1.6-RANDOM-INTAKE-PIPELINE.md`
  - Added OCR/visual recovery benchmark for weak runs (`2026-02-28`, `2026-03-01`):
    - new script: `scripts/v16_ocr_recovery_experiment.py`
    - new outputs:
      - `data/research/v1_6/ocr_recovery/ocr_variant_ranked_summary.csv`
      - `data/research/v1_6/ocr_recovery/visual_similarity_summary.csv`
      - `data/research/v1_6/ocr_recovery/manual_label_queue.csv`
      - `docs/V1.6-LABEL-RECOVERY-EXPERIMENT.md`
  - Added focused review surfaces for fast error isolation:
    - `tracker/hard-row-reviewer.html` (manual-queue correction UI)
    - `tracker/pot-run-comparison.html` (pot-by-pot side-by-side `2026-02-28` vs `2026-03-01`)
  - Codified a continuity-first routine for future fresh-batch ingestion:
    - batch partitioning and frame routing
    - pot detection before OCR
    - OCR as weak signal
    - identity resolution prioritized by manual overrides and baseline continuity
    - strict confidence gating into review queues
  - Updated snapshot defaults so release archives now include v1.6 research artifacts.
- Validation:
  - `python3 scripts/extract_google_photos_public_album.py --html-input data/intake/google_photos/raw_album_page.html` passed (`photos_extracted=123`).
  - `python3 scripts/download_google_photos_images.py --run-date 2026-03-01` passed (`downloaded_rows=32`).
  - `python3 scripts/label_non_tomato_from_images.py --mixed-csv ... --output-csv ... --non-tomato-csv ... --overrides-csv ...` passed (`processed_rows=123`).
  - `python3 scripts/build_tomato_pot_mapping.py --run-date 2026-03-01 --expected-pots 32 --strict` passed (`unique_pot_count=32`).
  - `python3 scripts/v16_random_intake_research.py` passed (`latest_run_mode=watering_day_unlabeled_sequence`).
  - `python3 scripts/v16_ocr_recovery_experiment.py --run-dates 2026-02-28,2026-03-01 --visual-baseline-run-date 2026-02-27` passed.
  - `python3 -m unittest tests/test_v16_random_intake_research.py tests/test_v16_ocr_recovery_experiment.py tests/test_build_hard_row_reviewer_page.py tests/test_build_pot_intake_history_page.py tests/test_build_pot_run_comparison_page.py` passed.
  - `npm run build:tracker` passed.
  - `python3 scripts/create_version_snapshot.py --version-id v1.6-2026-03-02 ...` passed.

## v1.10-2026-03-07

- Release date: 2026-03-07
- Snapshot folder: `releases/v1.10-2026-03-07`
- Highlights:
  - Merged the v1.10 pot-anchored CV line into `master`.
  - Added the full indoor annotation workflow:
    - `tracker/v1-10-mask-label-seed.html`
    - `tracker/v1-10-neighbor-disambiguation.html`
    - `tracker/single-photo-seed-labeler.html`
    - `tracker/v1-10-seed-annotation-status.html`
  - Added queue and status artifacts for manual labeling:
    - `data/research/v1_10/mask_label_queue.csv`
    - `data/research/v1_10/mask_label_seed_set.csv`
    - `data/research/v1_10/neighbor_disambiguation_queue.csv`
    - `data/research/v1_10/seed_label_annotation_manifest.csv`
    - `data/research/v1_10/seed_label_annotation_summary.json`
  - Added pot-ID verification inside the seed labeler so annotators can reject a wrong prefilled pot and carry that mismatch through the status board.
- Validation:
  - `python3 -m unittest tests.test_build_single_photo_seed_labeler_page tests.test_build_v110_mask_seed_page tests.test_build_v110_neighbor_disambiguation_page tests.test_build_v110_pot_cv_page tests.test_build_v110_seed_annotation_status_page tests.test_v110_pot_cv_experiment tests.test_v110_seed_label_annotation_status` passed.
  - `npm run build:tracker` passed.
  - `python3 scripts/create_version_snapshot.py --version-id v1.10-2026-03-07 ...` passed.

## v1.11-2026-03-08

- Release date: 2026-03-08
- Snapshot folder: `releases/v1.11-2026-03-08`
- Highlights:
  - Refreshed the Google Photos intake and pulled a new latest batch:
    - `45` new photos on `capture_date=2026-03-07`
    - album manifest now includes `424` total photos
  - Rebuilt the production tracker surfaces around the new latest run:
    - `tracker/tomato-trails-view.html`
    - `tracker/pot-intake-history.html`
    - `tracker/non-tomato-snapshot.html`
    - `tracker/multi-photo-quick-labeler.html`
  - Added the v1.11 training-ingest board and outputs:
    - `tracker/v1-11-seed-annotation-ingest.html`
    - `data/research/v1_11/seed_annotation_ingest_manifest.csv`
    - `data/research/v1_11/seed_annotation_box_rows.csv`
    - `data/research/v1_11/seed_annotation_ingest_summary.json`
  - Fixed `scripts/build_pot_run_comparison_page.py` so the default comparison page follows the latest two available run dates instead of staying pinned to `2026-02-28` vs `2026-03-01`.
- Validation:
  - `python3 scripts/daily_ingest_google_photos.py` passed (`photos_extracted=424`, `downloaded_rows=45`, `latest_capture_date=2026-03-07`).
  - `python3 -m unittest tests/test_build_pot_run_comparison_page.py` passed.
  - `npm run build:tracker` passed.
  - `python3 scripts/create_version_snapshot.py --version-id v1.11-2026-03-08 ...` passed.

## v1.12-2026-03-12

- Release date: 2026-03-12
- Snapshot folder: `releases/v1.12-2026-03-12`
- Highlights:
  - Refreshed the Google Photos intake and pulled a new latest batch:
    - `32` new photos on `capture_date=2026-03-11`
    - album manifest now includes `456` total photos
  - Rebuilt the latest-run review surfaces around the new intake:
    - `tracker/tomato-trails-view.html`
    - `tracker/pot-intake-history.html`
    - `tracker/pot-run-comparison.html`
    - `tracker/multi-photo-quick-labeler.html`
  - Advanced the default latest-run comparison page to `2026-03-07` vs `2026-03-11`.
  - Refreshed the pot mapping outputs for experiment day `15` with all `32` pots auto-resolved and no mapping errors.
- Validation:
  - `python3 scripts/daily_ingest_google_photos.py` passed (`photos_extracted=456`, `downloaded_rows=32`, `latest_capture_date=2026-03-11`).
  - `npm run build:tracker` passed.
  - `python3 scripts/create_version_snapshot.py --version-id v1.12-2026-03-12 ...` passed.

## v1.13-2026-03-12

- Release date: 2026-03-12
- Snapshot folder: `releases/v1.13-2026-03-12`
- Highlights:
  - Added a new visual tracker surface:
    - `tracker/tomato-signal-observatory.html`
  - Wired the observatory into the main tracker and release archive flows:
    - `tracker/index.html`
    - `scripts/create_version_snapshot.py`
    - `scripts/build_version_archive_page.py`
  - Kept the March 11 intake state as the latest production baseline:
    - `456` total album rows
    - latest tomato run on `2026-03-11`
    - `32` mapped pots with `0` mapping errors
- Validation:
  - `python3 -m unittest tests/test_build_tomato_signal_observatory_page.py tests/test_build_pot_run_comparison_page.py` passed.
  - `npm run build:tracker` passed.
  - `python3 scripts/create_version_snapshot.py --version-id v1.13-2026-03-12 ...` passed.
