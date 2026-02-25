# Observations

One CSV file per variety. Name each file `{variety_id}.csv` matching the IDs in `varieties.json`.

Example filenames:
- `stupice.csv`
- `glacier.csv`
- `siletz.csv`
- etc.

See `docs/DATA_SCHEMA.md` for the full field definitions and CSV column headers.

## CSV Header (copy this into each new file)

```
date,week_number,variety_id,plant_id,height_cm,num_main_stems,pruned_this_week,foliage_score,fungal_score,disease_type,flower_count,green_fruit_count,first_fruit_set_date,ripe_fruit_count,harvest_weight_g,cumulative_harvest_g,first_harvest_date,flavor_score,fruit_notes,plant_notes
```
