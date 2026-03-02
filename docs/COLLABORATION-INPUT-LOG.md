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

### 2026-02-25 - Implementation Milestone 1 kickoff (manual intake pipeline)

User input summary:
- Confirmed implementation should begin now, while waiting for the public Google Photos share URL.
- Requested a simpler, repeatable operating pattern for photo labeling and future iterations.

How this changed project direction:
- Moved from discovery artifacts to an executable V1 intake path.
- Implemented a manual-link baseline ingestion script that accepts the simplified caption contract and emits normalized baseline records.
- Added a local demo path and automated tests so milestone output is verifiable before live album intake.

Artifacts affected:
- `scripts/google_photos_manual_intake.py`
- `tests/test_google_photos_manual_intake.py`
- `data/intake/google_photos/manual_baseline.csv`
- `data/intake/google_photos/manual_baseline_sample.csv`
- `docs/V1-BASELINE-INTAKE.md`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- T/collaborator can begin structured baseline intake immediately, even before API integration.
- Once share URL arrives, ingestion can run with minimal extra setup.

### 2026-02-26 - Shared album URL received and intake fallback hardened

User input summary:
- Shared Google Photos album URL was provided for V1 intake.

How this changed project direction:
- Added a default album URL config file and pipeline fallback so rows can be processed even when per-photo URLs are not yet extracted.
- Added validation check: current provided URL returns HTTP 404 from Google Photos in this environment, so link publication/access likely still pending.

Artifacts affected:
- `data/intake/google_photos/album_url.txt`
- `scripts/google_photos_manual_intake.py`
- `tests/test_google_photos_manual_intake.py`
- `docs/V1-BASELINE-INTAKE.md`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Intake work can proceed now with simple caption rows and no per-photo URL requirement.
- Once link access is active, support can optionally add per-photo URLs later for finer traceability.

### 2026-02-26 - Separate local non-tomato species catalog added

User input summary:
- Requested non-tomato photos be labeled, species-identified, and stored separately in a local database outside Tomato Trails outputs.

How this changed project direction:
- Added a dedicated non-tomato catalog pipeline that filters tomato photos, assigns non-tomato species labels from caption/notes keywords, and stores only non-tomato rows in a separate local SQLite database.
- Kept this store local-only (git-ignored) to avoid mixing auxiliary species data into Tomato Trails core records.

Artifacts affected:
- `scripts/non_tomato_species_catalog.py`
- `tests/test_non_tomato_species_catalog.py`
- `data/intake/google_photos/manual_mixed_photos.csv`
- `data/intake/google_photos/manual_mixed_photos_sample.csv`
- `docs/NON-TOMATO-SPECIES-LOCAL-DB.md`
- `.gitignore`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Mixed albums can now be processed without contaminating tomato trial datasets.
- Non-tomato species context is retained for local reference and can be expanded later with better classifiers if needed.

### 2026-02-26 - Public album extraction + OCR-based non-tomato labeling

User input summary:
- Shared a working public album URL and asked to keep going.
- Clarified photos include visible species labels/seed packet labels.

How this changed project direction:
- Added public-album extraction from shared URL into local manifest/intake CSVs.
- Added OCR-based packet-label parsing over downloaded full-resolution images.
- Added automated non-tomato labeling pipeline and connected it to the separate local species DB flow.

Artifacts affected:
- `scripts/extract_google_photos_public_album.py`
- `scripts/label_non_tomato_from_images.py`
- `tests/test_extract_google_photos_public_album.py`
- `tests/test_label_non_tomato_from_images.py`
- `docs/GOOGLE-PHOTOS-PUBLIC-EXTRACTION.md`
- `docs/NON-TOMATO-SPECIES-LOCAL-DB.md`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Public album metadata can now be pulled and normalized immediately from share URL.
- Non-tomato rows can be identified from visible packet labels and persisted to a separate local DB without manual row-by-row triage.

### 2026-02-26 - Live album run completed and non-tomato species persisted

User input summary:
- Confirmed labels on photos/seed packets indicate species identity and asked to continue execution.

How this changed project direction:
- Completed live extraction on public album and downloaded full-resolution assets.
- Added packet-crop extraction for faster OCR from label cards.
- Ran OCR labeling pass and persisted detected non-tomato rows into the separate local species DB.

