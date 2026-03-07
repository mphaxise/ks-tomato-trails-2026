#!/usr/bin/env python3
"""Extract photo metadata from a public Google Photos shared album page."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.parse
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

DEFAULT_RPC_QUERY = {
    "hl": "en-US",
    "soc-app": "116",
    "soc-platform": "1",
    "soc-device": "1",
    "rt": "c",
}


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


def extract_balanced_segment(
    text: str, start_idx: int, open_char: str, close_char: str
) -> str:
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != open_char:
        raise ValueError(f"Expected '{open_char}' at index {start_idx}")

    index = start_idx
    depth = 0
    in_string: str | None = None
    escape = False
    while index < len(text):
        ch = text[index]
        if in_string is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
        else:
            if ch in ('"', "'"):
                in_string = ch
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start_idx : index + 1]
        index += 1

    raise ValueError(f"Unterminated segment starting at {start_idx}")


def parse_ds1_payload(html: str) -> List[Any]:
    payload_raw = extract_json_array_after_data(html, "ds:1")
    payload = json.loads(payload_raw)
    if not isinstance(payload, list) or len(payload) < 4:
        raise ValueError("Unexpected ds:1 payload shape")
    return payload


def parse_wiz_global_data(html: str) -> Dict[str, Any]:
    marker = "window.WIZ_global_data = "
    marker_idx = html.find(marker)
    if marker_idx < 0:
        return {}
    object_start = html.find("{", marker_idx + len(marker))
    if object_start < 0:
        return {}
    object_raw = extract_balanced_segment(html, object_start, "{", "}")
    try:
        parsed = json.loads(object_raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_af_data_service_requests(html: str) -> Dict[str, Any]:
    marker = "var AF_dataServiceRequests = "
    marker_idx = html.find(marker)
    if marker_idx < 0:
        return {}
    object_start = html.find("{", marker_idx + len(marker))
    if object_start < 0:
        return {}

    object_raw = extract_balanced_segment(html, object_start, "{", "}")
    normalized = re.sub(
        r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:",
        r'\1"\2":',
        object_raw,
    )
    normalized = normalized.replace("'", '"')
    normalized = normalized.replace("undefined", "null")
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_continuation_context(
    html: str, ds1_payload: List[Any], album_url_input: str
) -> Dict[str, Any]:
    continuation_token = safe_get_list(ds1_payload, 2, "") or ""
    if not isinstance(continuation_token, str) or not continuation_token:
        return {}

    album_meta = safe_get_list(ds1_payload, 3, []) or []
    album_id = str(safe_get_list(album_meta, 0, "") or "")
    auth_key = str(safe_get_list(album_meta, 19, "") or "")
    if not album_id or not auth_key:
        return {}

    wiz_data = parse_wiz_global_data(html)
    f_sid = str(wiz_data.get("FdrFJe", "") or "")
    build_label = str(wiz_data.get("cfb2h", "") or "")
    at_token = str(wiz_data.get("SNlM0e", "") or "")

    data_requests = parse_af_data_service_requests(html)
    ds1_request = data_requests.get("ds:1", {}) if isinstance(data_requests, dict) else {}
    rpc_id = str(ds1_request.get("id", "") or "snAcKc")
    request_template = ds1_request.get("request", [])
    if not isinstance(request_template, list):
        request_template = []

    source_path = f"/share/{album_id}?key={auth_key}"
    if not source_path and album_url_input:
        parsed = urllib.parse.urlparse(album_url_input)
        if parsed.path:
            source_path = parsed.path
            if parsed.query:
                source_path = f"{source_path}?{parsed.query}"

    return {
        "album_id": album_id,
        "auth_key": auth_key,
        "continuation_token": continuation_token,
        "rpc_id": rpc_id,
        "request_template": request_template,
        "source_path": source_path,
        "f_sid": f_sid,
        "build_label": build_label,
        "at_token": at_token,
    }


def build_continuation_request_args(context: Dict[str, Any], continuation_token: str) -> List[Any]:
    request_args = list(context.get("request_template", []))
    while len(request_args) < 4:
        request_args.append(None)

    request_args[0] = request_args[0] or context.get("album_id", "")
    request_args[1] = continuation_token
    request_args[3] = request_args[3] or context.get("auth_key", "")
    return request_args


def parse_batchexecute_rpc_payload(
    response_text: str, rpc_id: str
) -> List[Any]:
    pattern = (
        r'\["wrb\.fr","'
        + re.escape(rpc_id)
        + r'","((?:\\.|[^"\\])*)",null,null,null,"generic"\]'
    )
    match = re.search(pattern, response_text)
    if match is None:
        raise ValueError(f"Could not find wrb.fr payload for rpc id {rpc_id}")

    escaped_inner = match.group(1)
    inner_json = json.loads('"' + escaped_inner + '"')
    payload = json.loads(inner_json)
    if not isinstance(payload, list):
        raise ValueError("Unexpected continuation payload type")
    return payload


def fetch_continuation_payload(
    context: Dict[str, Any], continuation_token: str, req_id: int
) -> List[Any]:
    rpc_id = str(context.get("rpc_id", "") or "snAcKc")
    request_args = build_continuation_request_args(context, continuation_token)
    request_json = json.dumps(request_args, separators=(",", ":"))
    f_req = json.dumps(
        [[[rpc_id, request_json, None, "generic"]]],
        separators=(",", ":"),
    )

    query = dict(DEFAULT_RPC_QUERY)
    query["rpcids"] = rpc_id
    query["_reqid"] = str(req_id)

    source_path = str(context.get("source_path", "") or "")
    if source_path:
        query["source-path"] = source_path
    f_sid = str(context.get("f_sid", "") or "")
    if f_sid:
        query["f.sid"] = f_sid
    build_label = str(context.get("build_label", "") or "")
    if build_label:
        query["bl"] = build_label

    url = "https://photos.google.com/_/PhotosUi/data/batchexecute?" + urllib.parse.urlencode(
        query
    )
    at_token = str(context.get("at_token", "") or "")

    curl_cmd = [
        "curl",
        "-sS",
        "-L",
        "-A",
        "Mozilla/5.0",
        url,
        "--data-urlencode",
        f"f.req={f_req}",
        "--data-urlencode",
        f"at={at_token}",
    ]
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise ValueError("curl is required for continuation fetches but is not installed") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise ValueError(f"Continuation fetch failed: {stderr or exc}") from exc

    return parse_batchexecute_rpc_payload(result.stdout, rpc_id)


def merge_photo_rows(initial_photos: List[Any], extra_photos: List[Any]) -> List[Any]:
    merged: List[Any] = []
    seen_asset_ids = set()

    for row in [*initial_photos, *extra_photos]:
        if not isinstance(row, list):
            continue
        asset_id = safe_get_list(row, 0, "")
        if isinstance(asset_id, str) and asset_id:
            if asset_id in seen_asset_ids:
                continue
            seen_asset_ids.add(asset_id)
        merged.append(row)

    return merged


def collect_continuation_photos(
    html: str, ds1_payload: List[Any], album_url_input: str
) -> Dict[str, Any]:
    context = build_continuation_context(html, ds1_payload, album_url_input)
    token = str(context.get("continuation_token", "") or "")
    if not token:
        return {"photos": [], "batches": 0}

    photos: List[Any] = []
    batches = 0
    req_id = 1000
    seen_tokens = set()

    while token and token not in seen_tokens:
        seen_tokens.add(token)
        continuation_payload = fetch_continuation_payload(context, token, req_id)
        req_id += 100000

        batch_photos = safe_get_list(continuation_payload, 1, []) or []
        if isinstance(batch_photos, list):
            photos.extend(batch_photos)
        batches += 1

        next_token = safe_get_list(continuation_payload, 2, "") or ""
        token = next_token if isinstance(next_token, str) else ""
        if not batch_photos and not token:
            break

    return {"photos": photos, "batches": batches}


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
    parser.add_argument(
        "--follow-continuation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fetch additional pages via Google Photos continuation RPC when a "
            "continuation token is present (default: true)."
        ),
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

    continuation_batches = 0
    continuation_rows = 0
    if args.follow_continuation:
        try:
            continuation = collect_continuation_photos(html, payload, args.album_url or "")
            extra_photos = continuation.get("photos", [])
            if isinstance(extra_photos, list) and extra_photos:
                initial_photos = safe_get_list(payload, 1, []) or []
                if isinstance(initial_photos, list):
                    merged_photos = merge_photo_rows(initial_photos, extra_photos)
                    payload = list(payload)
                    payload[1] = merged_photos
                    continuation_rows = max(0, len(merged_photos) - len(initial_photos))
            continuation_batches = int(continuation.get("batches", 0) or 0)
        except Exception as exc:  # pragma: no cover - network failure fallback
            print(f"continuation_warning={exc}", file=sys.stderr)

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
    print(f"continuation_batches={continuation_batches}")
    print(f"continuation_rows_added={continuation_rows}")
    print(f"manifest_output={args.manifest_output}")
    print(f"mixed_output={args.mixed_output}")
    if args.raw_html_output:
        print(f"raw_html_output={args.raw_html_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
