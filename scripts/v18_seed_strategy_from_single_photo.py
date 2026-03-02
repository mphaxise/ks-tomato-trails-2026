#!/usr/bin/env python3
"""Build a first-pass pipeline strategy from single-photo seed annotations."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def infer_level_priority(level_key: str, level_desc: str) -> str:
    text = f"{level_key} {level_desc}".lower()
    if "label" in text or "number" in text or "stake" in text:
        return "identity_signal"
    if "plant" in text or "leaf" in text or "fruit" in text:
        return "growth_signal"
    if "background" in text:
        return "noise_signal"
    return "review_signal"


def infer_stage_hint(level_key: str, level_desc: str) -> str:
    text = f"{level_key} {level_desc}".lower()
    if "label" in text or "number" in text or "stake" in text:
        return "Run OCR + numeric matching first; use as pot-ID evidence."
    if "plant" in text or "leaf" in text or "fruit" in text:
        return "Use embedding/segmentation features for growth and re-ID support."
    if "background" in text:
        return "Treat as distractor; down-weight in OCR crops."
    return "Route to reviewer until enough examples exist for automation."


def summarize(seed: Dict[str, object]) -> Dict[str, object]:
    levels_raw = seed.get("levels", [])
    boxes_raw = seed.get("boxes", [])
    if not isinstance(levels_raw, list):
        levels_raw = []
    if not isinstance(boxes_raw, list):
        boxes_raw = []

    levels: List[Tuple[str, str]] = []
    for item in levels_raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        desc = str(item.get("description", "")).strip()
        if not key:
            continue
        levels.append((key, desc))

    box_count_by_level: Counter[str] = Counter()
    box_count_by_label: Counter[str] = Counter()
    label_by_level: Dict[str, Counter[str]] = defaultdict(Counter)

    for item in boxes_raw:
        if not isinstance(item, dict):
            continue
        level_key = str(item.get("level_key", "")).strip()
        label = str(item.get("label", "")).strip() or "unknown"
        if level_key:
            box_count_by_level[level_key] += 1
            label_by_level[level_key][label] += 1
        box_count_by_label[label] += 1

    level_rows = []
    for key, desc in levels:
        level_rows.append(
            {
                "level_key": key,
                "description": desc,
                "priority_class": infer_level_priority(key, desc),
                "stage_hint": infer_stage_hint(key, desc),
                "box_count": box_count_by_level.get(key, 0),
                "top_labels": dict(label_by_level.get(key, Counter()).most_common(5)),
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "image_src": str(seed.get("image_src", "")),
        "reviewer": str(seed.get("reviewer", "")),
        "global_description": str(seed.get("global_description", "")),
        "levels_count": len(level_rows),
        "boxes_count": len([b for b in boxes_raw if isinstance(b, dict)]),
        "level_rows": level_rows,
        "box_count_by_label": dict(box_count_by_label),
    }


def render_markdown(summary: Dict[str, object], input_json: Path, output_json: Path) -> str:
    levels = summary.get("level_rows", [])
    if not isinstance(levels, list):
        levels = []
    label_counts = summary.get("box_count_by_label", {})
    if not isinstance(label_counts, dict):
        label_counts = {}

    lines = [
        "# V1.8 Seed Pipeline Strategy (Single Photo)",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        "",
        "## Inputs",
        "",
        f"- Seed annotation JSON: `{input_json}`",
        f"- Parsed summary JSON: `{output_json}`",
        f"- Image: `{summary.get('image_src', '')}`",
        f"- Reviewer: `{summary.get('reviewer', '')}`",
        "",
        "## Snapshot",
        "",
        f"- Levels defined: `{summary.get('levels_count', 0)}`",
        f"- Boxes annotated: `{summary.get('boxes_count', 0)}`",
        "",
        "## Label Distribution",
        "",
        "| Label | Count |",
        "|---|---:|",
    ]
    for label, count in sorted(label_counts.items()):
        lines.append(f"| `{label}` | {count} |")

    lines.extend(
        [
            "",
            "## Level-to-Stage Mapping",
            "",
            "| Level | Description | Priority Class | Boxes | Stage Hint |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in levels:
        lines.append(
            "| `{level_key}` | {description} | `{priority_class}` | {box_count} | {stage_hint} |".format(
                level_key=row.get("level_key", ""),
                description=row.get("description", "") or "-",
                priority_class=row.get("priority_class", ""),
                box_count=row.get("box_count", 0),
                stage_hint=row.get("stage_hint", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "1. Add 3-5 more annotated photos using the same level schema.",
            "2. Keep level keys stable (`L1`, `L2`, ...) so we can train per-level routing logic.",
            "3. Use level classes to split pipeline stages: identity OCR, growth embeddings, and distractor filtering.",
            "4. Re-run this strategy script after each new batch to update stage priorities.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a pipeline strategy draft from one seed annotation JSON."
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        required=True,
        help="Exported JSON from tracker/single-photo-seed-labeler.html",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_8/seed_strategy_summary.json"),
        help="Output summary JSON path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.8-SEED-PIPELINE-STRATEGY.md"),
        help="Output markdown strategy path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    seed = read_json(args.input_json)
    summary = summarize(seed)
    write_json(args.output_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_markdown(summary, args.input_json, args.output_json), encoding="utf-8"
    )

    print(f"input_json={args.input_json}")
    print(f"levels_count={summary['levels_count']}")
    print(f"boxes_count={summary['boxes_count']}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