Artifacts affected:
- `scripts/extract_packet_crops.py`
- `scripts/label_non_tomato_from_images.py`
- `scripts/non_tomato_species_catalog.py`
- `data/intake/google_photos/album_manifest.csv`
- `data/intake/google_photos/manual_mixed_photos.csv`
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`
- `data/intake/google_photos/manual_non_tomato_labeled_v3.csv`
- `docs/NON-TOMATO-SPECIES-LOCAL-DB.md`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Separate local DB now contains species-labeled non-tomato records from the live shared album.
- Tomato-trial data remains isolated from auxiliary species tracking.

### 2026-02-26 - Simple OCR status web page generated

User input summary:
- Requested a simple web page showing what is currently available in the experiment trails after OCR tagging.

How this changed project direction:
- Added a static HTML status page generator for current OCR-tagging snapshot reporting.
- Page includes total counts, non-tomato species breakdown, tomato/non-tomato tables, and unresolved rows needing manual review.

Artifacts affected:
- `scripts/build_experiment_trails_page.py`
- `tracker/experiment-trails-ocr.html`
- `tracker/README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Provides a shareable, low-friction view of current OCR coverage without opening raw CSV/DB files.
- Can be regenerated quickly after each new OCR run to keep progress visible.

### 2026-02-26 - Manual packet-label verification + OCR pipeline hardening

User input summary:
- Shared additional close-up packet photos and asked to continue implementation with better OCR.
- Clarified that seed packet labels are the source of truth for species/variety labeling.

How this changed project direction:
- Added a manual per-row override layer for verified packet labels to prevent OCR-only misclassification.
- Expanded non-tomato and tomato keyword coverage (including Leek/Spinach and additional TomatoFest varieties).
- Re-ran labeling and regenerated tracker output using verified labels from local photo evidence.

Artifacts affected:
- `scripts/label_non_tomato_from_images.py`
- `scripts/non_tomato_species_catalog.py`
- `data/intake/google_photos/manual_label_overrides_v1.csv`
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`
- `data/intake/google_photos/manual_non_tomato_labeled_v3.csv`
- `tracker/experiment-trails-ocr.html`
- `docs/NON-TOMATO-SPECIES-LOCAL-DB.md`
- `tests/test_label_non_tomato_from_images.py`
- `tests/test_non_tomato_species_catalog.py`

Collaboration impact:
- OCR+manual hybrid labeling now captures verified tomato varieties and non-tomato species with lower false positives.
- The status page and non-tomato local DB now reflect currently confirmed packet-label evidence.

### 2026-02-26 - Unknown rows closed with packet-level verification

User input summary:
- Asked to keep going and provided additional close-up packet photos for unresolved rows.

How this changed project direction:
- Completed manual packet-label resolution for rows 01-12 (non-tomato block).
- Converted unresolved rows to verified/inferred species labels and reduced `unknown` to zero.

Artifacts affected:
- `data/intake/google_photos/manual_label_overrides_v1.csv`
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`
- `data/intake/google_photos/manual_non_tomato_labeled_v3.csv`
- `tracker/experiment-trails-ocr.html`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Current OCR status page now represents a fully classified snapshot for the 26 available album photos.
- Non-tomato local DB ingest now includes Lettuce, Spinach, Kale, Red Cabbage, Turnip, Leek, Collards, and Pea records.

### 2026-02-26 - Added editable photo-label correction page

User input summary:
- Requested a second page listing all photos with editable identified plant names.
- Asked whether pot-number / packet-number pairing should inform classification.

How this changed project direction:
- Added a dedicated editable correction workspace page that shows each photo with editable classification/species fields.
- Added correction export flow and merge utility to feed manual edits back into the override-based labeling pipeline.
- Added optional `pot_tag` and `packet_tag` capture in editor exports (stored via `notes_append`) for future inference support.

Artifacts affected:
- `scripts/build_experiment_trails_label_editor_page.py`
- `scripts/merge_label_overrides.py`
- `tracker/experiment-trails-label-editor.html`
- `tracker/README.md`
- `tests/test_merge_label_overrides.py`

Collaboration impact:
- Manual labeling can now be performed in a visual web workflow and merged into canonical overrides without hand-editing CSV files.
- Pot/packet numeric linkage can now be captured consistently for future auto-label logic improvements.

### 2026-02-27 - Tracker page renamed to view-only catalog and enriched with lightbox navigation

