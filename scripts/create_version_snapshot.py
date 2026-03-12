#!/usr/bin/env python3
"""Create versioned release snapshots of data and tracker HTML artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DEFAULT_FILES = [
    "data/intake/google_photos/manual_mixed_photos.csv",
    "data/intake/google_photos/manual_mixed_photos_labeled_v3.csv",
    "data/intake/google_photos/manual_non_tomato_labeled_v3.csv",
    "data/intake/google_photos/manual_label_overrides_v1.csv",
    "data/intake/google_photos/manual_tomato_series_map.csv",
    "data/intake/google_photos/manual_tomato_pot_series_overrides.csv",
    "data/intake/processed/tomato_pot_mapping_latest.csv",
    "data/intake/processed/tomato_pot_mapping_report_latest.json",
    "data/research/v1_4/cv_experiment_results.csv",
    "data/research/v1_4/pot_recommendations.csv",
    "data/research/v1_4/algorithm_assessment.csv",
    "data/research/v1_4/research_summary.json",
    "data/research/v1_6/batch_drift_summary.csv",
    "data/research/v1_6/intake_pipeline_plan.json",
    "docs/V1.6-RANDOM-INTAKE-PIPELINE.md",
    "data/research/v1_10/algorithm_assessment.csv",
    "data/research/v1_10/pot_cv_metrics.csv",
    "data/research/v1_10/pot_cv_recommendations.csv",
    "data/research/v1_10/pot_cv_summary.json",
    "data/research/v1_10/mask_label_queue.csv",
    "data/research/v1_10/mask_label_seed_set.csv",
    "data/research/v1_10/neighbor_disambiguation_queue.csv",
    "data/research/v1_10/seed_label_annotation_manifest.csv",
    "data/research/v1_10/seed_label_annotation_summary.json",
    "data/research/v1_11/seed_annotation_ingest_manifest.csv",
    "data/research/v1_11/seed_annotation_box_rows.csv",
    "data/research/v1_11/seed_annotation_ingest_summary.json",
    "docs/V1.10-POT-CV-EXPERIMENT.md",
    "docs/V1.10-SEED-LABEL-ANNOTATION-STATUS.md",
    "docs/V1.11-SEED-ANNOTATION-INGEST.md",
    "tracker/index.html",
    "tracker/experiment-trails-view.html",
    "tracker/experiment-trails-label-editor.html",
    "tracker/tomato-trails-view.html",
    "tracker/pot-intake-history.html",
    "tracker/pot-run-comparison.html",
    "tracker/tomato-signal-observatory.html",
    "tracker/hard-row-reviewer.html",
    "tracker/non-tomato-snapshot.html",
    "tracker/v1-4-cv-research.html",
    "tracker/v1-10-pot-cv-research.html",
    "tracker/v1-10-mask-label-seed.html",
    "tracker/v1-10-neighbor-disambiguation.html",
    "tracker/single-photo-seed-labeler.html",
    "tracker/v1-10-seed-annotation-status.html",
    "tracker/v1-11-seed-annotation-ingest.html",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(args: List[str], cwd: Path) -> Tuple[int, str]:
    result = subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def git_ref_commit(workdir: Path, source_ref: str) -> str:
    if source_ref == "WORKTREE":
        code, output = run_cmd(["git", "rev-parse", "HEAD"], workdir)
    else:
        code, output = run_cmd(["git", "rev-parse", source_ref], workdir)
    if code != 0:
        return ""
    return output.strip()


def load_from_ref(workdir: Path, source_ref: str, rel_path: str) -> str:
    if source_ref == "WORKTREE":
        target = workdir / rel_path
        if not target.exists():
            raise FileNotFoundError(rel_path)
        return target.read_text(encoding="utf-8")

    code, output = run_cmd(["git", "show", f"{source_ref}:{rel_path}"], workdir)
    if code != 0:
        raise FileNotFoundError(rel_path)
    return output


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_manifest(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"versions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, payload: Dict[str, object]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def normalize_version_id(raw: str) -> str:
    value = raw.strip().lower()
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_", "."})
    if not cleaned:
        raise ValueError("Version id is empty after normalization")
    return cleaned


def build_version_page_html(manifest: Dict[str, object]) -> str:
    versions = manifest.get("versions", [])
    rows = []
    for item in versions:
        if not isinstance(item, dict):
            continue
        version_id = str(item.get("version_id", "")).strip()
        release_date = str(item.get("release_date", "")).strip()
        source_ref = str(item.get("source_ref", "")).strip()
        notes = str(item.get("notes", "")).strip()
        copied = set(item.get("copied_files", [])) if isinstance(item.get("copied_files"), list) else set()
        tracker_root = f"./releases/{version_id}/tracker"
        data_root = f"./releases/{version_id}/data"
        links = []
        if "tracker/index.html" in copied:
            links.append(f"<a href=\"{tracker_root}/index.html\">index</a>")
        if "tracker/experiment-trails-view.html" in copied:
            links.append(f"<a href=\"{tracker_root}/experiment-trails-view.html\">mixed</a>")
        if "tracker/experiment-trails-label-editor.html" in copied:
            links.append(f"<a href=\"{tracker_root}/experiment-trails-label-editor.html\">editor</a>")
        if "tracker/tomato-trails-view.html" in copied:
            links.append(f"<a href=\"{tracker_root}/tomato-trails-view.html\">tomato</a>")
        if "tracker/pot-intake-history.html" in copied:
            links.append(f"<a href=\"{tracker_root}/pot-intake-history.html\">pot history</a>")
        if "tracker/pot-run-comparison.html" in copied:
            links.append(f"<a href=\"{tracker_root}/pot-run-comparison.html\">pot compare</a>")
        if "tracker/tomato-signal-observatory.html" in copied:
            links.append(
                f"<a href=\"{tracker_root}/tomato-signal-observatory.html\">observatory</a>"
            )
        if "tracker/hard-row-reviewer.html" in copied:
            links.append(f"<a href=\"{tracker_root}/hard-row-reviewer.html\">hard-row reviewer</a>")
        if "tracker/non-tomato-snapshot.html" in copied:
            links.append(f"<a href=\"{tracker_root}/non-tomato-snapshot.html\">non-tomato</a>")
        if "tracker/v1-4-cv-research.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-4-cv-research.html\">v1.4 research</a>")
        if "tracker/v1-10-pot-cv-research.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-10-pot-cv-research.html\">v1.10 CV</a>")
        if "tracker/v1-10-mask-label-seed.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-10-mask-label-seed.html\">v1.10 seed pack</a>")
        if "tracker/v1-10-neighbor-disambiguation.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-10-neighbor-disambiguation.html\">v1.10 neighbor queue</a>")
        if "tracker/single-photo-seed-labeler.html" in copied:
            links.append(f"<a href=\"{tracker_root}/single-photo-seed-labeler.html\">seed labeler</a>")
        if "tracker/v1-10-seed-annotation-status.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-10-seed-annotation-status.html\">annotation status</a>")
        if "tracker/v1-11-seed-annotation-ingest.html" in copied:
            links.append(f"<a href=\"{tracker_root}/v1-11-seed-annotation-ingest.html\">v1.11 ingest</a>")
        links_html = " | ".join(links) if links else "n/a"
        rows.append(
            "<tr>"
            f"<td><strong>{version_id}</strong></td>"
            f"<td>{release_date or 'n/a'}</td>"
            f"<td>{source_ref or 'n/a'}</td>"
            f"<td>{notes or ''}</td>"
            f"<td>{links_html}</td>"
            f"<td><code>{data_root}</code></td>"
            "</tr>"
        )

    body_rows = "\n".join(rows) if rows else "<tr><td colspan='6'>No versions yet.</td></tr>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
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
    <section class="card">
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


def create_snapshot(
    workdir: Path,
    version_id: str,
    source_ref: str,
    release_date: str,
    notes: str,
    files: List[str],
) -> Dict[str, object]:
    archive_root = workdir / "releases"
    version_root = archive_root / version_id
    copied: List[str] = []
    missing: List[str] = []

    for rel_path in files:
        try:
            content = load_from_ref(workdir, source_ref, rel_path)
        except FileNotFoundError:
            missing.append(rel_path)
            continue
        target = version_root / rel_path
        ensure_parent(target)
        target.write_text(content, encoding="utf-8")
        copied.append(rel_path)

    metadata = {
        "version_id": version_id,
        "release_date": release_date,
        "source_ref": source_ref,
        "source_commit": git_ref_commit(workdir, source_ref),
        "created_at_utc": iso_now(),
        "notes": notes,
        "copied_files": copied,
        "missing_files": missing,
    }
    metadata_path = version_root / "metadata.json"
    ensure_parent(metadata_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
    return metadata


def upsert_manifest(manifest: Dict[str, object], metadata: Dict[str, object]) -> Dict[str, object]:
    versions = manifest.get("versions")
    if not isinstance(versions, list):
        versions = []

    version_id = str(metadata.get("version_id", ""))
    kept = [
        item
        for item in versions
        if not (isinstance(item, dict) and str(item.get("version_id", "")) == version_id)
    ]
    kept.append(metadata)
    kept.sort(key=lambda item: str(item.get("release_date", "")))
    return {"versions": kept}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create release snapshot under releases/<version_id>/."
    )
    parser.add_argument(
        "--version-id",
        required=True,
        help="Version identifier (for example: v1.2-2026-02-28)",
    )
    parser.add_argument(
        "--source-ref",
        default="WORKTREE",
        help="Git ref to snapshot from (default: WORKTREE).",
    )
    parser.add_argument(
        "--release-date",
        required=True,
        help="Release date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Short notes for the version manifest.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        help="Optional explicit file include (can repeat).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workdir = Path.cwd()

    version_id = normalize_version_id(args.version_id)
    files = args.include if args.include else DEFAULT_FILES

    metadata = create_snapshot(
        workdir,
        version_id,
        args.source_ref,
        args.release_date.strip(),
        args.notes.strip(),
        files,
    )

    manifest_path = workdir / "releases" / "manifest.json"
    manifest = load_manifest(manifest_path)
    manifest = upsert_manifest(manifest, metadata)
    write_manifest(manifest_path, manifest)

    tracker_archive_page = workdir / "tracker" / "version-archive.html"
    archive_builder = workdir / "scripts" / "build_version_archive_page.py"
    if archive_builder.exists():
        subprocess.run(
            ["python3", str(archive_builder)],
            cwd=str(workdir),
            check=False,
        )
    else:
        tracker_archive_page.write_text(
            build_version_page_html(manifest), encoding="utf-8"
        )

    print(f"version_id={version_id}")
    print(f"source_ref={args.source_ref}")
    print(f"release_date={args.release_date.strip()}")
    print(f"copied_files={len(metadata['copied_files'])}")
    print(f"missing_files={len(metadata['missing_files'])}")
    print(f"snapshot_root=releases/{version_id}")
    print(f"manifest_path={manifest_path}")
    print(f"tracker_archive_page={tracker_archive_page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
