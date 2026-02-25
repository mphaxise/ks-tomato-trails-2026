# New Thread Prompt (Post-Discovery)

Use this prompt to start the next implementation thread.

```text
You are my coding agent for /Users/praneet/ks-tomato-trails-2026.

Continue from completed discovery docs and execute implementation end-to-end in continuous test-and-deploy mode with collaborative UX checkpoints.

Read first:
- /Users/praneet/ks-tomato-trails-2026/docs/STRATEGY.md
- /Users/praneet/ks-tomato-trails-2026/docs/requirements-catalog.md
- /Users/praneet/ks-tomato-trails-2026/docs/V1-HANDOFF-WORKFLOW.md
- /Users/praneet/ks-tomato-trails-2026/docs/DATA_SCHEMA.md
- /Users/praneet/ks-tomato-trails-2026/docs/COLLABORATION-INPUT-LOG.md
- /Users/praneet/ks-tomato-trails-2026/docs/next-questions.md

Resolved decisions to enforce:
- Canonical name: K's Tomato Trails 2026; repo slug ks-tomato-trails-2026.
- V1 ingestion source: Google Photos album only.
- V1 access mode: manual shared-link pull first.
- V1 location model: one shared backyard location for all plants.
- Geotag policy: keep exact internally; coarse-grain before any sharing.
- Dashboard delivery mode: hosted URL from day 1.
- Advisory scope: weather + rodents/pests + pollination + city/ecosystem alerts.
- Sharing posture: private-first for K/T/collaborator support; publication only if K decides.
- V1 baseline metadata required:
  - variety_name
  - plant_id_or_pot_id
  - photo
  - capture_date
  - seed_source_or_packet_name (unknown allowed)
  - notes optional
- V1 ownership: T + collaborator prepare baseline package; then handoff to K.

Execution requirements:
- Implement in small milestones; after each milestone run tests/checks and report outcomes.
- Include me in UX checkpoints; pause for feedback at each milestone boundary.
- Update /Users/praneet/ks-tomato-trails-2026/docs/COLLABORATION-INPUT-LOG.md at each milestone.
- At each major step show:
  - what changed
  - exact files edited/created
  - next 1-3 actions

Start with milestone 1:
- Implement baseline data intake path for Google Photos manual-link workflow and produce a verifiable local test/demo.
```
