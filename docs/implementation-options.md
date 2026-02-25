# Implementation Options: K's Tomato Trails 2026

Review date: 2026-02-25  
Goal: choose the first build path before coding starts

## Execution method (resolved)

- Use a continuous test-and-deploy loop for implementation.
- Run collaborative UX testing with user feedback throughout development.
- Keep V1 private-first for K/T/collaborator support.

## Option 1: Concierge workflow first (manual operations + strong templates)

### What this path includes
- Create a very lightweight operating workflow for K, T, and collaborator support.
- Start with baseline seedling photos + canonical 12-variety metadata.
- Use simple shared templates for recurring notes and weekly summaries.
- Use shared Google Photos album as the initial ingestion source.

### Advantages
- Fastest to activate with today's real-world seedling stage.
- Lowest technical overhead while requirements stabilize.
- Strong fit for K's low-friction constraint.

### Tradeoffs
- Data quality and consistency depend on manual discipline.
- Weather/advisory enrichment can become inconsistent.
- Harder to scale into repeatable analysis without tooling.

## Option 2: Hybrid foundation (minimal capture + automated enrichment/checks)

### What this path includes
- Keep K's capture workflow minimal (photo + short note + optional quick fields).
- Add support-side automation for:
  - metadata and observation validation
  - Google Photos ingestion
  - weather enrichment by location/date
  - advisory aggregation and relevance filtering
- Add weekly summary generation from captured data.

### Advantages
- Preserves low burden on K while improving decision quality.
- Reduces manual cleanup for T/you.
- Builds a reusable core for future app/dashboard work.

### Tradeoffs
- More initial setup than pure concierge mode.
- Requires early choices on data sources and validation strictness.
- Still not a full self-serve product for K unless UI is added.

## Option 3: Product-first app (capture UI + dashboard + publishing)

### What this path includes
- Build K-facing capture UI first (mobile-friendly).
- Include environment layer, alerts, and variety comparison dashboard.
- Add direct publish mode for community-facing website/report output.

### Advantages
- Best long-term usability if adopted.
- Strong public storytelling and sharing potential.
- Can unify capture, analysis, and publishing into one system.

### Tradeoffs
- Highest complexity and scope risk at this early stage.
- Can delay immediate insights for K while engineering catches up.
- Requires unresolved decisions about auth, hosting, and long-term ownership.

## Recommended path

Recommended: Option 2 (Hybrid foundation), preceded by a fast Option 1 baseline onboarding pass.

Why:
- It matches the real state: seedlings already exist and K needs low-friction support now.
- It keeps K's effort minimal while still producing cleaner, context-rich data.
- It enables weekly decision support sooner than a full app-first approach.

## First milestone (60-90 minutes)

1. Finalize collaborator workflow: who captures, who validates, who summarizes.
2. Define baseline onboarding packet for all 12 seedlings (name, ID, photo, pot/location, date).
3. Implement Google Photos manual/shared-link pull workflow for v1 ingestion.
4. Define the minimum weekly capture contract for K (small enough to sustain; extra uploads optional).
5. Implement selected enrichment scope (weather + rodents/pests + pollination + city/ecosystem alerts).
6. Implement K handoff package and hosted dashboard URL workflow.
7. Define the test/deploy cadence and UX feedback checkpoint for the first implementation sprint.

Expected deliverable at 60-90 minutes: one concrete, approved operating spec that can be executed immediately with current seedlings and later automated safely.

## End-of-day outcome

- K-facing workflow is clear and low-effort.
- Shared photo ingest path is operationally clear for K and support collaborators.
- Baseline data model covers both plant observations and environmental context.
- Team can run a repeatable weekly insight loop without high manual overhead.
- Next-session implementation can start without re-litigating product fundamentals.
