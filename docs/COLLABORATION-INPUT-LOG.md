# Collaboration Input Log

Purpose: keep an evolving record of user guidance and how it changes project direction.

How to use this file:
- Update at the end of each discovery or implementation milestone.
- Capture what the user asked for, what changed in project artifacts, and why it matters.
- Keep entries concise and traceable to files changed.

## Milestone log

### 2026-02-25 - Discovery baseline created

User input summary:
- Run discovery first and do not start implementation without approval.
- Extract full idea context from `/Users/praneet/PraneetIdeas/manual_ideas.json` and `/Users/praneet/PraneetIdeas/memory.md`.
- Review repo state and produce three discovery artifacts.

How this changed project direction:
- Established a discovery-first workflow and gated implementation behind user approval.
- Produced explicit problem framing, implementation paths, and pre-coding decisions.

Artifacts affected:
- `docs/discovery-analysis.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`

Collaboration impact:
- Reduced ambiguity about scope and sequencing.
- Made approval checkpoints explicit before coding begins.

### 2026-02-25 - User-context redefinition (K/T collaboration model)

User input summary:
- Primary user is K; T and collaborator support K.
- Trial is already in progress (seedlings germinated, repotted on 2026-02-24).
- Priority is low-friction data capture with decision-useful outputs for K.

How this changed project direction:
- Reframed project from generic citizen-science trial to K-centered decision support.
- Added role-based workflow (K vs T/support) and updated success criteria around usability and weekly insight delivery.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`
- `docs/requirements-catalog.md`

Collaboration impact:
- Converted narrative context into executable requirements.
- Clarified who does what in recurring operations.

### 2026-02-25 - Data-entry workflow update (existing-app upload path)

User input summary:
- Expect weekly or multi-weekly photos, not strict daily capture.
- Do not require same time-of-day captures.
- Prefer least-resistance workflow via existing apps (Google Drive or Google Photos shared source).
- Support side can ingest photo metadata and enrich with external data sources.

How this changed project direction:
- Formalized external shared-source ingestion as a core requirement.
- Relaxed rigid photo-capture constraints and shifted complexity to support-side ingestion/enrichment.
- Added privacy/permission considerations for geotags and shared access.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/DATA_SCHEMA.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`

Collaboration impact:
- Improved adoption likelihood for K by preserving existing behavior.
- Increased feasibility of sustained data capture with minimal friction.

### 2026-02-25 - Collaboration governance update

User input summary:
- Create a dedicated repository document that records user instructions and explains how those instructions shape collaboration and milestones.
- Keep the document evolving as new milestones are completed.

How this changed project direction:
- Added a standing artifact for process traceability, not just product requirements.
- Formalized milestone-by-milestone updates as part of standard workflow.

Artifacts affected:
- `docs/COLLABORATION-INPUT-LOG.md`
- `docs/STRATEGY.md` (reference link added to collaboration log)

Collaboration impact:
- Makes decision history auditable and easier to resume in future sessions.
- Reduces repeated context re-explanation across milestones.

### 2026-02-25 - Naming decision resolved

User input summary:
- Confirmed canonical naming with "yes":
  - Project name: `K's Tomato Trails 2026`
  - Repo slug: `ks-tomato-trails-2026`
  - Keep `fog-tomato-trials` only as historical context.

How this changed project direction:
- Locked naming consistency for active docs and decision artifacts.
- Reduced future ambiguity in handoff and collaboration communication.