User input summary:
- Requested the non-editor tracker page be renamed to a view-only page and updated with evolved fields.
- Requested clickable photos, full-photo lightbox view, and next/previous navigation controls.
- Requested keyboard arrow navigation in lightbox and full metadata visibility beside the expanded photo.

How this changed project direction:
- Repositioned the tracker status output as a read-only catalog page (`experiment-trails-view.html`).
- Added full-photo lightbox behavior to both gallery cards and table thumbnails.
- Added bottom nav controls (`Previous` / `Next`) and keyboard controls (`ArrowLeft`, `ArrowRight`, `Escape`) for faster review.
- Ensured metadata panel in lightbox includes common name, variety, scientific name, specific note, weather hypothesis, and harvest window.

Artifacts affected:
- `scripts/build_experiment_trails_page.py`
- `tracker/experiment-trails-view.html`
- `tracker/README.md`

Collaboration impact:
- Makes photo review practical on laptop without losing context.
- Reduces manual back-and-forth while validating row-level labels and variety assignments.

### 2026-02-27 - Evolved field persistence added across overrides, OCR output, and local non-tomato DB

User input summary:
- Asked to update database logic and documentation with the newly evolved data fields.
- Confirmed ongoing need for editable taxonomy/notes data to flow through future iterations.

How this changed project direction:
- Extended override-merge schema to retain `variety_name`, `specific_note`, `weather_hypothesis`, and `expected_harvest_window`.
- Extended OCR labeled output schema with the same evolved fields.
- Updated non-tomato local DB ingestion to preserve curated input fields when available and to store them in SQLite.
- Added schema migration support for existing local DB tables via additive column checks.

Artifacts affected:
- `scripts/merge_label_overrides.py`
- `scripts/label_non_tomato_from_images.py`
- `scripts/non_tomato_species_catalog.py`
- `tests/test_label_non_tomato_from_images.py`
- `tests/test_non_tomato_species_catalog.py`
- `docs/DATA_SCHEMA.md`
- `docs/NON-TOMATO-SPECIES-LOCAL-DB.md`
- `docs/GOOGLE-PHOTOS-PUBLIC-EXTRACTION.md`
- `README.md`
- `tracker/README.md`

Collaboration impact:
- Manual corrections now persist more completely between runs.
- Local non-tomato catalog can carry richer agronomic context, not just species labels.

### 2026-02-27 - Cloudflare deployment and CI pipeline established for tracker pages

User input summary:
- Requested both HTML tracker pages be made live on the internet.
- Requested a deployment pipeline to Cloudflare using existing credentials.

How this changed project direction:
- Created a Cloudflare Pages project (`ks-tomato-trails-2026`) and deployed tracker pages publicly.
- Added a tracker index launcher page for a clean root URL entry point.
- Added local repeatable deploy scripts via `package.json` and `wrangler.jsonc`.
- Added GitHub Actions deployment workflow for Cloudflare Pages on `master` updates.

Artifacts affected:
- `tracker/index.html`
- `tracker/experiment-trails-view.html`
- `tracker/experiment-trails-label-editor.html`
- `package.json`
- `wrangler.jsonc`
- `.github/workflows/deploy-cloudflare-pages.yml`
- `README.md`
- `tracker/README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- K/T can open live tracker URLs immediately without local files.
- Deployment is now repeatable locally and automatable through GitHub CI.

### 2026-02-28 - V1.4 CV research track started with isolated DB and 32-photo experiment run

User input summary:
- Start version 1.4 as a computer-vision research effort.
- Keep production views and existing databases unchanged.
- Use an independent research database.
- Run algorithm experiments against the 32-photo pot run and produce a mergeable research document with actionable hypotheses and per-plant suggestions.

How this changed project direction:
- Added a dedicated v1.4 computer-vision pipeline that writes to a separate SQLite database and separate research artifact folder.
- Ran a full baseline experiment on the 32 tomato-pot photos and generated a research report with algorithm utility assessment, survival hypotheses, and pot-level next-action suggestions.
- Added tests for baseline lookup, CV feature extraction, and end-to-end isolated pipeline execution.

Artifacts affected:
- `scripts/v14_cv_research_pipeline.py`
- `tests/test_v14_cv_research_pipeline.py`
- `docs/V1.4-CV-RESEARCH.md`
- `data/research/v1_4/cv_experiment_results.csv`
- `data/research/v1_4/pot_recommendations.csv`
- `data/research/v1_4/algorithm_assessment.csv`
- `data/research/v1_4/research_summary.json`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- V1.4 research can progress independently without risking production regressions.
- Results are now reproducible, queryable via an isolated DB, and ready to merge as research notes for release documentation.

### 2026-02-28 - V1.4 calibration pass + release-notes draft

User input summary:
- Requested both:
  - a focused threshold-calibration follow-up pass against a manually reviewed subset
  - a `v1.4` release-notes draft section.

How this changed project direction:
- Added manual image-review calibration subset and an explicit calibration checker script.
- Calibrated segmentation/ROI/scoring thresholds to reduce background leakage and over-optimistic survival calls on early-seedling photos.
- Added a draft `v1.4` release-notes section that records the isolated research-track outputs and validation commands.

Artifacts affected:
- `scripts/v14_cv_research_pipeline.py`
- `scripts/v14_cv_calibration_check.py`
- `tests/test_v14_cv_research_pipeline.py`
- `tests/test_v14_cv_calibration_check.py`
- `data/research/v1_4/manual_calibration_subset.csv`
- `data/research/v1_4/calibration_report.md`
- `data/research/v1_4/calibration_summary.json`
- `docs/V1.4-CV-RESEARCH.md`
- `releases/RELEASE_NOTES.md`
- `README.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Calibration quality is now measurable (`91.7%` survival agreement, `83.3%` action agreement on reviewed subset).
- `v1.4` is documented for merge/release communication without altering production surfaces.

