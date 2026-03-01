# Bugfix Issues

Created on 2026-02-28 for the `codex/bugfix-lightbox-issue-1` branch.

## Issue 1 - Lightbox clipped on laptop viewport
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `tracker/v1-4-cv-research.html` lightbox layout
- Problem: Photo and bottom nav controls (Previous/Next) are partially or fully below the fold on laptop screens.
- Goal: Ensure the full photo fits in the visible lightbox area and navigation controls remain visible at all times.

## Issue 2 - Add lightbox photo zoom interaction
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `tracker/v1-4-cv-research.html` lightbox image interaction
- Problem: No zoom interaction in lightbox for close inspection.
- Goal: Add practical zoom controls (desktop + laptop friendly).

## Issue 3 - Plants identified per pot appears incorrect
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: V1.4 metric generation/display for `plant_count_estimate`
- Problem: Displayed plants count does not match expected real-world count for some pots.
- Goal: Audit plant count derivation and correct displayed values.

## Issue 4 - Show Pot ID in details
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: Pot detail panel fields
- Problem: Pot ID should be explicitly shown as a dedicated detail field.
- Goal: Add a clear Pot ID field in the details list for each pot.

## Issue 5 - V1.4 pipeline date mixing
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/v14_cv_research_pipeline.py`
- Problem: Pipeline mixed rows from multiple capture dates into one run.
- Goal: Process only rows from the latest run date selected for that pipeline execution.

## Issue 6 - V1.4 duplicate pot ID details mismatch
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/build_v14_cv_research_page.py` lightbox row lookup
- Problem: Details panel lookup keyed only by `pot_id` could show wrong data when duplicate pot IDs exist.
- Goal: Tie details lookup to card row index so lightbox details always match clicked card.

## Issue 7 - Lightbox clipping in mixed view page
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/build_experiment_trails_page.py`
- Problem: Image/meta/nav stack could exceed viewport on laptop and clip controls.
- Goal: Constrain lightbox shell/panel sizing to keep full photo and nav controls visible.

## Issue 8 - Lightbox clipping in label editor page
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/build_experiment_trails_label_editor_page.py`
- Problem: Same clipping behavior as mixed view page under constrained laptop heights.
- Goal: Apply same constrained lightbox layout approach for editor modal.

## Issue 9 - Label editor saved-state row drift
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/build_experiment_trails_label_editor_page.py` browser storage load
- Problem: Saved edits were re-applied by array index only, causing wrong-row merge after reordering.
- Goal: Load saved edits by stable keys (`source_asset_id`, fallback `row_index`) instead of index position.

## Issue 10 - Tomato page title and filtering correctness
- Status: Fixed in branch `codex/bugfix-lightbox-issue-1`
- Scope: `scripts/build_tomato_trails_page.py`
- Problem: Output title stayed generic and non-tomato rows on run date could be forced into tomato view.
- Goal: Ensure tomato-specific title is rendered and non-tomato rows are excluded from tomato run output.
