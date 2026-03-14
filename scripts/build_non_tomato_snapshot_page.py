#!/usr/bin/env python3
"""Build a view-only non-tomato snapshot page."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Dict

from build_experiment_trails_page import build_page, read_rows
from stable_generated_output import stabilize_rendered_text, write_text_if_changed


def filter_non_tomato(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in rows
        if (row.get("classification_label", "") or "").strip() == "non_tomato"
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build non-tomato snapshot HTML from labeled CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_non_tomato_labeled_v3.csv"),
        help="CSV containing non-tomato (or mixed) labeled rows",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/non-tomato-snapshot.html"),
        help="Output HTML file",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = read_rows(args.input_csv)
    non_tomato_rows = filter_non_tomato(rows)
    page = build_page(non_tomato_rows, args.input_csv)
    page = page.replace(
        "K's Experiment Trails 2026: View-Only Catalog",
        "K's Non-Tomato Snapshot: View-Only",
    ).replace(
        "Read-only photo catalog with canonical variety, taxonomy, weather hypothesis, and harvest window fields.",
        "Snapshot archive of non-tomato plants retained for reference while the active project focuses on tomato pots.",
    )

    page = stabilize_rendered_text(args.output_html, page)
    write_text_if_changed(args.output_html, page)

    print(f"input_csv={args.input_csv}")
    print(f"rows={len(rows)}")
    print(f"non_tomato_rows={len(non_tomato_rows)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
