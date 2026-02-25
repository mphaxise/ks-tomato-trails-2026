# Requirements Catalog: K's Tomato Trails 2026

Review date: 2026-02-25  
Status: discovery decisions resolved; ready for implementation

## Scope statement

Build a low-friction decision-support system for K's ongoing 12-variety tomato trial in Sausalito, with T and collaborator support for data quality, environmental enrichment, and reporting.

## Phase anchor (resolved)

- V1 target window: by end of day or by end of weekend (2026-02-25 to weekend).
- V1 owners: T + collaborator support.
- V1 output: initial photo set mapped to variety/seedling identity, then handoff to K.
- V1 ingestion source: shared Google Photos album (Google Drive deferred unless needed).
- V1 access mode: manual/shared-link pull first (API ingestion deferred).
- V1 location model: one shared backyard location for all plants.
- V1 dashboard mode: hosted URL from day 1.
- V1 advisory scope: weather + rodents/pests + pollination + city/ecosystem alerts.
- Geotag policy: keep exact internally, coarse-grain before any sharing.
- Sharing posture: private to K/T/collaborator support first; publication only if K decides.
- Post-handoff K flow: upload/tag photos in shared Google Photos album, then review project dashboard URL later from laptop.
- Album contributors may include you, T, or K depending on phase.
- Baseline metadata contract is finalized:
  - required: `variety_name`, `plant_id_or_pot_id`, `photo`, `capture_date`, `seed_source_or_packet_name` (`unknown` allowed)
  - optional: `notes`
- Implementation mode is continuous test-and-deploy with collaborative UX checkpoints.

## User roles

- K: primary user and grower-scientist; needs fast capture and useful guidance.
- T: collaborator and handoff bridge; supports field operations and K enablement.
- You (project collaborator): system setup, quality checks, context enrichment, summaries.
- Community growers (optional future audience): only in scope if K chooses publication later.

## Functional requirements

### F1. Trial registry
- Maintain canonical registry of 12 varieties with stable IDs.
- Track plant-level identifiers where multiple plants exist per variety.

### F2. Baseline onboarding
- Capture initial seedling state for all 12 varieties:
  - variety name
  - plant/pot ID
  - baseline photo
  - timestamp
  - backyard location metadata (shared site-level value in V1)
  - optional starter notes
- V1 requirement: complete baseline mapping package prepared by T + collaborator support.

### F3. Ongoing capture workflow
- Support recurring updates with minimal friction.
- K target: photo-first entry via existing apps (album add/tag), no spreadsheet work.
- Capture cadence target: weekly minimum, multiple times per week when feasible.
- No requirement for same-time-of-day photos.

### F4. Observation schema integrity
- Ensure required fields are present and normalized.
- Keep observation records usable for longitudinal comparison.

### F5. Environmental enrichment
- Attach weather context by date and location.
- Track key environmental signals that can impact plant outcomes.

### F6. Local advisory enrichment
- Aggregate local advisories relevant to plant health.
- V1 in-scope categories:
  - pollination-impacting conditions
  - rodents/animals/pest alerts
  - city-level weather/climate/ecosystem updates

### F7. Weekly insight output
- Produce recurring summary for K:
  - what changed
  - which varieties improved/declined
  - probable context signals
  - suggested focus for next check

### F8. Comparative ranking output
- Generate end-of-season comparative ranking using Fog Belt Score framework.
- Include narrative rationale, not only scores.

### F9. Sharing and handoff
- Ensure T can access and share outputs with K reliably.
- Provide output formats for private review first.
- Treat external publishing as optional and controlled by K.

### F10. Exportability
- Preserve data in portable formats suitable for future analysis/publication.

### F11. External photo-source ingestion
- Ingest photos from a shared Google Photos album (V1).
- Use manual shared-link pull for V1 ingestion.
- Keep Google Drive as future fallback requirement only if needed.
- Keep API-based ingestion as future enhancement after V1 stability.
- Extract available phone metadata (capture time, optional geotag/device, file identity).
- Preserve source references for traceability and reprocessing.

### F12. K dashboard access
- Provide a project URL where K can view synced photos/data and emerging insights.
- Dashboard must be readable from laptop with minimal navigation.
- Use hosted URL delivery from day 1 in V1.

### F13. Handoff package
- Provide concise instructions for K after V1 setup:
  - where to upload/tag photos
  - expected capture cadence
  - how to open and interpret the dashboard URL

### F16. End-of-season info-viz package
- Deliver a final visual report package for K combining rankings, timeline insights, and contextual factors.
- Keep final package private by default unless K opts to publish.

### F14. Continuous test-and-deploy loop
- Implement in small increments that are testable and deployable at each milestone.
- Maintain a repeatable verification step before each handoff.

### F15. Collaborative UX validation
- Include user-in-the-loop UX testing checkpoints during implementation.
- Translate UX feedback into documented requirement or workflow updates.

## Non-functional requirements

### N1. Low-friction by default
- K-facing interactions should stay short and repeatable.
- Avoid requiring spreadsheet maintenance during capture.

### N2. Mobile-friendly capture
- Workflow must work from a phone camera context.
- K should be able to continue using existing apps already on her phone.

### N3. Incremental adoption
- Start useful with baseline photos and minimal metadata.
- Allow deeper automation without breaking early records.

### N4. Explainability
- Every key insight should be traceable to source observations and context.

### N5. Resilience to missing data
- System should handle skipped days and still provide value.

### N6. Operational clarity
- Ownership for capture, validation, and summaries must be explicit.

### N7. Low onboarding overhead
- Avoid introducing new user accounts/apps for K in initial phase.
- Support-side automation should absorb complexity.

### N8. Fast handoff readiness
- V1 must be handoff-ready for K by the agreed short window (today/weekend).

### N9. Short feedback cycle
- Each implementation step should close with: test result, demoable output, and feedback intake.

### N10. Privacy-first location handling
- Exact location/geotag data is internal analysis data only.
- Shared outputs must use coarse-grained location representation.

## Data requirements

### Core entities
- Variety
- Plant
- Observation
- Photo
- Location
- Weather event/summary
- Advisory item
- Insight summary

### Minimum fields to confirm before coding
- Variety canonical names for all 12 entries
- Plant/pot ID convention
- Required photo metadata set for ingestion pipeline

## Priority tags (MoSCoW)

- Must:
  - F1, F2, F3, F4, F6, F7, F9, F11, F12, F13, F14, F15, F16
  - N1, N2, N6, N7, N8, N9, N10
- Should:
  - F5, F8, F10
  - N3, N4
- Could:
  - F6 in expanded depth beyond first categories
  - richer publish-mode website packaging in first phase
- Won't (for initial phase):
  - full product UI with complex accounts/permissions
  - broad ecosystem data ingestion without relevance filtering

## Acceptance criteria for discovery completion

All core discovery decisions are resolved as of 2026-02-25.

1. K/T/you workflow responsibilities are agreed.
2. Baseline onboarding fields are finalized.
3. Capture cadence and minimum data contract are approved.
4. Initial enrichment scope is approved.
5. Private vs public output posture for first phase is decided.
6. K handoff package and dashboard URL experience are approved.
7. Continuous test-and-deploy + UX checkpoint cadence is approved.
