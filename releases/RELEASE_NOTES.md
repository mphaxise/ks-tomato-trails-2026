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
