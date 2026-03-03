#!/usr/bin/env python3
"""Ingest a quick-multi-photo export into per-row v1.8 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

from v18_quick_seed_pair_resolver import (
    build_markdown as resolver_markdown,
    load_pot_series_map,
    load_series_map,
    resolve_seed,
    write_json,
)
from v18_strategy_from_quick_seed import (
    strategy_markdown,
    summarize,
)


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_token(text: str, fallback: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return fallback
    out = []
    for ch in raw:
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or fallback


def single_seed_from_photo(
    payload: Dict[str, object], photo: Dict[str, object], fallback_row_index: int
) -> Dict[str, object]:
    capture_date = str(photo.get("capture_date", "") or payload.get("capture_date", "") or "").strip()
    row_index = str(photo.get("row_index", "") or str(fallback_row_index)).strip()
    source_asset_id = str(photo.get("source_asset_id", "") or "").strip()
    photo_url = str(photo.get("photo_url", "") or "").strip()
    boxes = photo.get("boxes", [])
    if not isinstance(boxes, list):
        boxes = []
    return {
        "version": "quick-single-photo-v1",
        "saved_at_utc": str(payload.get("saved_at_utc", "") or ""),
        "capture_date": capture_date,
        "row_index": row_index,
        "source_asset_id": source_asset_id,
        "photo_url": photo_url,
        "boxes": boxes,
    }


def ingest_multi_export(
    input_json: Path,
    output_seed_dir: Path,
    output_data_dir: Path,
    output_docs_dir: Path,
    series_map_csv: Path,
    pot_overrides_csv: Path,
    baseline_mapping_csv: Path,
) -> Dict[str, object]:
    payload = read_json(input_json)
    photos = payload.get("photos", [])
    if not isinstance(photos, list):
        photos = []

    series_map = load_series_map(series_map_csv)
    pot_series_map = load_pot_series_map(pot_overrides_csv, baseline_mapping_csv)

    processed_rows: List[Dict[str, object]] = []
    skipped_rows = 0

    for i, photo in enumerate(photos, start=1):
        if not isinstance(photo, dict):
            skipped_rows += 1
            continue
        seed = single_seed_from_photo(payload, photo, fallback_row_index=i)
        source_asset_id = str(seed.get("source_asset_id", "") or "").strip()
        capture_date = str(seed.get("capture_date", "") or "").strip()
        row_index = str(seed.get("row_index", "") or "").strip()
        boxes = seed.get("boxes", [])
        if not source_asset_id or not capture_date or not isinstance(boxes, list) or len(boxes) == 0:
            skipped_rows += 1
            continue

        capture_token = sanitize_token(capture_date, "unknown_date")
        row_token = sanitize_token(row_index, f"row_{i}")
        asset_token = sanitize_token(source_asset_id[:12], "asset")

        seed_out = (
            output_seed_dir
            / f"quick_seed_{capture_token}_{row_token}_{asset_token}.json"
        )
        write_json(seed_out, seed)

        summary = summarize(seed)
        summary_out = output_data_dir / f"quick_seed_strategy_summary_{capture_token}_{row_token}.json"
        write_json(summary_out, summary)

        summary_md_out = output_docs_dir / f"V1.8-STRATEGY-FROM-QUICK-SEED-{capture_token}-{row_token}.md"
        summary_md_out.parent.mkdir(parents=True, exist_ok=True)
        summary_md_out.write_text(
            strategy_markdown(summary, seed_out, summary_out), encoding="utf-8"
        )

        resolution = resolve_seed(seed, pot_series_map=pot_series_map, series_map=series_map)
        resolution_out = output_data_dir / f"quick_seed_pair_resolution_{capture_token}_{row_token}.json"
        write_json(resolution_out, resolution)

        resolution_md_out = output_docs_dir / f"V1.8-QUICK-SEED-PAIR-RESOLUTION-{capture_token}-{row_token}.md"
        resolution_md_out.parent.mkdir(parents=True, exist_ok=True)
        resolution_md_out.write_text(
            resolver_markdown(resolution, seed_out, resolution_out), encoding="utf-8"
        )

        processed_rows.append(
            {
                "capture_date": capture_date,
                "row_index": row_index,
                "source_asset_id": source_asset_id,
                "boxes": len(boxes),
                "seed_json": str(seed_out),
                "strategy_json": str(summary_out),
                "pair_json": str(resolution_out),
            }
        )

    processed_rows.sort(
        key=lambda row: (
            str(row.get("capture_date", "")),
            int(str(row.get("row_index", "0") or "0")),
            str(row.get("source_asset_id", "")),
        )
    )

    return {
        "input_json": str(input_json),
        "photos_total": len(photos),
        "photos_processed": len(processed_rows),
        "photos_skipped": skipped_rows,
        "rows": processed_rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest quick-multi-photo export into per-row v1.8 artifacts."
    )
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument(
        "--output-seed-dir",
        type=Path,
        default=Path("data/research/v1_8/imported_seeds"),
    )
    parser.add_argument(
        "--output-data-dir",
        type=Path,
        default=Path("data/research/v1_8"),
    )
    parser.add_argument(
        "--output-docs-dir",
        type=Path,
        default=Path("docs"),
    )
    parser.add_argument(
        "--series-map-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_series_map.csv"),
    )
    parser.add_argument(
        "--pot-overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_tomato_pot_series_overrides.csv"),
    )
    parser.add_argument(
        "--baseline-mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
    )
    parser.add_argument(
        "--manifest-json",
        type=Path,
        default=Path("data/research/v1_8/quick_seed_multi_ingest_manifest.json"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest = ingest_multi_export(
        input_json=args.input_json,
        output_seed_dir=args.output_seed_dir,
        output_data_dir=args.output_data_dir,
        output_docs_dir=args.output_docs_dir,
        series_map_csv=args.series_map_csv,
        pot_overrides_csv=args.pot_overrides_csv,
        baseline_mapping_csv=args.baseline_mapping_csv,
    )
    write_json(args.manifest_json, manifest)

    print(f"input_json={manifest['input_json']}")
    print(f"photos_total={manifest['photos_total']}")
    print(f"photos_processed={manifest['photos_processed']}")
    print(f"photos_skipped={manifest['photos_skipped']}")
    print(f"manifest_json={args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
