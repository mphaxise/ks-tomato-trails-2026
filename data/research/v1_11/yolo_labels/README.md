## V1.11 YOLO Label Outputs

This directory is populated by `python3 scripts/v111_seed_annotation_ingest.py`.

Each ready-for-training task writes one `*.txt` file here using YOLO box format:

```text
<class_id> <x_center_norm> <y_center_norm> <w_norm> <h_norm>
```

The directory is empty right now because the current v1.10 seed annotation queue still has `0` completed tasks.