### 2026-02-28 - Visual v1.4 research HTML viewer added

User input summary:
- Requested a consumable visual HTML page for research output that uses images and presents results clearly.

How this changed project direction:
- Added a dedicated v1.4 research page generator that transforms research CSV/JSON outputs into an image-rich, filterable HTML viewer.
- Extended v1.4 metrics output with `photo_url` and `variety_name` fields so cards can display direct photos and clearer context.

Artifacts affected:
- `scripts/build_v14_cv_research_page.py`
- `tracker/v1-4-cv-research.html`
- `scripts/v14_cv_research_pipeline.py`
- `tests/test_build_v14_cv_research_page.py`
- `tracker/README.md`
- `README.md`
- `releases/RELEASE_NOTES.md`

Collaboration impact:
- Research findings are now easier to consume visually for quick review and decision-making.
- v1.4 outputs can be shared as a single static page without changing existing production tracker pages.

### 2026-03-02 - V1.6 random-intake experiment kickoff with latest Google Photos batch

User input summary:
- Wrap up prior version context and start a new version focused on realistic intake behavior.
- Pull one additional Google Photos batch (last-night uploads) before implementation changes.
- Analyze how incoming batches differ from baseline one-pot labeled photos.
- Define a robust standard algorithm sequence for identifying pots/plants and mapping to the DB under random photo conditions.

How this changed project direction:
- Refreshed album extraction and pulled the newest batch (`capture_date=2026-03-01`, `uploaded_at=2026-03-02`, 32 photos).
- Re-ran labeling and tomato mapping for the latest batch and quantified that mapping success is now continuity-driven rather than OCR-driven.
- Started an explicit v1.6 research track for batch-drift analysis and intake-routing strategy.

Artifacts affected:
- `data/intake/google_photos/raw_album_page.html`
- `data/intake/google_photos/album_manifest.csv`
- `data/intake/google_photos/manual_mixed_photos.csv`
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`
- `data/intake/processed/tomato_pot_mapping_latest.csv`
- `data/intake/processed/tomato_pot_mapping_report_latest.json`
- `scripts/v16_random_intake_research.py`
- `tests/test_v16_random_intake_research.py`
- `data/research/v1_6/batch_drift_summary.csv`
- `data/research/v1_6/intake_pipeline_plan.json`
- `docs/V1.6-RANDOM-INTAKE-PIPELINE.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- The team now has a repeatable, data-backed intake analysis routine that can run after each new Google Photos pull.
- V1.6 formalizes a continuity-first identification pipeline for unlabeled/random batches while preserving a review queue for uncertain rows.

### 2026-03-02 - OCR/visual recovery experiment on weak runs + manual queue extraction

User input summary:
- Confirmed dissatisfaction with 2026-02-28 and especially 2026-03-01 pot/variety identification quality.
- Requested deeper image-analysis exploration on those runs.
- Asked for long-term ideas including potential human-labeling support with minimal effort.

