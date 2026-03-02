#!/usr/bin/env python3
"""Sprint 0: sweep label-crop coordinates and measure OCR match uplift."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import cv2

import v16_ocr_recovery_experiment as v16


@dataclass(frozen=True)
class CropSpec:
    name: str
    x0: float
    x1: float
    y0: float
    y1: float


CANDIDATES: Tuple[CropSpec, ...] = (
    CropSpec("baseline", 0.28, 0.72, 0.45, 0.98),
    CropSpec("wide_lower", 0.20, 0.80, 0.35, 0.98),
    CropSpec("center_tall", 0.25, 0.75, 0.20, 0.95),
    CropSpec("left_tall", 0.15, 0.65, 0.20, 0.95),
    CropSpec("right_tall", 0.35, 0.85, 0.20, 0.95),
    CropSpec("wide_tall", 0.12, 0.88, 0.18, 0.95),
    CropSpec("narrow_top", 0.30, 0.70, 0.10, 0.85),
    CropSpec("broad_top", 0.10, 0.90, 0.12, 0.95),
)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def crop_with_spec(image: cv2.typing.MatLike, spec: CropSpec) -> cv2.typing.MatLike:
    height, width = image.shape[:2]
    x0 = max(0, min(width - 1, int(width * spec.x0)))
    x1 = max(1, min(width, int(width * spec.x1)))
    y0 = max(0, min(height - 1, int(height * spec.y0)))
    y1 = max(1, min(height, int(height * spec.y1)))
    if x1 <= x0 or y1 <= y0:
        return image
    return image[y0:y1, x0:x1]


def extract_numbers_for_crop(crop: cv2.typing.MatLike) -> Tuple[List[int], str]:
    adaptive = v16.to_adaptive_binary(crop, upscale=3.0)
    text_a = v16.ocr_image_with_tesseract(adaptive, psm=6)
    text_b = v16.ocr_image_with_tesseract(adaptive, psm=11)
    numbers = v16.parse_numeric_tokens(f"{text_a} {text_b}".strip())
    return numbers, f"{text_a} || {text_b}".strip()


def evaluate(
    queue_rows: Sequence[Dict[str, str]],
    candidates: Sequence[CropSpec],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    detail_rows: List[Dict[str, object]] = []
    summary_map: Dict[str, Dict[str, int]] = {
        c.name: {
            "total_rows": 0,
            "rows_with_digits": 0,
            "rows_with_match": 0,
            "rows_missing_image": 0,
            "sum_detected_numbers": 0,
        }
        for c in candidates
    }

    for row in queue_rows:
        expected = parse_int(row.get("pot_number", "0") or "0", default=0)
        image_path = Path((row.get("image_path", "") or "").strip())
        image = cv2.imread(str(image_path)) if image_path.exists() else None

        for spec in candidates:
            summary = summary_map[spec.name]
            summary["total_rows"] += 1
            if image is None:
                summary["rows_missing_image"] += 1
                detail_rows.append(
                    {
                        "candidate": spec.name,
                        "run_date": (row.get("run_date", "") or "").strip(),
                        "row_index": (row.get("row_index", "") or "").strip(),
                        "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                        "expected_pot_number": expected,
                        "detected_numbers": "",
                        "detected_count": 0,
                        "match": 0,
                        "image_missing": 1,
                        "ocr_text_preview": "",
                    }
                )
                continue

            crop = crop_with_spec(image, spec)
            numbers, preview = extract_numbers_for_crop(crop)
            has_digits = 1 if numbers else 0
            match = 1 if expected > 0 and expected in set(numbers) else 0

            summary["rows_with_digits"] += has_digits
            summary["rows_with_match"] += match
            summary["sum_detected_numbers"] += len(numbers)

            detail_rows.append(
                {
                    "candidate": spec.name,
                    "run_date": (row.get("run_date", "") or "").strip(),
                    "row_index": (row.get("row_index", "") or "").strip(),
                    "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                    "expected_pot_number": expected,
                    "detected_numbers": ",".join(str(v) for v in numbers),
                    "detected_count": len(numbers),
                    "match": match,
                    "image_missing": 0,
                    "ocr_text_preview": preview[:180],
                }
            )

    summary_rows: List[Dict[str, object]] = []
    for spec in candidates:
        summary = summary_map[spec.name]
        total = summary["total_rows"]
        match_rate = (summary["rows_with_match"] / total * 100.0) if total else 0.0
        digits_rate = (summary["rows_with_digits"] / total * 100.0) if total else 0.0
        avg_numbers = (summary["sum_detected_numbers"] / total) if total else 0.0
        summary_rows.append(
            {
                "candidate": spec.name,
                "x0": spec.x0,
                "x1": spec.x1,
                "y0": spec.y0,
                "y1": spec.y1,
                "total_rows": total,
                "rows_with_digits": summary["rows_with_digits"],
                "rows_with_match": summary["rows_with_match"],
                "rows_missing_image": summary["rows_missing_image"],
                "digits_rate_pct": round(digits_rate, 2),
                "match_rate_pct": round(match_rate, 2),
                "avg_detected_numbers": round(avg_numbers, 3),
            }
        )

    summary_rows.sort(
        key=lambda row: (
            -float(row.get("match_rate_pct", 0.0) or 0.0),
            -float(row.get("digits_rate_pct", 0.0) or 0.0),
            str(row.get("candidate", "")),
        )
    )
    return detail_rows, summary_rows


def build_markdown(summary_rows: Sequence[Dict[str, object]], queue_csv: Path) -> str:
    lines = [
        "# V1.7 SW-0 Crop-Target Sweep",
        "",
        f"Input queue: `{queue_csv}`",
        "",
        "## Candidate Ranking",
        "",
        "| Candidate | x0 | x1 | y0 | y1 | Match % | Digits % | Match Rows | Total |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                row["candidate"],
                row["x0"],
                row["x1"],
                row["y0"],
                row["y1"],
                row["match_rate_pct"],
                row["digits_rate_pct"],
                row["rows_with_match"],
                row["total_rows"],
            )
        )

    if summary_rows:
        best = summary_rows[0]
        lines.extend(
            [
                "",
                "## Recommendation",
                "",
                "- Best candidate by match rate: `{}` (match={}%, digits={}%).".format(
                    best["candidate"],
                    best["match_rate_pct"],
                    best["digits_rate_pct"],
                ),
                "- Rebuild label crops with this candidate and rerun SW-0/SW-0b before SW-1.",
            ]
        )

    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep label-crop coordinates and evaluate OCR match uplift.",
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/manual_label_queue.csv"),
        help="Input hard-row queue CSV.",
    )
    parser.add_argument(
        "--output-detail-csv",
        type=Path,
        default=Path("data/research/v1_7/sw0_crop_target_sweep_details.csv"),
        help="Per-row per-candidate detail output.",
    )
    parser.add_argument(
        "--output-summary-csv",
        type=Path,
        default=Path("data/research/v1_7/sw0_crop_target_sweep_summary.csv"),
        help="Per-candidate summary output.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.7-SW0-CROP-TARGET-SWEEP.md"),
        help="Markdown summary output.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    queue_rows = read_csv_rows(args.queue_csv)
    detail_rows, summary_rows = evaluate(queue_rows, CANDIDATES)

    write_csv(
        args.output_detail_csv,
        detail_rows,
        fieldnames=[
            "candidate",
            "run_date",
            "row_index",
            "source_asset_id",
            "expected_pot_number",
            "detected_numbers",
            "detected_count",
            "match",
            "image_missing",
            "ocr_text_preview",
        ],
    )
    write_csv(
        args.output_summary_csv,
        summary_rows,
        fieldnames=[
            "candidate",
            "x0",
            "x1",
            "y0",
            "y1",
            "total_rows",
            "rows_with_digits",
            "rows_with_match",
            "rows_missing_image",
            "digits_rate_pct",
            "match_rate_pct",
            "avg_detected_numbers",
        ],
    )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(summary_rows, args.queue_csv), encoding="utf-8")

    print(f"queue_rows={len(queue_rows)}")
    print(f"detail_rows={len(detail_rows)}")
    print(f"output_detail_csv={args.output_detail_csv}")
    print(f"output_summary_csv={args.output_summary_csv}")
    print(f"output_md={args.output_md}")
    if summary_rows:
        top = summary_rows[0]
        print(
            "best_candidate={} match_rate_pct={} digits_rate_pct={}".format(
                top["candidate"],
                top["match_rate_pct"],
                top["digits_rate_pct"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
