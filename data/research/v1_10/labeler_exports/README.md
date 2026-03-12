## V1.10 Seed Labeler Exports

Drop exported JSON files from `tracker/single-photo-seed-labeler.html` into this folder.

Then refresh the status and ingest artifacts:

```bash
python3 scripts/v110_seed_label_annotation_status.py
python3 scripts/build_v110_seed_annotation_status_page.py
python3 scripts/v111_seed_annotation_ingest.py
python3 scripts/build_v111_seed_annotation_ingest_page.py
```

The refreshed outputs land in:
- `data/research/v1_10/seed_label_annotation_manifest.csv`
- `data/research/v1_10/seed_label_annotation_summary.json`
- `docs/V1.10-SEED-LABEL-ANNOTATION-STATUS.md`
- `tracker/v1-10-seed-annotation-status.html`
- `data/research/v1_11/seed_annotation_ingest_manifest.csv`
- `data/research/v1_11/seed_annotation_box_rows.csv`
- `data/research/v1_11/seed_annotation_ingest_summary.json`
- `docs/V1.11-SEED-ANNOTATION-INGEST.md`
- `tracker/v1-11-seed-annotation-ingest.html`
