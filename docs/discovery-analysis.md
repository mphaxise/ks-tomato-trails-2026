# Discovery Analysis: K's Tomato Trails 2026

Review date: 2026-02-25  
Repository: `mphaxise/ks-tomato-trails-2026` (renamed from `fog-tomato-trials`)  
Source context files: `/Users/praneet/PraneetIdeas/manual_ideas.json`, `/Users/praneet/PraneetIdeas/memory.md`  
Conversation context added: user briefing on 2026-02-25

## Idea context extracted from sources and briefing

### Ranked idea context
- Title: K's Tomato Trails 2026
- Ranked source idea: Advance fog-tomato-trials: Tracking tomato variety trials in Sausalito fog-belt - citizen science for backyard growers
- Rank: 1
- Priority: 7
- Source: Repository ks-tomato-trails-2026 (renamed from fog-tomato-trials)
- Idea link: https://github.com/mphaxise/ks-tomato-trails-2026

### From `/Users/praneet/PraneetIdeas/manual_ideas.json`
- No tomato-trials manual entry currently exists.
- Practical implication: tomato project context currently lives in memory/repo review and direct collaborator briefing.

### From `/Users/praneet/PraneetIdeas/memory.md`
- 2026-02-25 daily review ranks tomato project as top pick.
- Existing direction: create clear execution plan and ship first ambiguity-reducing milestone.
- Existing gap callout: add next-milestone strategy/roadmap documentation.

### From collaborator briefing (2026-02-25)
- Primary user is K (grower-scientist running the real experiment).
- T and you are support operators who help K capture, organize, and analyze data.
- Current state:
  - Seeds for 12 tomato varieties have germinated into seedlings.
  - Seedlings were repotted on 2026-02-24.
  - Team discussion occurred on 2026-02-25 morning.
- Critical operating constraint: K has limited time, so project entry effort must be minimal.
- Desired flow:
  - confirm all 12 variety names
  - start with baseline photos of all seedlings
  - support weekly minimum photo capture with optional additional uploads
  - use shared Google Photos album for V1 uploads
  - V1 setup by collaborator + T with initial mapping package, then handoff to K
  - K uploads/tags photos in shared album and later checks a hosted project dashboard URL
  - enrich observations with local weather and local advisories (pollination, rodents/animals, city climate/ecosystem updates)
  - produce private decision support and info-viz outputs for K; K decides if/when to publish.

## Problem statement (redefined)

K is actively running a 12-variety tomato trial, but lacks a low-friction system that turns daily/weekly observations into decision-grade insights for Sausalito conditions. The project must minimize data-entry burden on K while maximizing relevant environmental context and producing credible conclusions and visuals for K's personal decision making.

## Target users (redefined)

- Primary user: K (experiment owner, busy practitioner, needs fast capture and useful insights).
- Secondary users: T and you (setup, data QA, enrichment, analysis, handoff operations).
- Tertiary users (optional): local growers only if K chooses to publish outputs later.

## Jobs-to-be-done

1. K can log plant progress quickly without administrative overhead.
2. T/you can enrich raw plant observations with local weather and advisory context.
3. Team can compare 12 varieties over time and produce defensible recommendations.
4. K can open one hosted dashboard URL to review synced trails and insights.
5. Team can deliver a final info-viz report package for K.
6. Publication remains a K-controlled optional path.

## Requirement extraction (high-level)

### Functional requirements
- A canonical list of 12 varieties with stable IDs.
- Baseline onboarding capture for each seedling (photo + variety + plant/pot ID + location + timestamp).
- V1 onboarding ownership: collaborator + T deliver initial photo-to-variety mapping package.
- Repeatable capture workflow for ongoing photos and simple status notes.
- Shared Google Photos ingestion (V1) with metadata extraction.
- Site-level backyard location metadata (V1) to support local weather correlation.
- Weather timeline linked to observation dates.
- Advisory feed layer for local events that may impact growth (pollination conditions, rodents/animals, city/ecosystem alerts).
- Weekly summary output for K (what changed, what needs action).
- End-of-season ranking and rationale for top-performing varieties.
- Private info-viz/report output mode for K, with optional publish-ready export only if K requests.