Artifacts affected:
- `README.md`
- `docs/VARIETIES.md`
- `docs/next-questions.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Eliminates naming churn before implementation.
- Keeps legacy references intentionally scoped to historical notes.

### 2026-02-25 - Ownership split and V1 handoff flow resolved

User input summary:
- V1 target: by end of day or by end of weekend.
- V1 setup is owned by T + collaborator support.
- V1 output is initial photos mapped to seedling/variety identity.
- After handoff, K should use existing behavior:
  - take photos from phone
  - add/tag photos into shared Google Drive/Google Photos album
  - later open a project URL on laptop to review synced data and insights

How this changed project direction:
- Replaced abstract role split with concrete phase-based ownership.
- Added explicit dashboard-consumption workflow for K.
- Anchored near-term milestone around handoff readiness, not just documentation.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Clarifies immediate execution for this weekend.
- Aligns product direction around K's real usage pattern instead of speculative flows.

### 2026-02-25 - V1 ingestion source narrowed to Google Photos

User input summary:
- Start with Google Photos album only for V1.
- Defer Google Drive unless future user behavior requires it.
- Album contributions may come from you, T, or K depending on phase.

How this changed project direction:
- Reduced integration surface for V1 and removed a parallel source path.
- Focused ingestion requirements and handoff workflow on one source of truth.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`
- `docs/DATA_SCHEMA.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Improves implementation speed for weekend V1 target.
- Lowers operational ambiguity during handoff to K.

### 2026-02-25 - V1 access model set to manual pull

User input summary:
- Selected option 1 for access model:
  - use shared-link/manual pull first for Google Photos ingestion in V1.

How this changed project direction:
- Removed API-first dependency from V1 path.
- Converted access-model choice from open question to decided baseline.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`
- `docs/DATA_SCHEMA.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Keeps V1 feasible within the weekend window.
- Defers integration complexity until after real usage feedback.

### 2026-02-25 - Baseline metadata + implementation cadence decisions

User input summary:
- Confirmed baseline metadata contract ("yes"):
  - required: `variety_name`, `plant_id_or_pot_id`, `photo`, `capture_date`, `seed_source_or_packet_name` (`unknown` allowed)
  - optional: `notes`
- Directed implementation mode:
  - continuous test-and-deploy execution
  - collaborative UX testing with user throughout implementation
- Requested a reusable prompt to start a new thread after discovery.

How this changed project direction:
- Resolved baseline field ambiguity for V1 onboarding.
- Added process-level requirements for short feedback cycles during build.
- Added new-thread handoff artifact for clean session transitions.

Artifacts affected:
- `docs/DATA_SCHEMA.md`
- `docs/requirements-catalog.md`
- `docs/STRATEGY.md`
- `docs/implementation-options.md`
- `docs/discovery-analysis.md`
- `docs/next-questions.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/NEW-THREAD-PROMPT.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Speeds implementation startup with fewer unresolved inputs.
- Aligns build workflow with rapid validation and user-in-loop UX checks.

### 2026-02-25 - V1 location granularity set to single backyard site

User input summary:
- Chose option 1 for location granularity:
  - use one backyard location for all plants in V1.

How this changed project direction:
- Removed per-pot micro-location complexity from initial implementation.
- Standardized weather correlation against a single site-level location context.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/DATA_SCHEMA.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/next-questions.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Keeps V1 data model lean and faster to execute this weekend.
- Defers fine-grained location modeling until there is evidence it is needed.

### 2026-02-25 - Collaboration process tuned (batch updates)

User input summary:
- Raised concern about excessive document churn after every single question.
- Requested a more optimal collaboration flow.

How this changed project direction:
- Switched from per-question doc edits to batched update passes after multiple decisions are collected.

Artifacts affected:
- `docs/COLLABORATION-INPUT-LOG.md`
- `docs/next-questions.md` (used as decision queue between batched updates)

Collaboration impact:
- Reduces noise during decision-making.
- Keeps updates focused and easier to review.

### 2026-02-25 - Final discovery decisions for privacy, delivery, and scope

User input summary:
- Geotag policy: use recommended option (exact internal, coarse in shared outputs).
- Dashboard delivery: hosted URL from day 1.
- Advisory scope: weather + rodents/pests + pollination + city/ecosystem alerts.
- Sharing model: private to K/T/collaborator support first.
- Clarified this is K's personal project; outputs and analysis are for K, and K decides if/when publication happens.

How this changed project direction:
- Finalized privacy and delivery assumptions for V1.
- Locked broad advisory ingestion scope for initial implementation.
- Reframed publication as optional, K-controlled pathway.

Artifacts affected:
- `docs/STRATEGY.md`
- `docs/discovery-analysis.md`
- `docs/requirements-catalog.md`
- `docs/implementation-options.md`
- `docs/next-questions.md`
- `docs/DATA_SCHEMA.md`
- `docs/V1-HANDOFF-WORKFLOW.md`
- `docs/NEW-THREAD-PROMPT.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Discovery phase now has a complete resolved decision set.
- Implementation can start without further requirement ambiguity.

## Update template for future milestones

```
### YYYY-MM-DD - <milestone title>

User input summary:
- ...

How this changed project direction:
- ...

Artifacts affected:
- ...

Collaboration impact:
- ...
```