How this changed project direction:
- Added a focused OCR-variant recovery benchmark on the weak runs (`2026-02-28`, `2026-03-01`) with exact pot-ID match evaluation.
- Added a non-OCR visual-similarity baseline against the stronger `2026-02-27` template run.
- Added a targeted manual-label queue with pre-cropped images for hard rows to support low-friction human correction.

Artifacts affected:
- `scripts/v16_ocr_recovery_experiment.py`
- `tests/test_v16_ocr_recovery_experiment.py`
- `data/research/v1_6/ocr_recovery/ocr_variant_eval_details.csv`
- `data/research/v1_6/ocr_recovery/ocr_variant_ranked_summary.csv`
- `data/research/v1_6/ocr_recovery/visual_similarity_predictions.csv`
- `data/research/v1_6/ocr_recovery/visual_similarity_summary.csv`
- `data/research/v1_6/ocr_recovery/manual_label_queue.csv`
- `data/research/v1_6/ocr_recovery/manual_label_queue/`
- `docs/V1.6-LABEL-RECOVERY-EXPERIMENT.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Established quantitative evidence that OCR-only and template-similarity methods are currently insufficient on weak-photo runs.
- Produced a practical path that combines continuity-first automation with a compact human review queue for long-term quality gains.

### 2026-03-02 - Hard-row reviewer UI implemented for low-effort correction loop

User input summary:
- Approved testing the manual-queue approach as an experiment.
- Requested continued exploration while trying this path in practice.

How this changed project direction:
- Implemented a dedicated hard-row reviewer page focused only on difficult OCR rows.
- Added queue-crop rendering (label/center/full), lightweight review fields, local autosave, and reviewed-CSV export.
- Wired the reviewer into normal tracker build and navigation for immediate use.

Artifacts affected:
- `scripts/build_hard_row_reviewer_page.py`
- `tests/test_build_hard_row_reviewer_page.py`
- `tracker/hard-row-reviewer.html`
- `tracker/assets/hard-row-reviewer/`
- `package.json` (`build:tracker` now includes hard-row reviewer generation)
- `tracker/index.html`
- `tracker/README.md`
- `README.md`
- `scripts/create_version_snapshot.py`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Enables a minimal-human-effort correction pass on only high-value hard rows.
- Creates a practical feedback loop: review hard rows, export corrections, rerun experiments, and measure recovery gains.

### 2026-03-02 - Side-by-side pot comparison view added for continuity-error detection

User input summary:
- Requested a direct side-by-side comparison where each `pot_id` is shown across `2026-02-28` and `2026-03-01`.
- Goal was to immediately expose continuity-carried wrong assignments if the same incorrect mapping appears on both days.

How this changed project direction:
- Added a dedicated pot comparison generator and HTML page for cross-run inspection by `pot_id`.
- Added explicit status classes (`risk`, `drift`, `warn`, `ok/info`) with filters to focus review on continuity-lock and drift cases.
- Integrated the comparison build into the normal tracker build path and linked it from tracker navigation.

Artifacts affected:
- `scripts/build_pot_run_comparison_page.py`
- `tests/test_build_pot_run_comparison_page.py`
- `tracker/pot-run-comparison.html`
- `tracker/index.html`
- `tracker/README.md`
- `README.md`
- `scripts/create_version_snapshot.py`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Reduces time to spot false stability caused by continuity reuse.
- Gives a shared visual decision surface for validating mapping quality between consecutive intake days.

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

### 2026-03-02 - Garden CV research briefing ingested and V1.7 execution plan initialized

User input summary:
- Provided a full research-agent briefing covering live findings, assumptions, experiments, sprint sequencing, and success metrics.
- Requested creation of a new branch, upload of that research doc, and start of planning.

How this changed project direction:
- Established a formal V1.7 research track centered on immediate Type 0 diagnosis before any additional reviewer effort.
- Added explicit gate conditions that block architecture and HITL work until OCR root-cause and reviewer-signal honesty issues are addressed.

Artifacts affected:
- `docs/V1.7-GARDEN-CV-RESEARCH-BRIEFING.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Research scope and priorities are now captured in-repo and versioned on a dedicated branch.
- Next engineering step is clear: implement `SW-0`, `SW-0b`, and `HITL-0` support paths before running broader experiments.

### 2026-03-02 - Sprint 0 started: SW-0/SW-0b diagnostics and HITL-0 reviewer UX fix

User input summary:
- Requested committing and pushing planning work, then immediately starting Sprint 0.