### Non-functional requirements
- Minimal interaction cost for K (quick, repeatable, phone-friendly workflow).
- No strict same-time-of-day requirement for photo capture.
- Clear handoff model between you, T, and K.
- One-URL insight access pattern for K (low navigation overhead).
- Continuous test-and-deploy cadence during implementation.
- Collaborative UX testing checkpoints with user during implementation.
- Privacy-first handling of location/geotag data in shared outputs.
- Data traceability (source/date/location attached to each key observation).
- Graceful handling of missing days (system should still provide useful insights).
- Keep implementation incremental to avoid delaying real-world data capture.

Detailed requirements catalog: `docs/requirements-catalog.md`.

## Success metrics (updated)

### User and workflow metrics
- K can complete a capture session in a few minutes without needing spreadsheet cleanup.
- At least one usable summary is delivered to K every week during active season.
- K can reliably open one project URL and see latest synced insights after upload.
- Data backlog requiring manual cleanup stays low and bounded.

### Data quality metrics
- 12 varieties registered with confirmed names/IDs.
- Baseline photo set exists for all seedlings.
- Observation records maintain required fields at high completeness.
- Weather/advisory context is available for most observation windows.

### Outcome metrics
- Clear, evidence-backed ranking of varieties for K's backyard conditions.
- Practical recommendations K can act on in-season and next season.
- Final info-viz report package delivered for K's personal use.
- Optional publish-ready export prepared only if K requests.

## Constraints and assumptions (updated)

- Trial is real and already underway; onboarding must start from current seedling stage.
- K is time-constrained; support tooling must reduce burden, not add process.
- Full 12-variety names are not yet confirmed in repo data.
- Current repo is documentation-heavy with minimal automation.
- Legacy `fog-tomato-trials` naming should be retained only in explicit historical-context notes.
- Environmental enrichment sources are not yet selected or integrated.
- Google Photos ingestion source and manual/shared-link pull mode are selected for V1.
- Baseline onboarding metadata fields are selected for V1.
- V1 location granularity is selected as one backyard location for all plants.
- Hosted dashboard delivery mode for V1 is selected.
- Sharing posture is private-first with K-controlled publication.
- Geotag policy is selected: exact internal, coarse in shared outputs.
- The trial remains observational, so conclusions are practical and directional.

## Current state and gaps

### Current state in repo
- Strong baseline docs: strategy, schema, varieties, climate context, scoring.
- Starter data exists in `data/varieties.json` and `data/weather_log.csv`.
- Tracker implementation is not yet built.

### Gaps relative to new briefing
- Collaborator-role workflow for K/T/you is documented but not yet trialed in real operations.
- Low-friction capture protocol is documented but not yet validated with K usage.
- Baseline seedling photo workflow is defined but not yet completed for all 12 varieties.
- No implemented Google Photos ingestion and metadata mapping workflow exists yet (manual/shared-link mode is selected but not built).
- K handoff instructions document exists but is not yet approved and executed.
- Dashboard delivery mode is defined, but hosted implementation is not yet built.
- No advisory-ingestion or relevance-filter model is defined.
- Handoff plan for T sharing outputs with K exists at doc level but no operational checklist automation exists.
- Private-first sharing posture is defined; publication-export workflow is not yet implemented.

## Risks (updated)

- Adoption risk: if logging is too heavy, K will not sustain high-quality capture.
- Data relevance risk: generic weather/advisories may add noise without location-aware filtering.
- Coordination risk: unclear ownership among K/T/you can create dropped tasks.
- Insight risk: missing baseline photos/IDs can weaken season-end comparisons.
- Platform risk: shared-album permissions or link changes can break ingestion continuity.
- Privacy risk: photo geotags may expose precise location data if publishing defaults are not controlled.
- Scope risk: building full product UI too early may delay useful weekly insights.
- Communication risk: mixed legacy naming can fragment docs and handoff clarity.

## 2026-03-02 Update: V1.7 Diagnosis-First Research Track

A new research briefing identified a critical mismatch between intended architecture (OCR-primary with continuity fallback) and observed behavior on weak runs (continuity-only with zero OCR matches in hard queue rows).

Planning implications:
1. Run Type 0 diagnosis first (`SW-0`, `SW-0b`) before further architecture experiments.
2. Deploy minimum reviewer UX honesty fixes (`HITL-0`) before spending additional reviewer time.
3. Treat OCR crop-targeting diagnosis as the immediate gate for downstream experiments.

Linked artifacts:
- `docs/V1.7-GARDEN-CV-RESEARCH-BRIEFING.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
