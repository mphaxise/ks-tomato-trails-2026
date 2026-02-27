#!/usr/bin/env python3
"""Extract photo metadata from a public Google Photos shared album page."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


MANIFEST_FIELDS = [
    "album_title",
    "album_id",
    "album_url",
    "album_url_with_key",
    "album_short_url",
    "photo_index",
    "source_asset_id",
    "photo_url",
    "width",
    "height",
    "capture_ms",
    "captured_at",
    "capture_date",
    "timezone_offset_minutes",
    "uploaded_ms",
    "uploaded_at",
    "device_make",
    "device_model",
    "owner_key",
]

MIXED_FIELDS = [
    "photo_url",
    "caption",
    "capture_date",
    "captured_at",
    "uploaded_at",
    "timezone",
    "latitude",
    "longitude",
    "device_model",
    "notes",
    "source_asset_id",
    "source_platform",
]


def fetch_html(album_url: str) -> str:
    request = urllib.request.Request(
        album_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_json_array_after_data(html: str, ds_key: str) -> str:
    needle = f"AF_initDataCallback({{key: '{ds_key}'"
    start_idx = html.find(needle)
    if start_idx < 0:
        raise ValueError(f"Could not find {ds_key} callback in HTML")

    data_idx = html.find("data:", start_idx)
    if data_idx < 0:
        raise ValueError(f"Could not find data: segment for {ds_key}")

    array_start = html.find("[", data_idx)
    if array_start < 0:
        raise ValueError(f"Could not find opening '[' for {ds_key} payload")

    index = array_start
    depth = 0
    in_string = False
    escape = False
    while index < len(html):
        ch = html[index]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return html[array_start : index + 1]
        index += 1

    raise ValueError(f"Unterminated JSON array for {ds_key}")


def parse_ds1_payload(html: str) -> List[Any]:
    payload_raw = extract_json_array_after_data(html, "ds:1")
    payload = json.loads(payload_raw)
    if not isinstance(payload, list) or len(payload) < 4:
        raise ValueError("Unexpected ds:1 payload shape")
    return payload


def to_iso_utc_from_ms(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def to_iso_local_from_ms(value: Any, offset_ms: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if not isinstance(offset_ms, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()

    offset = timezone(timedelta(milliseconds=offset_ms))
    return datetime.fromtimestamp(value / 1000, tz=offset).isoformat()


def offset_to_timezone_string(offset_ms: Any) -> str:
    if not isinstance(offset_ms, (int, float)):
        return ""
    minutes_total = int(offset_ms // 60000)
    sign = "+" if minutes_total >= 0 else "-"
    absolute = abs(minutes_total)
    hours = absolute // 60
    minutes = absolute % 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def safe_get_list(value: Any, index: int, default: Any = None) -> Any:
    if not isinstance(value, list):
        return default
    if index < 0 or index >= len(value):
        return default
    return value[index]


def parse_album_rows(ds1_payload: List[Any], album_url_input: str) -> Dict[str, Any]:
    photos = safe_get_list(ds1_payload, 1, []) or []
    album_meta = safe_get_list(ds1_payload, 3, []) or []

    album_id = safe_get_list(album_meta, 0, "")
    album_title = safe_get_list(album_meta, 1, "")
    auth_key = safe_get_list(album_meta, 19, "")
    album_short_url = safe_get_list(album_meta, 32, "")
    album_url_with_key = (
        f"https://photos.google.com/share/{album_id}?key={auth_key}"
        if album_id and auth_key
        else ""
    )
    album_url = f"https://photos.google.com/share/{album_id}" if album_id else album_url_input

    manifest_rows: List[Dict[str, str]] = []
    mixed_rows: List[Dict[str, str]] = []

    for index, photo in enumerate(photos, start=1):
        if not isinstance(photo, list):
            continue
        source_asset_id = safe_get_list(photo, 0, "")
        media_block = safe_get_list(photo, 1, []) or []
        photo_url = safe_get_list(media_block, 0, "")
        width = safe_get_list(media_block, 1, "")
        height = safe_get_list(media_block, 2, "")
        capture_ms = safe_get_list(photo, 2, "")
        owner_key_list = safe_get_list(photo, 6, []) or []
        owner_key = safe_get_list(owner_key_list, 0, "")
        offset_ms = safe_get_list(photo, 4, "")
        uploaded_ms = safe_get_list(photo, 5, "")

        metadata_block = safe_get_list(media_block, 8, []) or []
        device_block = safe_get_list(metadata_block, 4, []) or []
        device_make = safe_get_list(device_block, 0, "")
        device_model = safe_get_list(device_block, 1, "")

        captured_at = to_iso_local_from_ms(capture_ms, offset_ms)
        capture_date = captured_at[:10] if captured_at else ""
        uploaded_at = to_iso_utc_from_ms(uploaded_ms)
        timezone_str = offset_to_timezone_string(offset_ms)

        manifest_rows.append(
            {
                "album_title": str(album_title or ""),
                "album_id": str(album_id or ""),
                "album_url": str(album_url or ""),
                "album_url_with_key": str(album_url_with_key or ""),
                "album_short_url": str(album_short_url or ""),
                "photo_index": str(index),
                "source_asset_id": str(source_asset_id or ""),
                "photo_url": str(photo_url or ""),
                "width": str(width or ""),
                "height": str(height or ""),
                "capture_ms": str(capture_ms or ""),
                "captured_at": str(captured_at or ""),
                "capture_date": str(capture_date or ""),
                "timezone_offset_minutes": str(int(offset_ms // 60000))
                if isinstance(offset_ms, (int, float))
                else "",
                "uploaded_ms": str(uploaded_ms or ""),
                "uploaded_at": str(uploaded_at or ""),
                "device_make": str(device_make or ""),
                "device_model": str(device_model or ""),
                "owner_key": str(owner_key or ""),
            }
        )

        mixed_rows.append(
            {
                "photo_url": str(photo_url or ""),
                "caption": "",
                "capture_date": str(capture_date or ""),
                "captured_at": str(captured_at or ""),
                "uploaded_at": str(uploaded_at or ""),
                "timezone": str(timezone_str or ""),
                "latitude": "",
                "longitude": "",
                "device_model": str(device_model or ""),
                "notes": "",
                "source_asset_id": str(source_asset_id or ""),
                "source_platform": "google_photos",
            }
        )

    return {
        "album_title": album_title or "",
        "album_id": album_id or "",
        "album_short_url": album_short_url or "",
        "album_url_with_key": album_url_with_key or "",
        "manifest_rows": manifest_rows,
        "mixed_rows": mixed_rows,
    }


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract metadata from a public Google Photos album URL."
    )
    parser.add_argument(
        "--album-url",
        default="",
        help="Public album URL (photos.app.goo.gl or photos.google.com/share...)",
    )
    parser.add_argument(
        "--html-input",
        type=Path,
        default=None,
        help="Use an already-downloaded album HTML file instead of fetching over network",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("data/intake/google_photos/album_manifest.csv"),
        help="Output CSV path for detailed album manifest",
    )
    parser.add_argument(
        "--mixed-output",
        type=Path,
        default=Path("data/intake/google_photos/manual_mixed_photos.csv"),
        help="Output CSV path for mixed photo intake prefill",
    )
    parser.add_argument(
        "--raw-html-output",
        type=Path,
        default=Path("data/intake/google_photos/raw_album_page.html"),
        help="Optional path to persist fetched album HTML",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.html_input is not None:
        html = args.html_input.read_text(encoding="utf-8")
    else:
        if not args.album_url:
            raise ValueError("--album-url is required unless --html-input is provided")
        html = fetch_html(args.album_url)
    payload = parse_ds1_payload(html)
    parsed = parse_album_rows(payload, args.album_url or "")

    if args.raw_html_output:
        args.raw_html_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_html_output.write_text(html, encoding="utf-8")

    write_csv(args.manifest_output, MANIFEST_FIELDS, parsed["manifest_rows"])
    write_csv(args.mixed_output, MIXED_FIELDS, parsed["mixed_rows"])

    print(f"album_title={parsed['album_title']}")
    print(f"album_id={parsed['album_id']}")
    print(f"album_short_url={parsed['album_short_url']}")
    print(f"album_url_with_key={parsed['album_url_with_key']}")
    print(f"photos_extracted={len(parsed['manifest_rows'])}")
    print(f"manifest_output={args.manifest_output}")
    print(f"mixed_output={args.mixed_output}")
    if args.raw_html_output:
        print(f"raw_html_output={args.raw_html_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
