# V1.4 Manual Calibration Check

- Manual subset rows: `12`
- Survival accuracy: `91.7%`
- Action accuracy: `83.3%`
- Joint accuracy (survival+action): `83.3%`

## Survival Distribution

- Expected: low=5, moderate=7
- Predicted: low=4, moderate=8

## Mismatches

| Pot | Expected Survival | Predicted Survival | Expected Action | Predicted Action |
|---|---|---|---|---|
| 23T | low | moderate | inspect_root_moisture | maintain_current_care |
| 25T | moderate | moderate | maintain_current_care | inspect_root_moisture |
