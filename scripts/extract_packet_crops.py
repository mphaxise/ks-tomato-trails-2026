#!/usr/bin/env python3
"""Extract likely seed packet regions from album images."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import cv2


def extract_packet_crop(image_path: Path, output_path: Path) -> bool:
    image = cv2.imread(str(image_path))
    if image is None:
        return False

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0] * image.shape[1]

    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < image_area * 0.01 or area > image_area * 0.8:
            continue
        ratio = w / h
        if ratio < 0.25 or ratio > 2.5:
            continue
        candidates.append((area, x, y, w, h))

    if not candidates:
        return False

    candidates.sort(reverse=True)
    _, x, y, w, h = candidates[0]
    crop = image[y : y + h, x : x + w]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(output_path), crop))


def run(input_dir: Path, output_dir: Path) -> int:
    images = sorted(input_dir.glob("*.jpg"))
    written = 0
    for image_path in images:
        output_path = output_dir / image_path.name
        if extract_packet_crop(image_path, output_path):
            written += 1
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract seed packet crops from downloaded album photos."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory with downloaded full-resolution images",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("local/non_tomato_species/packet_crops"),
        help="Directory to write packet crop images",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    written = run(args.input_dir, args.output_dir)
    print(f"input_dir={args.input_dir}")
    print(f"output_dir={args.output_dir}")
    print(f"packet_crops_written={written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
