#!/usr/bin/env python3
"""Generate pipeline strategy from quick single-photo seed JSON."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


VARIETAL_RE = re.compile(
    r"\bvariet(?:al)?\s*(?:no|number)?\s*([0-9]{1,3})\b", re.IGNORECASE
)
VARIETAL_TAG_RE = re.compile(r"\b([0-9]{1,3})\s*variet(?:al)?\s*tag\b", re.IGNORECASE)
VARIETAL_SIMPLE_RE = re.compile(r"\b([0-9]{1,3})\s*variet(?:al)?\b", re.IGNORECASE)
# Pot-ID parsing is strict: a valid pot tag must include an explicit T suffix.
POT_TAG_RE = re.compile(
    r"\b(?:tag\s*for\s*)?pot\s*([0-9]{1,3})\s*t\b", re.IGNORECASE
)
POT_ID_WITH_T_RE = re.compile(r"\b([0-9]{1,3})\s*t\b", re.IGNORECASE)

CONFIRMED_ANNOTATION_RULES = {
    "varietal_no_maps_to_series_number": True,
    "pot_id_requires_t_suffix": True,
}

IDENTITY_RESOLUTION_POLICY = {
    "primary_key": "pot_id",
    "secondary_key": "varietal_number",
    "conflict_action": "needs_review",
    "conflict_reason_code": "pot_varietal_conflict",
}


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def classify_description(desc: str) -> Tuple[str, str]:
    text = (desc or "").strip()
    if not text:
        return "unlabeled", ""

    m_var = VARIETAL_RE.search(text)
    if m_var:
        return "varietal_number", m_var.group(1)
    m_var_tag = VARIETAL_TAG_RE.search(text)
    if m_var_tag:
        return "varietal_number", m_var_tag.group(1)
    m_var_simple = VARIETAL_SIMPLE_RE.search(text)
    if m_var_simple:
        return "varietal_number", m_var_simple.group(1)

    m_pot = POT_TAG_RE.search(text)
    if m_pot:
        return "pot_id", f"{int(m_pot.group(1))}T"
    if "pot" in text.lower():
        m_pot_with_t = POT_ID_WITH_T_RE.search(text)
        if m_pot_with_t:
            return "pot_id", f"{int(m_pot_with_t.group(1))}T"

    return "other", ""


def summarize(seed: Dict[str, object]) -> Dict[str, object]:
    boxes = seed.get("boxes", [])
    if not isinstance(boxes, list):
        boxes = []

    typed_rows: List[Dict[str, object]] = []
    type_counts: Counter[str] = Counter()
    varietal_numbers: Counter[str] = Counter()
    pot_ids: Counter[str] = Counter()

    for box in boxes:
        if not isinstance(box, dict):
            continue
        box_id = box.get("id")
        desc = str(box.get("description", "") or "").strip()
        kind, value = classify_description(desc)
        type_counts[kind] += 1
        if kind == "varietal_number" and value:
            varietal_numbers[value] += 1
        if kind == "pot_id" and value:
            pot_ids[value] += 1

        typed_rows.append(
            {
                "id": box_id,
                "description": desc,
                "kind": kind,
                "value": value,
                "x_norm": box.get("x_norm"),
                "y_norm": box.get("y_norm"),
                "w_norm": box.get("w_norm"),
                "h_norm": box.get("h_norm"),
            }
        )

    total = len(typed_rows)
    typed = total - type_counts.get("unlabeled", 0)
    typed_ratio = float(typed) / float(total) if total else 0.0

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": seed.get("version", ""),
        "capture_date": seed.get("capture_date", ""),
        "row_index": seed.get("row_index", ""),
        "source_asset_id": seed.get("source_asset_id", ""),
        "photo_url": seed.get("photo_url", ""),
        "boxes_total": total,
        "typed_ratio": round(typed_ratio, 4),
        "type_counts": dict(type_counts),
        "varietal_number_counts": dict(varietal_numbers),
        "pot_id_counts": dict(pot_ids),
        "confirmed_annotation_rules": CONFIRMED_ANNOTATION_RULES,
        "identity_resolution_policy": IDENTITY_RESOLUTION_POLICY,
        "typed_rows": typed_rows,
    }


def strategy_markdown(summary: Dict[str, object], input_json: Path, output_json: Path) -> str:
    type_counts = summary.get("type_counts", {})
    if not isinstance(type_counts, dict):
        type_counts = {}
    varietal_counts = summary.get("varietal_number_counts", {})
    if not isinstance(varietal_counts, dict):
        varietal_counts = {}
    pot_counts = summary.get("pot_id_counts", {})
    if not isinstance(pot_counts, dict):
        pot_counts = {}
    annotation_rules = summary.get("confirmed_annotation_rules", {})
    if not isinstance(annotation_rules, dict):
        annotation_rules = {}
    resolution_policy = summary.get("identity_resolution_policy", {})
    if not isinstance(resolution_policy, dict):
        resolution_policy = {}

    lines = [
        "# V1.8 Strategy From Quick Seed",
        "",
        f"Generated: `{summary.get('generated_at_utc', '')}`",
        "",
        "## Inputs",
        "",
        f"- Seed JSON: `{input_json}`",
        f"- Parsed summary JSON: `{output_json}`",
        f"- capture_date: `{summary.get('capture_date', '')}`",
        f"- source_asset_id: `{summary.get('source_asset_id', '')}`",
        "",
        "## What This Seed Contains",
        "",
        f"- Total boxes: `{summary.get('boxes_total', 0)}`",
        f"- Typed ratio: `{summary.get('typed_ratio', 0)}`",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]

    for key, value in sorted(type_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Extracted Pot IDs", "", "| Pot ID | Count |", "|---|---:|"])
    for key, value in sorted(pot_counts.items(), key=lambda kv: int(kv[0].rstrip("T")) if str(kv[0]).endswith("T") else 9999):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Extracted Varietal Numbers", "", "| Varietal Number | Count |", "|---|---:|"])
    for key, value in sorted(varietal_counts.items(), key=lambda kv: int(kv[0])):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Confirmed Label Rules",
            "",
            f"- `varietal no X` means canonical series number: `{annotation_rules.get('varietal_no_maps_to_series_number', False)}`",
            f"- Pot tags must include `T` suffix: `{annotation_rules.get('pot_id_requires_t_suffix', False)}`",
        ]
    )

    lines.extend(
        [
            "",
            "## Pipeline Strategy (Derived From This Seed)",
            "",
            "1. **Stage A: Box Detection/Proposal**",
            "- Reuse this manual schema as the target output format: `{bbox, description}`.",
            "- Near-term: keep human-drawn boxes on a few more photos to build a small training/eval packet.",
            "",
            "2. **Stage B: Semantic Parsing Layer**",
            "- Parse descriptions into two canonical signals:",
            "  - `pot_id` (e.g., `21T`, `32T`)",
            "  - `varietal_number` (e.g., `7`, `10`, `11`)",
            "- Any unmatched text remains `other` for reviewer follow-up.",
            "",
            "3. **Stage C: Identity Resolution Layer**",
            "- Primary identity key: `pot_id` extracted from `pot` tags.",
            "- Secondary key: `varietal_number` mapped via canonical series map.",
            "- Conflict policy: if `pot_id` and `varietal_number` disagree, set `needs_review=true` and reason `pot_varietal_conflict`.",
            "",
            "4. **Stage D: Run-Level Mapping Output**",
            "- Emit row-level mapping with fields:",
            "  - `source_asset_id`, `pot_id`, `varietal_number`, `evidence_type`, `confidence`, `needs_review`.",
            "",
            "5. **Stage E: Human-in-the-loop Rules**",
            "- Only review rows where:",
            "  - no `pot_id` extracted, or",
            "  - multiple conflicting `pot_id` values in one image, or",
            "  - `varietal_number` is missing/unknown, or",
            "  - `pot_varietal_conflict` was detected.",
            "",
            "## Next Step",
            "",
            "1. Annotate 3-5 additional photos with this same style (`varietal no X`, `pot NN T`).",
            "2. Run this strategy extractor on each seed JSON to track parser coverage and conflicts.",
            "3. Start a tiny resolver prototype that pairs nearby `pot_id` and `varietal_number` boxes per image.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate strategy docs from quick single-photo seed JSON."
    )
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_8/quick_seed_strategy_summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.8-STRATEGY-FROM-QUICK-SEED.md"),
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
        strategy_markdown(summary, args.input_json, args.output_json),
        encoding="utf-8",
    )

    print(f"input_json={args.input_json}")
    print(f"boxes_total={summary['boxes_total']}")
    print(f"type_counts={summary['type_counts']}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
