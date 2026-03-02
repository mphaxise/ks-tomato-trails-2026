#!/usr/bin/env python3
"""Build deployable tracker version archive and copy release tracker snapshots.

Cloudflare Pages deploys the `tracker/` directory only. This script mirrors
`releases/<version>/tracker/*` into `tracker/releases/<version>/tracker/*` and
builds `tracker/version-archive.html` with links rooted at `./releases/...`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Sequence, Set

MANIFEST_PATH = Path("releases/manifest.json")
TRACKER_ROOT = Path("tracker")
RELEASES_ROOT = Path("releases")
DEPLOY_RELEASES_ROOT = TRACKER_ROOT / "releases"
ARCHIVE_HTML_PATH = TRACKER_ROOT / "version-archive.html"


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def load_manifest(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"versions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_versions(manifest: Dict[str, object]) -> List[Dict[str, object]]:
    versions = manifest.get("versions", [])
    if not isinstance(versions, list):
        return []
    valid = [item for item in versions if isinstance(item, dict)]
    valid.sort(key=lambda item: str(item.get("release_date", "")))
    return valid


def copied_files_set(version: Dict[str, object]) -> Set[str]:
    value = version.get("copied_files", [])
    if isinstance(value, list):
        return {str(entry) for entry in value}
    return set()


def build_links(copied: Set[str], base_url: str) -> List[str]:
    ordered = [
        ("tracker/index.html", "index"),
        ("tracker/experiment-trails-view.html", "mixed"),
        ("tracker/experiment-trails-label-editor.html", "editor"),
        ("tracker/tomato-trails-view.html", "tomato"),
        ("tracker/pot-intake-history.html", "pot history"),
        ("tracker/pot-run-comparison.html", "pot compare"),
        ("tracker/hard-row-reviewer.html", "hard-row reviewer"),
        ("tracker/non-tomato-snapshot.html", "non-tomato"),
        ("tracker/v1-4-cv-research.html", "v1.4 research"),
    ]
    links: List[str] = []
    for rel_path, label in ordered:
        if rel_path not in copied:
            continue
        leaf = rel_path.split("/", 1)[1]
        links.append(f'<a href="{base_url}/{leaf}">{label}</a>')
    return links


def sync_release_trackers(versions: Sequence[Dict[str, object]]) -> int:
    if DEPLOY_RELEASES_ROOT.exists():
        shutil.rmtree(DEPLOY_RELEASES_ROOT)
    DEPLOY_RELEASES_ROOT.mkdir(parents=True, exist_ok=True)

    copied_versions = 0
    for version in versions:
        version_id = str(version.get("version_id", "")).strip()
        if not version_id:
            continue
        source_tracker = RELEASES_ROOT / version_id / "tracker"
        target_tracker = DEPLOY_RELEASES_ROOT / version_id / "tracker"
        if not source_tracker.exists():
            continue
        target_tracker.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_tracker, target_tracker, dirs_exist_ok=True)
        copied_versions += 1
    return copied_versions


def build_html(versions: Sequence[Dict[str, object]]) -> str:
    rows: List[str] = []
    for version in versions:
        version_id = str(version.get("version_id", "")).strip()
        release_date = str(version.get("release_date", "")).strip()
        source_ref = str(version.get("source_ref", "")).strip()
        notes = str(version.get("notes", "")).strip()
        copied = copied_files_set(version)

        tracker_root = f"./releases/{html_escape(version_id)}/tracker"
        data_root = f"./releases/{html_escape(version_id)}/data"
        links = build_links(copied, tracker_root)
        links_html = " | ".join(links) if links else "n/a"

        rows.append(
            "<tr>"
            f"<td><strong>{html_escape(version_id)}</strong></td>"
            f"<td>{html_escape(release_date or 'n/a')}</td>"
            f"<td>{html_escape(source_ref or 'n/a')}</td>"
            f"<td>{html_escape(notes)}</td>"
            f"<td>{links_html}</td>"
            f"<td><code>{data_root}</code></td>"
            "</tr>"
        )

    body_rows = "\n".join(rows) if rows else "<tr><td colspan='6'>No versions yet.</td></tr>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Tomato Trails Version Archive</title>
  <style>
    body {{
      margin: 0;
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      background: #f3f0e3;
      color: #1f2b29;
    }}
    main {{
      max-width: 1180px;
      margin: 40px auto;
      padding: 0 16px;
    }}
    .card {{
      background: #fffdf7;
      border: 1px solid #d8d1c2;
      border-radius: 14px;
      padding: 20px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(1.3rem, 3vw, 2rem);
    }}
    p {{ margin: 0 0 14px; color: #4e5d58; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fffef9;
      border: 1px solid #d8d1c2;
    }}
    th, td {{
      border-bottom: 1px solid #ece5d4;
      text-align: left;
      padding: 8px 10px;
      vertical-align: top;
      font-size: 0.9rem;
    }}
    th {{
      background: #f5f0e4;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #5a6964;
    }}
    code {{
      background: #f3efe2;
      border-radius: 6px;
      padding: 2px 4px;
    }}
    a {{
      color: #2f6947;
      text-decoration: none;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main>
    <section class=\"card\">
      <h1>Tomato Trails Version Archive</h1>
      <p>Versioned snapshots of tracker HTML pages and source data files for each release cut.</p>
      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>Release Date</th>
            <th>Source Ref</th>
            <th>Notes</th>
            <th>Pages</th>
            <th>Data Folder</th>
          </tr>
        </thead>
        <tbody>
          {body_rows}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def main() -> int:
    manifest = load_manifest(MANIFEST_PATH)
    versions = normalize_versions(manifest)

    TRACKER_ROOT.mkdir(parents=True, exist_ok=True)
    copied_versions = sync_release_trackers(versions)

    html = build_html(versions)
    ARCHIVE_HTML_PATH.write_text(html, encoding="utf-8")

    print(f"manifest={MANIFEST_PATH}")
    print(f"versions={len(versions)}")
    print(f"copied_release_trackers={copied_versions}")
    print(f"deploy_release_root={DEPLOY_RELEASES_ROOT}")
    print(f"archive_html={ARCHIVE_HTML_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
