# Phase 1 Landing Experiment

Date: `2026-03-14`

## Goals

- Keep `tracker/index.html` intact and redesign the main tomato trails page around the locked Phase 1 seedling story.
- Lead every pot card with the `Last Day of Phase 1` image, but let the card flip back to `Day 1 of Phase 1`.
- Use the large detail view for side-by-side images, varietal expectations, Sausalito fog context, and the current growth assessment.
- Preserve the existing Phase 1 lock, manual photo analysis, and pot-level CV work instead of treating this as a blank-slate redesign.

## Canonical Inputs Used

- Phase lock and labels:
  - `docs/V1.14-PHASE-ONE-SEEDLING-LOCK.md`
  - `data/intake/google_photos/manual_phase_timeline.csv`
- Manual phase-pair analysis:
  - `docs/V1.14-PHASE1-PHOTO-ANALYSIS.md`
  - `data/research/phase1_day1_vs_lastday_manual_triage.csv`
- Pot-level CV guidance:
  - `docs/V1.10-POT-CV-EXPERIMENT.md`
  - `data/research/v1_10/pot_cv_metrics.csv`
- Climate context to preserve:
  - `docs/CLIMATE_RESEARCH.md`

## Product Read

The page should behave like a Phase 1 story board rather than a generic gallery:

1. Explain what Tomato Trails is and why Sausalito fog matters.
2. Make the current stage explicit: Phase 1 is the seedling-establishment chapter.
3. Call out the locked anchor window:
   - `Day 1 of Phase 1` = `2026-02-27`
   - `Last Day of Phase 1` = `2026-03-11`
   - `12` days between the anchor captures
4. Let the user scan the end-state first, then flip back to the baseline.
5. In the detail view, keep both images visible at once and layer in:
   - phase bucket
   - varietal expectation in Sausalito fog
   - current manual assessment
   - current CV readiness and next-step note

## Computer Vision Strategy

### What is already reliable

- Manual visual establishment buckets across the locked pair set
- Watchlist generation
- Selection of strong reference pots for future modeling
- Pot-level framing quality signals from the v1.10 CV run

### What should measure growth next

1. **Standardize capture first**
   - Keep camera distance, pot placement, and framing more consistent across runs.
   - Add a scale cue when possible.

2. **Register the image pair before measuring anything**
   - Use feature matching + homography when perspective changes are visible.
   - Use ECC alignment as a fallback when the pose difference is smaller and mostly translational/affine.

3. **Measure only inside the target pot**
   - Reuse the pot-mask / pot-polygon direction from the v1.10 work.
   - The measurement target should be in-pot canopy, not whole-image greenery, because neighbor spill is already a known failure mode.

4. **Track a small set of robust metrics**
   - in-pot canopy coverage
   - neighbor spill ratio
   - in-pot spill ratio
   - plant count / multi-stem signal
   - chlorosis / visible stress hints
   - data-quality flags for blur, brightness, and framing drift

5. **Keep the manual bucket as the truth layer until capture quality improves**
   - The current pair set is good for directional growth language.
   - It is not yet good enough for precise biomass or cross-pot size claims.

## Recommendation on Vision-Language Models

Use a VLM, but not as the primary measurement engine.

### Good use cases

- Compare two photos and draft a qualitative note about visible progression
- Call out legginess, empty pots, mold-looking media, or multi-stem competition
- Help produce human-readable summaries once the numeric CV metrics already exist

### Poor primary use cases

- Numeric growth scoring
- Pixel-accurate area estimation
- Trustworthy counting or spatial measurement without a separate CV pipeline

The safest stack is:

1. image registration
2. pot isolation / segmentation
3. numeric growth metrics
4. VLM commentary and QA on top

## External References

- OpenCV feature matching + homography tutorial:
  - [https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html](https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html)
- OpenCV ECC alignment reference:
  - [https://docs.opencv.org/4.x/dc/d6b/group__video__track.html#ga473e4b886d0bcc6b65831eb88ed93323](https://docs.opencv.org/4.x/dc/d6b/group__video__track.html#ga473e4b886d0bcc6b65831eb88ed93323)
- PlantCV object finding:
  - [https://plantcv.readthedocs.io/en/stable/find_objects/](https://plantcv.readthedocs.io/en/stable/find_objects/)
- PlantCV shape analysis:
  - [https://plantcv.readthedocs.io/en/stable/analyze_shape/](https://plantcv.readthedocs.io/en/stable/analyze_shape/)
- OpenAI Images and Vision guide:
  - [https://platform.openai.com/docs/guides/images-vision](https://platform.openai.com/docs/guides/images-vision)

## Decision Summary

- The new page should present the locked manual Phase 1 story now.
- The CV layer should stay visible as a research-backed strategy and readiness signal.
- A VLM should help with commentary, not replace the image-registration + in-pot measurement pipeline.
