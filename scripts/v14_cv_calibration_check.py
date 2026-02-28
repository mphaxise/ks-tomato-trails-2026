#!/usr/bin/env python3
"""Evaluate v1.4 CV outputs against a manually reviewed calibration subset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def accuracy(match_count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return match_count / float(total)


def run_check(
    predicted_csv: Path,
    manual_csv: Path,
    json_out: Path,
    markdown_out: Path,
) -> Dict[str, object]:
    predicted = read_csv(predicted_csv)
    manual = read_csv(manual_csv)

    predicted_by_pot = {row.get("pot_id", "").strip(): row for row in predicted}
    total = 0
    survival_match = 0
    action_match = 0
    both_match = 0
    missing_predictions: List[str] = []
    mismatches: List[Dict[str, str]] = []

    for row in manual:
        pot_id = (row.get("pot_id", "") or "").strip()
        if not pot_id:
            continue
        total += 1
        predicted_row = predicted_by_pot.get(pot_id)
        if predicted_row is None:
            missing_predictions.append(pot_id)
            continue

        expected_survival = (row.get("expected_survival", "") or "").strip()
        expected_action = (row.get("expected_action", "") or "").strip()
        predicted_survival = (predicted_row.get("survival_hypothesis", "") or "").strip()
        predicted_action = (predicted_row.get("action_code", "") or "").strip()

        s_match = expected_survival == predicted_survival
        a_match = expected_action == predicted_action
        if s_match:
            survival_match += 1
        if a_match:
            action_match += 1
        if s_match and a_match:
            both_match += 1
        if not (s_match and a_match):
            mismatches.append(
                {
                    "pot_id": pot_id,
                    "expected_survival": expected_survival,
                    "predicted_survival": predicted_survival,
                    "expected_action": expected_action,
                    "predicted_action": predicted_action,
                    "review_note": (row.get("review_note", "") or "").strip(),
                }
            )

    survival_accuracy = accuracy(survival_match, total)
    action_accuracy = accuracy(action_match, total)
    joint_accuracy = accuracy(both_match, total)

    predicted_counter = Counter(
        (predicted_by_pot.get((row.get("pot_id", "") or "").strip(), {}) or {}).get(
            "survival_hypothesis", ""
        )
        for row in manual
        if (row.get("pot_id", "") or "").strip()
    )
    expected_counter = Counter(
        (row.get("expected_survival", "") or "").strip()
        for row in manual
        if (row.get("pot_id", "") or "").strip()
    )

    summary = {
        "manual_rows": total,
        "missing_predictions": missing_predictions,
        "survival_accuracy": round(survival_accuracy, 4),
        "action_accuracy": round(action_accuracy, 4),
        "joint_accuracy": round(joint_accuracy, 4),
        "expected_survival_counts": expected_counter,
        "predicted_survival_counts": predicted_counter,
        "mismatches": mismatches,
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# V1.4 Manual Calibration Check")
    lines.append("")
    lines.append(f"- Manual subset rows: `{total}`")
    lines.append(f"- Survival accuracy: `{survival_accuracy * 100:.1f}%`")
    lines.append(f"- Action accuracy: `{action_accuracy * 100:.1f}%`")
    lines.append(f"- Joint accuracy (survival+action): `{joint_accuracy * 100:.1f}%`")
    lines.append("")
    lines.append("## Survival Distribution")
    lines.append("")
    lines.append(
        "- Expected: "
        + ", ".join(f"{key}={value}" for key, value in expected_counter.items())
    )
    lines.append(
        "- Predicted: "
        + ", ".join(f"{key}={value}" for key, value in predicted_counter.items())
    )
    lines.append("")
    lines.append("## Mismatches")
    lines.append("")
    if not mismatches:
        lines.append("- None")
    else:
        lines.append("| Pot | Expected Survival | Predicted Survival | Expected Action | Predicted Action |")
        lines.append("|---|---|---|---|---|")
        for row in mismatches:
            lines.append(
                "| "
                f"{row['pot_id']} | "
                f"{row['expected_survival']} | "
                f"{row['predicted_survival']} | "
                f"{row['expected_action']} | "
                f"{row['predicted_action']} |"
            )

    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare v1.4 CV predictions with a manually reviewed calibration subset."
    )
    parser.add_argument(
        "--predicted-csv",
        type=Path,
        default=Path("data/research/v1_4/cv_experiment_results.csv"),
        help="Pipeline output CSV containing predictions.",
    )
    parser.add_argument(
        "--manual-csv",
        type=Path,
        default=Path("data/research/v1_4/manual_calibration_subset.csv"),
        help="Manual calibration subset CSV.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("data/research/v1_4/calibration_summary.json"),
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=Path("data/research/v1_4/calibration_report.md"),
        help="Output markdown report path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_check(
        predicted_csv=args.predicted_csv,
        manual_csv=args.manual_csv,
        json_out=args.json_out,
        markdown_out=args.markdown_out,
    )
    for key in ("manual_rows", "survival_accuracy", "action_accuracy", "joint_accuracy"):
        print(f"{key}={summary[key]}")
    print(f"json_out={args.json_out}")
    print(f"markdown_out={args.markdown_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
