# Strategy Document: Fog Tomato Trials

## Project Goal

Determine which of 12 tomato varieties reliably produce fruit in Sausalito's coastal fog-belt microclimate — and generate reusable knowledge for other Bay Area fog-zone growers.

---

## The Core Problem

Tomatoes need heat. Most varieties require 60–70+ "heat days" (days above 65°F) to set and ripen fruit. Sausalito's fog belt routinely delivers summers where June, July, and August highs stay in the 58–68°F range, with persistent morning fog burning off late or not at all.

The result: most tomato varieties stall, drop blossoms without fruiting, develop fungal disease, or produce fruit that never ripens before the first fall rains arrive in October.

**The question we're answering:** Which varieties beat this pattern?

---

## Experimental Design

### Type: Controlled Observational Trial

This is not a true randomized controlled experiment — that would require identical growing conditions per plant. Instead, this is a **structured observational trial**: all 12 varieties grown by the same grower, in the same general garden, in the same season, under the same care regime.

This controls for:
- Grower behavior (watering, fertilizing, staking, pruning)
- Macro-climate (all plants experience the same fog events)
- Soil baseline (same amendment regime applied before planting)

It does **not** control for:
- Micro-positioning (some spots may get more sun)
- Soil pockets (slight variation plant-to-plant)
- Random pest/disease events

### Sample Size

- 1–2 plants per variety (note if replicated)
- 12 varieties = 12–24 data streams

### Duration

- **Transplant date:** Target late April / early May (after last frost risk)
- **Active observation window:** May through October
- **End-of-season scoring:** First week of November

---

## Hypothesis

We expect to find a clear performance cluster:

| Tier | Expected % of varieties | Characteristics |
|---|---|---|
| Fog winners | ~25% (3 varieties) | Early ripening, disease resistant, full fruit set |
| Marginal performers | ~40% (5 varieties) | Some fruit, significant disease or late ripening |
| Fog failures | ~35% (4 varieties) | Blossom drop, no ripening, heavy blight |

The goal is to validate or disprove this and identify exactly which varieties land in each tier.

---

## Key Research Questions

1. Which varieties produce ripe fruit before October 15th?
2. Which varieties show least fungal pressure (early/late blight, botrytis)?
3. Is there a correlation between variety origin climate and fog performance?
4. Does cherry/small-fruited vs. large-fruited predict success?
5. Does Days-to-Maturity (DTM) on the seed packet predict actual performance in fog?

---

## Data Collection Strategy

**Frequency:** Weekly observations, every 7 days, same day of week.

**Key measurements per plant:**
- Plant height (cm)
- Foliage health score (1–5 scale)
- Fungal pressure score (1–5 scale)
- Flower count (approximate)
- Fruit set count (green fruit forming)
- Ripe fruit count
- Harvest weight (grams, cumulative)

Full schema in `DATA_SCHEMA.md`.

---

## Success Definition

At season's end, each variety receives a **Fog Belt Score** (0–100) composite across:
- Fruit yield (weight and count)
- Ripening speed (days to first ripe fruit)
- Disease resistance
- Flavor (subjective 1–10 score)
- Plant vigor

Full scoring rubric in `SUCCESS_METRICS.md`.

---

## Output Deliverables

1. **Season log:** Complete weekly observation data for all 12 varieties
2. **End-of-season report:** Fog Belt Score rankings with narrative
3. **Grower's guide:** Top 3 recommended varieties for Sausalito/Marin fog-belt gardens
4. **Data file:** CSV export for future growers and comparison with other fog-zone gardens

---

## Timeline

| Milestone | Target Date |
|---|---|
| Variety registration complete | April 15, 2026 |
| Transplant to garden | Late April / Early May |
| Week 1 baseline observation | 7 days post-transplant |
| First fruit set expected | July (fog-tolerant) / Aug (others) |
| First harvest | July–August (fog-tolerant varieties) |
| Final harvest | October 15, 2026 |
| End-of-season scoring | November 1, 2026 |
| Grower's report complete | November 15, 2026 |
