# Strategy Document: K's Tomato Trails 2026

## Project context

This project supports a real, in-progress tomato trial run by K in Sausalito.  
As of 2026-02-25:
- 12 tomato varieties have germinated as seedlings.
- Seedlings were repotted on 2026-02-24.
- K is the primary grower-scientist and decision maker.
- T and project collaborators provide data/analysis support so K can stay focused on growing.

Collaboration input and milestone-level direction changes are tracked in `docs/COLLABORATION-INPUT-LOG.md`.
Initial operator-to-K handoff workflow is documented in `docs/V1-HANDOFF-WORKFLOW.md`.

## Project goal

Help K identify which tomato varieties perform best in her backyard conditions by combining low-effort plant observations with relevant local environmental context, then produce analysis and info-viz outputs for K's personal use. Publication decisions remain with K.

## Primary strategy principles

1. Minimize burden on K.
2. Prioritize decision-useful data over high-volume generic data.
3. Capture baseline now, then improve process incrementally.
4. Keep outputs understandable, not just data-rich.
5. Preserve traceability from raw observation to conclusion.
6. Reuse K's existing tools before introducing new apps.
7. Use continuous test-and-deploy in small increments.
8. Run collaborative UX testing with the user at each milestone.

## Core problem

K needs a practical decision system, not just a trial log:
- Which varieties are actually thriving?
- What local weather/ecosystem factors may explain changes?
- What action should K take this week?

Without structured capture and contextual enrichment, useful observations risk becoming fragmented notes that are hard to compare or turn into actionable decisions.

## User roles and responsibilities

### K (primary user)
- Runs the garden trial.
- After handoff, captures photos from phone and adds them to the shared album.
- Uses weekly insights for care and selection decisions.
- Reviews project dashboard URL later in the day (typically from laptop).

### T + collaborator support (secondary users)
- Deliver V1 setup by today/end-of-weekend:
  - initial seedling photos
  - mapping of each seedling to tomato variety/seed source
- Prepare handoff instructions for K's recurring workflow.
- Confirm and maintain canonical plant metadata.
- Ensure data quality and continuity.
- Add weather and advisory context.
- Produce weekly summaries and season-end analysis for K.

## Trial design

### Type: structured observational trial

All varieties are grown in one backyard context under similar care, with expected variation in micro-position and random events.

### Planned sample

- 12 varieties
- 1-2 plants per variety (where available)
- Plant-level tracking to support comparisons over time

### Observation horizon

- Seedling stage starts immediately (already in progress)
- Main active season expected through October 2026
- End-of-season scoring and recommendation package in November 2026

## Data collection model

### Layer 1: low-friction capture (K-facing)
- Baseline photos for all seedlings
- Ongoing photo updates (weekly minimum, multiple times per week when feasible)
- Minimal notes per update (health signal, obvious issues)

### Capture channel strategy (K-facing)
- Preferred channel for V1: shared Google Photos album.
- Google Drive is deferred and treated as future fallback only if needed.
- K should not be required to learn a new app or follow rigid formatting rules.
- Variable time-of-day captures are accepted; natural timing variance is expected.
- Album contribution can come from you, T, or K at different phases (V1 setup, handoff, ongoing use).
- K workflow target:
  - take photos during garden checks
  - add/tag photos into the shared album
  - open project URL later to review synced data and insights

### Layer 2: structured metrics (support-facing)
- Weekly standardized metrics from `DATA_SCHEMA.md`
- Variety and plant ID normalization
- Manual/shared-link pull from Google Photos album for V1 ingestion
- Timestamp and location metadata extraction from photo files when available
- Manual fallback fields when photo metadata is missing
- V1 location granularity uses one shared backyard location across all plants

### Layer 3: contextual enrichment
- Local weather snapshots and trend notes
- Local advisories that can affect growth:
  - pollination conditions
  - pests/rodents
  - city-level weather/climate/ecosystem alerts
- Relevance filtering so only actionable context appears in summaries

### Layer 4: insight delivery (K-facing)
- Hosted dashboard URL from day 1 where K can review:
  - synced photo timeline
  - variety-level trail/progress view
  - emerging insights and recommendations

## Data sharing posture (resolved)

- Default mode is private to K, T, and collaborator support.
- Exact geotags may be kept internally for analysis.
- Any shared output should use coarse-grained location representation.
- External publication is optional and only at K's discretion.

## Execution mode (resolved)

- Delivery mode: continuous test-and-deploy (ship in small, verifiable increments).
- UX mode: collaborative testing with user feedback loops throughout implementation.

## Key research questions

1. Which varieties set and ripen fruit reliably in K's backyard conditions?
2. Which varieties remain stable under fog/humidity and disease pressure?
3. Which environmental patterns correlate with growth changes?
4. Which varieties should be prioritized for next season?

## Success definition

### Operational success
- K can sustain data capture without workflow friction.
- K can capture and upload photos from existing apps in under a few minutes.
- Weekly summaries are delivered and useful for decisions.
- Dataset remains consistent enough for season-end comparison.

### Decision success
- Clear ranking using Fog Belt Score and supporting evidence.
- Actionable recommendations for next planting cycle.
- Final info-viz style report and analysis package for K.
- Optional publication support if K explicitly chooses to share.

Scoring rubric remains in `SUCCESS_METRICS.md`.

## Output deliverables

1. Complete seasonal observation record with baseline seedling context.
2. Weekly or periodic insight summaries for K.
3. End-of-season ranked report with rationale.
4. Private info-viz report package for K, with optional publish-ready export if K requests.

## Timeline (updated for current stage)

| Milestone | Target window |
|---|---|
| Confirm canonical list of 12 varieties | Immediate (today/weekend) |
| V1 baseline package from T+collaborator (photos + mapping) | Immediate (today/weekend) |
| Handoff instructions + dashboard URL for K | Immediate (today/weekend) |
| Finalize Google Photos album for V1 ingestion | Immediate (today/weekend) |
| Start recurring capture cadence | Within 1 week |
| Begin weather/advisory enrichment | Within 1-2 weeks |
| Mid-season comparative checkpoint | July-August 2026 |
| Final harvest window | By October 2026 |
| End-of-season scoring/report | November 2026 |
