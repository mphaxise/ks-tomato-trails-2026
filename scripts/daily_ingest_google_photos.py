#!/usr/bin/env python3
"""Run daily Google Photos intake + quick labeler refresh in one command."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List


def run_cmd(cmd: List[str]) -> None:
    print(f"+ {' '.join(shlex.quote(part) for part in cmd)}")
    subprocess.run(cmd, check=True)


def read_album_url(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"album URL file is empty: {path}")
    return raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run daily Google Photos intake and refresh quick labeler pages."
    )
    parser.add_argument(
        "--album-url-file",
        type=Path,
        default=Path("data/intake/google_photos/album_url.txt"),
        help="Text file containing shared Google Photos album URL.",
    )
    parser.add_argument(
        "--raw-html-output",
        type=Path,
        default=Path("data/intake/google_photos/raw_album_page.html"),
        help="Path for raw album HTML fetched by curl.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("data/intake/google_photos/album_manifest.csv"),
        help="Detailed album manifest CSV output.",
    )
    parser.add_argument(
        "--mixed-output",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos.csv"),
        help="Mixed intake CSV output.",
    )
    parser.add_argument(
        "--image-output-dir",
        type=Path,
        default=Path("local/non_tomato_species/images"),
        help="Directory for downloaded images.",
    )
    parser.add_argument(
        "--packet-crop-dir",
        type=Path,
        default=Path("local/non_tomato_species/packet_crops"),
        help="Directory for extracted packet crops.",
    )
    parser.add_argument(
        "--labeled-output",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos_labeled_v3.csv"),
        help="Labeled mixed CSV output.",
    )
    parser.add_argument(
        "--non-tomato-output",
        type=Path,
        default=Path("data/intake/google_photos/manual_non_tomato_labeled_v3.csv"),
        help="Non-tomato-only labeled CSV output.",
    )
    parser.add_argument(
        "--overrides-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_label_overrides_v1.csv"),
        help="Manual label overrides CSV.",
    )
    parser.add_argument(
        "--run-date",
        default="",
        help="Optional capture date for image downloads (YYYY-MM-DD). Defaults to latest date.",
    )
    parser.add_argument(
        "--all-dates",
        action="store_true",
        help="Download all dates instead of only selected run date.",
    )
    parser.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip already-downloaded files (default: true).",
    )
    parser.add_argument(
        "--skip-labeling",
        action="store_true",
        help="Skip packet crop + OCR labeling steps.",
    )
    parser.add_argument(
        "--skip-labeler-pages",
        action="store_true",
        help="Skip rebuilding single/multi quick labeler HTML pages.",
    )
    parser.add_argument(
        "--skip-monitor",
        action="store_true",
        help="Skip manifest monitor delta logging.",
    )
    parser.add_argument(
        "--monitor-state-json",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_state.json"),
        help="Persistent monitor state JSON (previous snapshot baseline).",
    )
    parser.add_argument(
        "--monitor-report-json",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_latest.json"),
        help="Latest monitor report JSON output.",
    )
    parser.add_argument(
        "--monitor-history-csv",
        type=Path,
        default=Path("data/intake/google_photos/manifest_monitor_history.csv"),
        help="Append-only monitor history CSV output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    py = sys.executable
    album_url = read_album_url(args.album_url_file)

    args.raw_html_output.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            "curl",
            "-sS",
            "-L",
            "-A",
            "Mozilla/5.0",
            album_url,
            "-o",
            str(args.raw_html_output),
        ]
    )

    run_cmd(
        [
            py,
            "scripts/extract_google_photos_public_album.py",
            "--html-input",
            str(args.raw_html_output),
            "--album-url",
            album_url,
            "--manifest-output",
            str(args.manifest_output),
            "--mixed-output",
            str(args.mixed_output),
            "--raw-html-output",
            str(args.raw_html_output),
        ]
    )

    if not args.skip_monitor:
        run_cmd(
            [
                py,
                "scripts/monitor_google_photos_manifest.py",
                "--manifest-csv",
                str(args.manifest_output),
                "--state-json",
                str(args.monitor_state_json),
                "--report-json",
                str(args.monitor_report_json),
                "--history-csv",
                str(args.monitor_history_csv),
            ]
        )

    download_cmd = [
        py,
        "scripts/download_google_photos_images.py",
        "--input-csv",
        str(args.mixed_output),
        "--output-dir",
        str(args.image_output_dir),
    ]
    if args.run_date.strip():
        download_cmd.extend(["--run-date", args.run_date.strip()])
    if args.all_dates:
        download_cmd.append("--all-dates")
    if args.skip_existing:
        download_cmd.append("--skip-existing")
    else:
        download_cmd.append("--no-skip-existing")
    run_cmd(download_cmd)

    if not args.skip_labeling:
        run_cmd(
            [
                py,
                "scripts/extract_packet_crops.py",
                "--input-dir",
                str(args.image_output_dir),
                "--output-dir",
                str(args.packet_crop_dir),
            ]
        )

        run_cmd(
            [
                py,
                "scripts/label_non_tomato_from_images.py",
                "--mixed-csv",
                str(args.mixed_output),
                "--output-csv",
                str(args.labeled_output),
                "--non-tomato-csv",
                str(args.non_tomato_output),
                "--overrides-csv",
                str(args.overrides_csv),
            ]
        )

    if not args.skip_labeler_pages:
        run_cmd([py, "scripts/build_single_photo_quick_labeler_page.py"])
        run_cmd([py, "scripts/build_multi_photo_quick_labeler_page.py"])

    print("daily_ingest_complete=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
