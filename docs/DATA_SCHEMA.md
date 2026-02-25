# Data Schema: What to Observe and How

## Overview

Weekly observations take approximately 10–15 minutes for all 12 plants. Each plant gets its own row per week. Observations are logged in CSV format under `data/observations/`.

---

## Observation Log: Field Definitions

### Identification Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `date` | Date | `2026-06-01` | ISO 8601, always Sunday |
| `week_number` | Integer | `3` | Weeks since transplant |
| `variety_id` | String | `stupice` | Snake case, matches varieties.json |
| `plant_id` | String | `stupice_01` | If multiple plants per variety, use _01, _02 |

---

### Growth Metrics

| Field | Type | Scale | Notes |
|---|---|---|---|
| `height_cm` | Integer | cm from soil to growing tip | Measure same plant, same point each week |
| `num_main_stems` | Integer | Count | How many main branches from base |
| `pruned_this_week` | Boolean | true/false | Did you sucker/prune this week? |

---

### Foliage Health Score

**Scale 1–5** (rate overall leaf health, not individual leaves)

| Score | Meaning |
|---|---|
| 5 | Lush, deep green, no damage visible |
| 4 | Mostly healthy, minor yellowing or small spots on lower leaves |
| 3 | Moderate yellowing, some necrotic spots, but majority still green |
| 2 | Significant leaf die-back, large necrotic patches, >30% affected |
| 1 | Severe — plant clearly struggling, major defoliation or collapse |

Field: `foliage_score` (Integer, 1–5)

---

### Fungal Pressure Score

**Scale 1–5** (rate visible fungal/disease symptoms)

| Score | Meaning |
|---|---|
| 1 | No visible disease |
| 2 | Minor spots on a few lower leaves only |
| 3 | Moderate blight/spots on lower 1/3 of plant |
| 4 | Disease progressing into middle/upper canopy |
| 5 | Severe — upper leaves affected, plant likely declining |

Field: `fungal_score` (Integer, 1–5)

Note: Also record the *type* of disease if identifiable:
- `EB` = Early Blight (Alternaria) — brown spots with yellow halos, lower leaves first
- `LB` = Late Blight (Phytophthora) — dark water-soaked lesions, spreads fast
- `Bot` = Botrytis (gray mold) — common in high-humidity fog conditions
- `?` = Unknown

Field: `disease_type` (String, one of: `none`, `EB`, `LB`, `Bot`, `?`)

---

### Fruit Metrics

| Field | Type | Notes |
|---|---|---|
| `flower_count` | Integer | Open flowers visible this week (estimate if >20) |
| `green_fruit_count` | Integer | Actively growing green/unripe fruit on plant |
| `first_fruit_set_date` | Date | One-time entry: date you first saw a fruit forming |
| `ripe_fruit_count` | Integer | Ripe/harvestable fruit this week |
| `harvest_weight_g` | Integer | Grams harvested this week (use kitchen scale) |
| `cumulative_harvest_g` | Integer | Running total grams harvested all season |
| `first_harvest_date` | Date | One-time entry: date of first ripe fruit harvested |

---

### Qualitative Notes

| Field | Type | Notes |
|---|---|---|
| `flavor_score` | Integer (1–10) | Rate flavor of harvested fruit this week. Leave blank if no harvest. |
| `fruit_notes` | String | Cracking? Blossom end rot? Sunscald? Color? Size? |
| `plant_notes` | String | Anything unusual — pest sighting, support issues, weather event |

---

## CSV Template

```csv
date,week_number,variety_id,plant_id,height_cm,num_main_stems,pruned_this_week,foliage_score,fungal_score,disease_type,flower_count,green_fruit_count,first_fruit_set_date,ripe_fruit_count,harvest_weight_g,cumulative_harvest_g,first_harvest_date,flavor_score,fruit_notes,plant_notes
2026-05-10,1,stupice,stupice_01,18,1,false,5,1,none,0,0,,,0,0,,,,Transplanted today
```

One CSV file per variety, named `data/observations/{variety_id}.csv`.

---

## Photo Protocol (Optional but Recommended)

Take one photo per plant per week:
- Same angle, same time of day (morning, after fog lifts)
- Include a date card or write the date on a card visible in frame
- Name files: `{variety_id}_{week_number}_{YYYYMMDD}.jpg`
- Store in `data/photos/{variety_id}/`

Visual records catch disease progression and fruit development that numbers alone don't capture.

---

## Fog Weather Log

Once per week, note the week's overall fog conditions. Store in `data/weather_log.csv`.

| Field | Notes |
|---|---|
| `week_start` | Monday date |
| `fog_days` | How many days this week had fog persisting past noon |
| `est_high_temp` | Estimated average daily high (check weather.gov) |
| `notable_events` | Heat spike, rain, high winds, etc. |

This lets you correlate weekly fruit set data with actual fog intensity — key for the final analysis.
