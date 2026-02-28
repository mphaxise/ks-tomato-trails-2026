#!/usr/bin/env python3
"""Enforce release snapshot updates for merge candidates."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


SENSITIVE_PREFIXES = [
    "data/intake/google_photos/",
    "data/intake/processed/",
    "tracker/",
    "scripts/build_",
    "scripts/download_google_photos_images.py",
    "scripts/extract_google_photos_public_album.py",
    "scripts/label_non_tomato_from_images.py",
    "scripts/merge_label_overrides.py",
    "package.json",
]

REQUIRED_FILES = [
    "releases/manifest.json",
    "releases/RELEASE_NOTES.md",
]

METADATA_RE = re.compile(r"^releases/v[^/]+/metadata\.json$")
VERSION_ID_RE = re.compile(r"^v\d+\.\d+-\d{4}-\d{2}-\d{2}$")


def run_cmd(args: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def lines(output: str) -> List[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def changed_files(
    cwd: Path,
    base_ref: str,
    head_ref: str,
    include_working_tree: bool,
) -> List[str]:
    result = run_cmd(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        cwd,
    )
    if result.returncode != 0:
        alt = run_cmd(["git", "diff", "--name-only", base_ref, head_ref], cwd)
        if alt.returncode != 0:
            sys.stderr.write(result.stderr or alt.stderr)
            raise RuntimeError("Unable to compute changed files via git diff")
        ref_changed = lines(alt.stdout)
    else:
        ref_changed = lines(result.stdout)

    if not include_working_tree:
        return sorted(set(ref_changed))

    work_changed = lines(run_cmd(["git", "diff", "--name-only"], cwd).stdout)
    staged_changed = lines(run_cmd(["git", "diff", "--name-only", "--cached"], cwd).stdout)
    untracked = lines(
        run_cmd(["git", "ls-files", "--others", "--exclude-standard"], cwd).stdout
    )

    merged = set(ref_changed)
    merged.update(work_changed)
    merged.update(staged_changed)
    merged.update(untracked)
    return sorted(merged)


def is_sensitive(path: str) -> bool:
    for prefix in SENSITIVE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def load_latest_version_id(manifest_path: Path) -> str:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    versions = payload.get("versions")
    if not isinstance(versions, list) or not versions:
        raise ValueError("releases/manifest.json has no versions entries")
    latest = versions[-1]
    if not isinstance(latest, dict):
        raise ValueError("Latest manifest entry is not an object")
    version_id = str(latest.get("version_id", "")).strip()
    if not version_id:
        raise ValueError("Latest manifest entry is missing version_id")
    if not VERSION_ID_RE.match(version_id):
        raise ValueError(
            f"Latest version_id '{version_id}' does not match v<major>.<minor>-YYYY-MM-DD"
        )
    return version_id


def ensure_notes_reference_version(notes_path: Path, version_id: str) -> None:
    content = notes_path.read_text(encoding="utf-8")
    marker = f"## {version_id}"
    if marker not in content:
        raise ValueError(
            f"{notes_path.as_posix()} is missing section header '{marker}'"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that release snapshot artifacts are updated when "
            "release-sensitive files changed."
        )
    )
    parser.add_argument(
        "--base-ref",
        required=True,
        help="Base git ref (example: origin/master)",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref (default: HEAD)",
    )
    parser.add_argument(
        "--include-working-tree",
        action="store_true",
        help=(
            "Also include staged/unstaged/untracked local file changes "
            "(recommended for local pre-merge checks)."
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path.cwd()

    changed = changed_files(
        repo_root,
        args.base_ref,
        args.head_ref,
        args.include_working_tree,
    )
    sensitive_changed = sorted(path for path in changed if is_sensitive(path))

    print(f"base_ref={args.base_ref}")
    print(f"head_ref={args.head_ref}")
    print(f"changed_files={len(changed)}")
    print(f"sensitive_changed={len(sensitive_changed)}")

    if not sensitive_changed:
        print("guard_status=pass")
        print("reason=no release-sensitive files changed")
        return 0

    problems: List[str] = []

    for req in REQUIRED_FILES:
        if req not in changed:
            problems.append(f"Missing required changed file: {req}")

    metadata_changed = sorted(path for path in changed if METADATA_RE.match(path))
    if not metadata_changed:
        problems.append("Missing required changed file matching: releases/v*/metadata.json")

    manifest_path = repo_root / "releases" / "manifest.json"
    notes_path = repo_root / "releases" / "RELEASE_NOTES.md"

    if not manifest_path.exists():
        problems.append("Missing required file on disk: releases/manifest.json")
    if not notes_path.exists():
        problems.append("Missing required file on disk: releases/RELEASE_NOTES.md")

    latest_version_id = ""
    if manifest_path.exists():
        try:
            latest_version_id = load_latest_version_id(manifest_path)
            print(f"latest_version_id={latest_version_id}")
        except Exception as exc:  # noqa: BLE001
            problems.append(str(exc))

    if latest_version_id and notes_path.exists():
        try:
            ensure_notes_reference_version(notes_path, latest_version_id)
        except Exception as exc:  # noqa: BLE001
            problems.append(str(exc))

    if latest_version_id:
        latest_meta = repo_root / "releases" / latest_version_id / "metadata.json"
        if not latest_meta.exists():
            problems.append(
                f"Latest version metadata file missing on disk: {latest_meta.as_posix()}"
            )

    if problems:
        print("guard_status=fail")
        print("sensitive_paths:")
        for path in sensitive_changed:
            print(f"  - {path}")
        print("problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("guard_status=pass")
    print("sensitive_paths:")
    for path in sensitive_changed:
        print(f"  - {path}")
    print("metadata_changed:")
    for path in metadata_changed:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
