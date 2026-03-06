#!/usr/bin/env python3
"""Build a ground-truth audit from imported quick seed labels vs pipeline output."""

from __future__ import annotations

import argparse
import csv
import glob
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from v18_strategy_from_quick_seed import classify_description


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def parse_int(text: str) -> int:
    raw = (text or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def normalize_pot_id(text: str) -> str:
    raw = (text or "").strip().upper()
    if not raw:
        return ""
    if raw.endswith("T"):
        number = parse_int(raw[:-1])
        if number > 0:
            return f"{number}T"
    return ""


def load_imported_seed_rows(imported_seed_dir: Path) -> Dict[str, Dict[str, object]]:
    rows: Dict[str, Dict[str, object]] = {}
    for path in sorted(imported_seed_dir.glob("quick_seed_*.json")):
        payload = read_json(path)
        source_asset_id = str(payload.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue
        boxes = payload.get("boxes", [])
        if not isinstance(boxes, list):
            boxes = []

        pot_ids: set[str] = set()
        varietal_numbers: set[int] = set()
        other_descriptions: List[str] = []
        type_counts: Counter[str] = Counter()

        for box in boxes:
            if not isinstance(box, dict):
                continue
            desc = str(box.get("description", "") or "").strip()
            kind, value = classify_description(desc)
            type_counts[kind] += 1
            if kind == "pot_id" and value:
                pot_ids.add(value)
            elif kind == "varietal_number" and value:
                number = parse_int(value)
                if number > 0:
                    varietal_numbers.add(number)
            elif kind == "other" and desc:
                other_descriptions.append(desc)

        rows[source_asset_id] = {
            "seed_json_path": str(path),
            "capture_date": str(payload.get("capture_date", "") or "").strip(),
            "row_index": str(payload.get("row_index", "") or "").strip(),
            "source_asset_id": source_asset_id,
            "photo_url": str(payload.get("photo_url", "") or "").strip(),
            "boxes_total": len(boxes),
            "type_counts": dict(type_counts),
            "manual_pot_ids": sorted(
                pot_ids, key=lambda pot: int(pot[:-1]) if pot.endswith("T") else 9999
            ),
            "manual_varietal_numbers": sorted(varietal_numbers),
            "other_descriptions": other_descriptions,
        }
    return rows


def load_pipeline_rows(mapping_csv: Path) -> Dict[str, Dict[str, object]]:
    rows: Dict[str, Dict[str, object]] = {}
    with mapping_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_asset_id = str(row.get("source_asset_id", "") or "").strip()
            if not source_asset_id:
                continue
            rows[source_asset_id] = {
                "capture_date": str(row.get("capture_date", "") or "").strip(),
                "row_index": str(row.get("row_index", "") or "").strip(),
                "source_asset_id": source_asset_id,
                "pred_pot_id": normalize_pot_id(str(row.get("pot_id", "") or "")),
                "pred_series_number": parse_int(str(row.get("packet_number", "") or "")),
                "pred_variety_name": str(row.get("variety_name", "") or "").strip(),
                "resolution_source": str(row.get("resolution_source", "") or "").strip(),
                "mapping_note": str(row.get("mapping_note", "") or "").strip(),
            }
    return rows


def load_pair_rows(pair_resolution_glob: str) -> Dict[str, Dict[str, object]]:
    rows: Dict[str, Dict[str, object]] = {}
    for raw_path in sorted(glob.glob(pair_resolution_glob)):
        path = Path(raw_path)
        payload = read_json(path)
        source_asset_id = str(payload.get("source_asset_id", "") or "").strip()
        if not source_asset_id:
            continue
        pairs = payload.get("rows", [])
        if not isinstance(pairs, list):
            pairs = []
        rows[source_asset_id] = {
            "pair_json_path": str(path),
            "capture_date": str(payload.get("capture_date", "") or "").strip(),
            "row_index": str(payload.get("row_index", "") or "").strip(),
            "source_asset_id": source_asset_id,
            "total_rows": int(payload.get("total_rows", 0) or 0),
            "auto_resolved_count": int(payload.get("auto_resolved_count", 0) or 0),
            "needs_review_count": int(payload.get("needs_review_count", 0) or 0),
            "review_reason_counts": payload.get("review_reason_counts", {}),
            "rows": pairs,
        }
    return rows


def build_audit(
    imported_seed_dir: Path,
    mapping_csv: Path,
    pair_resolution_glob: str,
) -> Dict[str, object]:
    seed_rows = load_imported_seed_rows(imported_seed_dir)
    pipeline_rows = load_pipeline_rows(mapping_csv)
    pair_rows = load_pair_rows(pair_resolution_glob)

    parser_type_counts: Counter[str] = Counter()
    other_desc_counter: Counter[str] = Counter()
    for seed in seed_rows.values():
        for kind, count in (seed.get("type_counts", {}) or {}).items():
            parser_type_counts[str(kind)] += int(count)
        for desc in seed.get("other_descriptions", []):
            other_desc_counter[str(desc)] += 1

    joined_rows: List[Dict[str, object]] = []
    missing_pipeline_rows: List[str] = []

    strict_comparable = 0
    strict_match = 0
    pot_presence_match = 0
    series_presence_match = 0
    both_presence_match = 0
    pair_exact_match = 0

    pred_pot_not_found: Counter[str] = Counter()
    pred_series_not_found: Counter[str] = Counter()

    aggregated_pair_reason_counts: Counter[str] = Counter()
    conflict_patterns: Counter[str] = Counter()
    missing_var_for_pot: Counter[str] = Counter()
    orphan_varietals: Counter[str] = Counter()

    for source_asset_id, seed in sorted(seed_rows.items(), key=lambda kv: int((kv[1].get("row_index") or "0"))):
        pipeline = pipeline_rows.get(source_asset_id)
        if pipeline is None:
            missing_pipeline_rows.append(source_asset_id)
            continue

        manual_pots = set(seed.get("manual_pot_ids", []))
        manual_vars = set(int(v) for v in seed.get("manual_varietal_numbers", []))
        pred_pot = str(pipeline.get("pred_pot_id", "") or "")
        pred_series = int(pipeline.get("pred_series_number", 0) or 0)

        pot_present = bool(pred_pot and pred_pot in manual_pots)
        series_present = bool(pred_series > 0 and pred_series in manual_vars)
        both_present = pot_present and series_present

        if pot_present:
            pot_presence_match += 1
        else:
            if pred_pot:
                pred_pot_not_found[pred_pot] += 1

        if series_present:
            series_presence_match += 1
        else:
            if pred_series > 0:
                pred_series_not_found[str(pred_series)] += 1

        if both_present:
            both_presence_match += 1

        strict_row = len(manual_pots) == 1 and len(manual_vars) == 1
        strict_ok = False
        if strict_row and pred_pot and pred_series > 0:
            strict_comparable += 1
            strict_ok = (
                pred_pot == next(iter(manual_pots))
                and pred_series == next(iter(manual_vars))
            )
            if strict_ok:
                strict_match += 1

        pair_data = pair_rows.get(source_asset_id, {"rows": []})
        pair_list = pair_data.get("rows", [])
        if not isinstance(pair_list, list):
            pair_list = []

        pair_match = False
        for pair in pair_list:
            if not isinstance(pair, dict):
                continue
            reason = str(pair.get("review_reason", "") or "").strip()
            if reason:
                aggregated_pair_reason_counts[reason] += 1
            if reason == "pot_varietal_conflict":
                pot = str(pair.get("pot_id", "") or "").strip()
                exp = str(pair.get("expected_series_number", "") or "").strip()
                got = str(pair.get("varietal_number", "") or "").strip()
                pattern = f"conflict: pot {pot} expected {exp} labeled {got}"
                conflict_patterns[pattern] += 1
            elif reason == "missing_varietal_pair":
                pot = str(pair.get("pot_id", "") or "").strip()
                if pot:
                    missing_var_for_pot[f"missing_varietal_for_pot: {pot}"] += 1
            elif reason == "orphan_varietal_without_pot":
                var = str(pair.get("varietal_number", "") or "").strip()
                if var:
                    orphan_varietals[f"orphan_varietal: {var}"] += 1

            pair_pot = str(pair.get("pot_id", "") or "").strip()
            pair_var = parse_int(str(pair.get("varietal_number", "") or ""))
            if pred_pot and pred_series > 0 and pair_pot == pred_pot and pair_var == pred_series:
                pair_match = True

        if pair_match:
            pair_exact_match += 1

        joined_rows.append(
            {
                "capture_date": seed.get("capture_date", ""),
                "row_index": seed.get("row_index", ""),
                "source_asset_id": source_asset_id,
                "pred_pot_id": pred_pot,
                "pred_series_number": pred_series,
                "manual_pot_ids": sorted(manual_pots, key=lambda p: int(p[:-1]) if p.endswith("T") else 9999),
                "manual_varietal_numbers": sorted(manual_vars),
                "pot_presence_match": pot_present,
                "series_presence_match": series_present,
                "both_presence_match": both_present,
                "pair_exact_match": pair_match,
                "strict_comparable": strict_row,
                "strict_match": strict_ok,
            }
        )

    total_joined = len(joined_rows)
    top_patterns_counter = Counter()
    top_patterns_counter.update(conflict_patterns)
    top_patterns_counter.update(missing_var_for_pot)
    top_patterns_counter.update(orphan_varietals)
    for pot_id, count in pred_pot_not_found.items():
        top_patterns_counter[f"pipeline_pot_not_in_manual_set: {pot_id}"] += count
    for series, count in pred_series_not_found.items():
        top_patterns_counter[f"pipeline_series_not_in_manual_set: {series}"] += count

    top_patterns = [
        {"pattern": pattern, "count": count}
        for pattern, count in top_patterns_counter.most_common(10)
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_imported_seed_dir": str(imported_seed_dir),
        "input_mapping_csv": str(mapping_csv),
        "seed_rows_total": len(seed_rows),
        "pipeline_rows_total": len(pipeline_rows),
        "joined_rows_total": total_joined,
        "missing_pipeline_rows_count": len(missing_pipeline_rows),
        "missing_pipeline_rows": missing_pipeline_rows,
        "parser_type_counts": dict(parser_type_counts),
        "parser_other_top": [
            {"description": desc, "count": count}
            for desc, count in other_desc_counter.most_common(10)
        ],
        "metrics": {
            "pot_presence_match_rate": round((pot_presence_match / total_joined), 4) if total_joined else 0.0,
            "series_presence_match_rate": round((series_presence_match / total_joined), 4) if total_joined else 0.0,
            "both_presence_match_rate": round((both_presence_match / total_joined), 4) if total_joined else 0.0,
            "pair_exact_match_rate": round((pair_exact_match / total_joined), 4) if total_joined else 0.0,
            "strict_rows_comparable": strict_comparable,
            "strict_row_match_rate": round((strict_match / strict_comparable), 4) if strict_comparable else 0.0,
        },
        "pair_review_reason_counts": dict(aggregated_pair_reason_counts),
        "pipeline_not_found": {
            "pred_pot_not_in_manual_set": dict(pred_pot_not_found),
            "pred_series_not_in_manual_set": dict(pred_series_not_found),
        },
        "top_failure_patterns": top_patterns,
        "joined_rows": joined_rows,
    }


def build_markdown(audit: Dict[str, object], output_json: Path) -> str:
    metrics = audit.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    pair_reasons = audit.get("pair_review_reason_counts", {})
    if not isinstance(pair_reasons, dict):
        pair_reasons = {}
    top_patterns = audit.get("top_failure_patterns", [])
    if not isinstance(top_patterns, list):
        top_patterns = []
    parser_types = audit.get("parser_type_counts", {})
    if not isinstance(parser_types, dict):
        parser_types = {}

    lines = [
        "# V1.8 Ground Truth Accuracy Audit",
        "",
        f"Generated: `{audit.get('generated_at_utc', '')}`",
        f"Output JSON: `{output_json}`",
        "",
        "## Coverage",
        "",
        f"- seed rows total: `{audit.get('seed_rows_total', 0)}`",
        f"- pipeline rows total: `{audit.get('pipeline_rows_total', 0)}`",
        f"- joined rows total: `{audit.get('joined_rows_total', 0)}`",
        f"- missing pipeline rows: `{audit.get('missing_pipeline_rows_count', 0)}`",
        "",
        "## Parser Counts",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    for kind, count in sorted(parser_types.items()):
        lines.append(f"| `{kind}` | {count} |")

    lines.extend(
        [
            "",
            "## Accuracy Metrics",
            "",
            f"- pot presence match rate: `{metrics.get('pot_presence_match_rate', 0)}`",
            f"- series presence match rate: `{metrics.get('series_presence_match_rate', 0)}`",
            f"- both presence match rate: `{metrics.get('both_presence_match_rate', 0)}`",
            f"- pair exact match rate: `{metrics.get('pair_exact_match_rate', 0)}`",
            f"- strict comparable rows: `{metrics.get('strict_rows_comparable', 0)}`",
            f"- strict row match rate: `{metrics.get('strict_row_match_rate', 0)}`",
            "",
            "## Pair Review Reasons",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )
    if pair_reasons:
        for reason, count in sorted(pair_reasons.items()):
            lines.append(f"| `{reason}` | {count} |")
    else:
        lines.append("| _(none)_ | 0 |")

    lines.extend(["", "## Top 10 Failure Patterns", "", "| Pattern | Count |", "|---|---:|"])
    if top_patterns:
        for row in top_patterns:
            pattern = str(row.get("pattern", "") or "")
            count = int(row.get("count", 0) or 0)
            lines.append(f"| `{pattern}` | {count} |")
    else:
        lines.append("| _(none)_ | 0 |")

    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ground-truth accuracy audit from imported seed annotations."
    )
    parser.add_argument(
        "--imported-seed-dir",
        type=Path,
        default=Path("data/research/v1_8/imported_seeds"),
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=Path("data/intake/processed/tomato_pot_mapping_latest.csv"),
    )
    parser.add_argument(
        "--pair-resolution-glob",
        type=str,
        default="data/research/v1_8/quick_seed_pair_resolution_2026-03-01_*.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/v1_8/ground_truth_accuracy_audit.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.8-GROUND-TRUTH-ACCURACY-AUDIT.md"),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    audit = build_audit(
        imported_seed_dir=args.imported_seed_dir,
        mapping_csv=args.mapping_csv,
        pair_resolution_glob=args.pair_resolution_glob,
    )
    write_json(args.output_json, audit)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(audit, args.output_json), encoding="utf-8")

    print(f"seed_rows_total={audit['seed_rows_total']}")
    print(f"joined_rows_total={audit['joined_rows_total']}")
    print(f"pair_exact_match_rate={audit['metrics']['pair_exact_match_rate']}")
    print(f"strict_rows_comparable={audit['metrics']['strict_rows_comparable']}")
    print(f"strict_row_match_rate={audit['metrics']['strict_row_match_rate']}")
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