How this changed project direction:
- Moved from planning-only to execution by implementing Sprint 0 scripts and producing first-run diagnosis artifacts.
- Upgraded hard-row reviewer UI to explicitly represent signal quality and allow honest no-basis reviewer outcomes.

Artifacts affected:
- `scripts/v17_sw0_ocr_crop_diagnosis.py`
- `scripts/v17_sw0b_reviewer_signal_audit.py`
- `scripts/build_hard_row_reviewer_page.py`
- `tests/test_v17_sw0_ocr_crop_diagnosis.py`
- `tests/test_v17_sw0b_reviewer_signal_audit.py`
- `tests/test_build_hard_row_reviewer_page.py`
- `data/research/v1_7/sw0_ocr_crop_diagnosis.csv`
- `data/research/v1_7/sw0b_signal_quality_audit.csv`
- `data/research/v1_7/sw0b_signal_quality_summary.json`
- `docs/V1.7-SW0-OCR-CROP-DIAGNOSIS.md`
- `docs/V1.7-SW0B-REVIEWER-SIGNAL-AUDIT.md`
- `docs/V1.7-HITL0-REVIEWER-UX-UPDATE.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `tracker/hard-row-reviewer.html`
- `tracker/sw0-ocr-diagnosis-sample.html`

Collaboration impact:
- SW-0b confirmed queue is `100% TYPE_III` (no evidential OCR match variants).
- Reviewer now sees explicit no-signal framing and can mark rows as `No basis - cannot verify from this photo`.
- SW-0 proxy packet is ready for manual crop-confirmation pass before Sprint 1 architecture validation.

### 2026-03-02 - SW-0 manual confirmation completed; Sprint 1 blocked pending crop-target fix

User input summary:
- Requested to proceed to the next step after initial Sprint 0 setup.

How this changed project direction:
- Completed manual validation on sampled SW-0 rows to turn proxy diagnosis into a gate decision.
- Confirmed crop-targeting failure as a primary upstream issue and held Sprint 1 until crop-target adjustment is tested.

Artifacts affected:
- `data/research/v1_7/sw0_ocr_crop_diagnosis.csv` (manual columns filled)
- `docs/V1.7-SW0-OCR-CROP-DIAGNOSIS.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- SW-0 gate is now explicit: do not start SW-1 until crop targeting is corrected and revalidated.
- Immediate implementation focus narrowed to crop-target adjustment experiment and SW-0 rerun.

### 2026-03-02 - New Google Photos batches ingested; suggestion-assisted labeling lane created

User input summary:
- Confirmed two new batches were shared in Google Photos and requested continued forward execution.

How this changed project direction:
- Added immediate ingestion of new album content and rebuilt tracker artifacts on latest intake.
- Added a non-destructive suggestion pipeline for newly ingested unknown rows to reduce manual review load.
- Preserved canonical labeling while creating seeded/provisional outputs for evaluation.

Artifacts affected:
- `data/intake/google_photos/raw_album_page.html`
- `data/intake/google_photos/album_manifest.csv`
- `data/intake/google_photos/manual_mixed_photos.csv`
- `data/intake/google_photos/manual_mixed_photos_labeled_v3.csv`
- `data/intake/processed/tomato_pot_mapping_latest.csv`
- `data/intake/processed/tomato_pot_mapping_report_latest.json`
- `scripts/v17_new_batch_label_suggester.py`
- `tests/test_v17_new_batch_label_suggester.py`
- `data/research/v1_7/new_batch_label_suggestions.csv`
- `data/research/v1_7/new_batch_label_override_seed.csv`
- `data/research/v1_7/new_batch_label_suggestions_summary.json`
- `data/research/v1_7/new_batch_unknown_remaining_review_queue.csv`
- `data/intake/google_photos/manual_label_overrides_v1_seeded.csv`
- `data/research/v1_7/manual_mixed_photos_labeled_seeded.csv`
- `data/research/v1_7/manual_non_tomato_labeled_seeded.csv`
- `data/research/v1_7/tomato_pot_mapping_2026-03-02_seeded.csv`
- `data/research/v1_7/tomato_pot_mapping_report_2026-03-02_seeded.json`
- `docs/V1.7-NEW-BATCH-INTAKE-2026-03-02.md`
- `tracker/*.html` pages rebuilt via `npm run build:tracker`

