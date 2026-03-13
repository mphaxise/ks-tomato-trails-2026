# V1 Handoff Workflow

Updated: 2026-03-13

## Purpose

Define the initial operating workflow from collaborator setup to K handoff.

## V1 objective (today to end of weekend)

T + collaborator support prepares the baseline package so K can continue with minimal friction.

### V1 package contents

1. Initial photo set for seedlings.
2. Mapping from each seedling/photo to tomato variety (and seed source when known).
3. Canonical plant/pot IDs for tracking continuity.
4. Short handoff instructions for K.
5. Hosted dashboard URL for reviewing synced trails and insights from day 1.

### Baseline metadata fields (resolved)

- Required per seedling:
  - `variety_name`
  - `plant_id_or_pot_id`
  - `photo`
  - `capture_date`
  - `seed_source_or_packet_name` (`unknown` allowed)
- Optional:
  - `notes`

Location note:
- V1 uses one shared backyard location for all plants (not per-pot tracking).

## Post-handoff K workflow

1. During garden checks, K takes photos on phone.
2. K adds/tags those photos into the shared Google Photos album.
3. Later in the day, K opens the hosted project dashboard URL from laptop.
4. K reviews synced timeline + emerging insights.

Notes:
- Weekly minimum photo cadence is sufficient.
- Additional uploads during notable changes are encouraged.
- Same time-of-day is not required.

## Support workflow (T + collaborator)

1. Pull newly uploaded photos from shared Google Photos album via manual/shared-link workflow.
2. Extract available metadata (capture timestamp, optional geotag/device).
3. Validate and map assets to variety/plant IDs.
4. For drifted runs, run manual two-run reconciliation (`tracker/manual-two-run-tagger.html`) and merge exported corrections into `data/intake/google_photos/manual_two_run_tag_overrides.csv`.
5. Enrich with weather and selected advisory signals:
   - pollination conditions
   - rodents/animals/pest alerts
   - city weather/climate/ecosystem alerts
6. Publish updated summaries/insights to dashboard view.

## Deferred enhancement

- API-based Google Photos ingestion can be added after V1 if manual pull creates operational friction.

## Privacy and sharing posture (resolved)

- This is a private project for K's personal use, supported by T + collaborator.
- Exact geotags remain internal.
- Any outward sharing/publication is optional and determined by K.
