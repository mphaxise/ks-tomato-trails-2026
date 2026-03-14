#!/usr/bin/env python3
"""Helpers for stable generated artifacts during repeated rebuilds."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text_optional(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _repo_root_for(path: Path) -> Optional[Path]:
    resolved_parent = path.resolve().parent
    for candidate in (resolved_parent, *resolved_parent.parents):
        if (candidate / ".git").exists():
            return candidate
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(resolved_parent),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    root = Path(result.stdout.strip())
    return root if root.exists() else None


def _read_head_text(path: Path) -> Optional[str]:
    repo_root = _repo_root_for(path)
    if repo_root is None:
        return None
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout


def _read_json_optional(path: Path) -> Optional[Dict[str, Any]]:
    text = _read_text_optional(path)
    if text is None:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _read_head_json(path: Path) -> Optional[Dict[str, Any]]:
    text = _read_head_text(path)
    if text is None:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_placeholder_value(
    rendered_text: str,
    template: str,
    placeholder: str,
) -> Optional[str]:
    if template.count(placeholder) != 1:
        raise ValueError(f"expected exactly one {placeholder!r} marker in template")
    before, _, after = template.partition(placeholder)
    start = rendered_text.find(before)
    if start == -1:
        return None
    value_start = start + len(before)
    value_end = rendered_text.find(after, value_start)
    if value_end == -1:
        return None
    normalized = rendered_text[:value_start] + placeholder + rendered_text[value_end:]
    if normalized != template:
        return None
    return rendered_text[value_start:value_end]


def stabilize_rendered_text(
    output_path: Path,
    template: str,
    *,
    placeholder: str = "__GENERATED_AT__",
    fallback_value: Optional[str] = None,
) -> str:
    existing_text = _read_text_optional(output_path)
    head_text = _read_head_text(output_path)

    existing_value = (
        _extract_placeholder_value(existing_text, template, placeholder)
        if existing_text is not None
        else None
    )
    head_value = (
        _extract_placeholder_value(head_text, template, placeholder)
        if head_text is not None
        else None
    )

    if existing_value is not None and head_value is not None:
        stable_value = head_value
    elif existing_value is not None:
        stable_value = existing_value
    elif head_value is not None:
        stable_value = head_value
    else:
        stable_value = fallback_value or iso_now()

    return template.replace(placeholder, stable_value, 1)


def stabilize_json_timestamp(
    output_path: Path,
    payload: Mapping[str, Any],
    *,
    timestamp_key: str = "generated_at_utc",
    fallback_value: Optional[str] = None,
) -> Dict[str, Any]:
    stable_payload = dict(payload)
    new_core = dict(stable_payload)
    new_core.pop(timestamp_key, None)

    existing_payload = _read_json_optional(output_path)
    head_payload = _read_head_json(output_path)

    existing_core = dict(existing_payload) if existing_payload is not None else None
    if existing_core is not None:
        existing_core.pop(timestamp_key, None)

    head_core = dict(head_payload) if head_payload is not None else None
    if head_core is not None:
        head_core.pop(timestamp_key, None)

    existing_value = (
        str(existing_payload.get(timestamp_key, "") or "").strip()
        if existing_payload is not None
        else ""
    )
    head_value = (
        str(head_payload.get(timestamp_key, "") or "").strip()
        if head_payload is not None
        else ""
    )

    if existing_core == new_core and head_core == new_core and head_value:
        stable_payload[timestamp_key] = head_value
        return stable_payload
    if existing_core == new_core and existing_value:
        stable_payload[timestamp_key] = existing_value
        return stable_payload
    if head_core == new_core and head_value:
        stable_payload[timestamp_key] = head_value
        return stable_payload

    stable_payload[timestamp_key] = fallback_value or iso_now()
    return stable_payload


def write_text_if_changed(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = _read_text_optional(path)
    if existing_text == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True, indent=2)
    return write_text_if_changed(path, text)