Collaboration impact:
- New album growth is now accounted for (`+68` assets), with a concrete path to convert unknown rows into review-ready suggestions.
- Remaining blocker is concentrated: `41` low-confidence new rows need explicit human review before reliable mapping conclusions.

### 2026-03-02 - Sprint 0 continuation committed/pushed; SW-1 pilot started

User input summary:
- Requested continued execution ("keep moving") after Sprint 0 and new-batch intake work.

How this changed project direction:
- Converted the accumulated Sprint 0 continuation work into a pushed checkpoint commit.
- Started Sprint 1 by adding a reusable silent-error audit script and running a first pilot pass.
- Explicitly surfaced the current Sprint 1 blocker: weak-run ground truth is still missing.

Artifacts affected:
- `scripts/v17_sw1_silent_error_audit.py`
- `tests/test_v17_sw1_silent_error_audit.py`
- `data/research/v1_7/sw1_silent_error_audit_details.csv`
- `data/research/v1_7/sw1_silent_error_summary.json`
- `docs/V1.7-SW1-SILENT-ERROR-AUDIT.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- Branch progress is now checkpointed on remote at commit `6e9746a`.
- Sprint 1 has executable tooling instead of a plan-only placeholder.
- Gate decision for SW-1 remains pending until we audit weak runs (`2026-02-28`, `2026-03-01`) with explicit truth labels.

### 2026-03-02 - Weak-run SW-1 truth template generated

User input summary:
- Requested continued forward movement without pause.

How this changed project direction:
- Added a concrete reviewer-ready artifact to unblock the SW-1 gate on weak runs.
- Converted the SW-1 blocker from "missing truth" into an actionable CSV review task.

Artifacts affected:
- `scripts/v17_sw1_build_ground_truth_template.py`
- `tests/test_v17_sw1_build_ground_truth_template.py`
- `data/research/v1_7/sw1_weak_run_ground_truth_template.csv`
- `docs/V1.7-SW1-WEAK-RUN-GROUND-TRUTH-TEMPLATE.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- SW-1 weak-run audit is now one reviewer pass away from execution (30 balanced rows across `2026-02-28` and `2026-03-01`).
- Next gate action is explicit and bounded rather than open-ended.

### 2026-03-02 - SW-3 dHash dedup probe executed in parallel

User input summary:
- Requested to continue with the next actionable step.

How this changed project direction:
- Started Sprint 2 parallel probe work while SW-1 waits on weak-run truth labeling.
- Added concrete evidence on dedup ROI so ingestion optimization can be prioritized (or deprioritized) with data.

Artifacts affected:
- `scripts/v17_sw3_dhash_dedup.py`
- `tests/test_v17_sw3_dhash_dedup.py`
- `data/research/v1_7/sw3_dhash_image_hashes.csv`
- `data/research/v1_7/sw3_dhash_clusters_threshold_5.csv`
- `data/research/v1_7/sw3_dhash_clusters_threshold_8.csv`
- `data/research/v1_7/sw3_dhash_clusters_threshold_12.csv`
- `data/research/v1_7/sw3_dhash_summary.csv`
- `data/research/v1_7/sw3_dhash_summary.json`
- `docs/V1.7-SW3-DHASH-DEDUP.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`

Collaboration impact:
- Observed dedup gain is low (`3.66%` at threshold `12`), far below the expected `20-40%` target.
- SW-3 is now evidence-based and can be held as low priority while higher-impact identity work continues.

### 2026-03-02 - Added SW-1 ground-truth reviewer workspace

User input summary:
- Requested to continue to the next step immediately.

How this changed project direction:
- Added a dedicated HTML reviewer page for the SW-1 weak-run truth template to reduce friction in collecting `true_pot_id`.
- Integrated the new page into the tracker build so it stays in sync with template updates.

Artifacts affected:
- `scripts/build_sw1_ground_truth_reviewer_page.py`
- `tests/test_build_sw1_ground_truth_reviewer_page.py`
- `tracker/sw1-ground-truth-reviewer.html`
- `tracker/assets/sw1-ground-truth/*`
- `package.json`
- `tracker/README.md`
- `README.md`
- `docs/V1.7-RESEARCH-EXECUTION-PLAN.md`
- `docs/COLLABORATION-INPUT-LOG.md`

Collaboration impact:
- SW-1 blocker is now operationally simpler: reviewer can fill and export truth labels directly from one page.
- Next execution action remains unchanged: run SW-1 with the reviewed CSV on weak runs and make the gate decision.
