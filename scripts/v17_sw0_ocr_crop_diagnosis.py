#!/usr/bin/env python3
"""Sprint 0: OCR crop-targeting diagnosis packet for hard queue rows."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a CSV header")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def parse_pot_number(pot_id: str) -> int:
    matched = re.fullmatch(r"([0-9]{1,3})T", (pot_id or "").strip())
    if not matched:
        return 0
    return int(matched.group(1))


def parse_numbers(raw: str) -> List[int]:
    numbers: List[int] = []
    seen = set()
    for token in re.findall(r"\b([0-9]{1,3})\b", raw or ""):
        value = int(token)
        if value <= 0 or value > 99 or value in seen:
            continue
        seen.add(value)
        numbers.append(value)
    return numbers


def row_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        (row.get("run_date", "") or "").strip(),
        (row.get("row_index", "") or "").strip(),
        (row.get("source_asset_id", "") or "").strip(),
    )


def choose_sample_rows(rows: List[Dict[str, str]], sample_size: int) -> List[Dict[str, str]]:
    if sample_size <= 0:
        return []

    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        run_date = (row.get("run_date", "") or "").strip()
        grouped[run_date].append(row)

    for run_date in grouped:
        grouped[run_date].sort(
            key=lambda row: parse_int((row.get("row_index", "") or "").strip(), default=0)
        )

    run_dates = sorted(grouped.keys())
    picked: List[Dict[str, str]] = []
    cursor = {run_date: 0 for run_date in run_dates}

    while len(picked) < sample_size:
        progressed = False
        for run_date in run_dates:
            rows_for_run = grouped[run_date]
            idx = cursor[run_date]
            if idx >= len(rows_for_run):
                continue
            picked.append(rows_for_run[idx])
            cursor[run_date] = idx + 1
            progressed = True
            if len(picked) >= sample_size:
                break
        if not progressed:
            break

    return picked


def classify_proxy_root_cause(
    *,
    expected_pot_number: int,
    label_numbers: Sequence[int],
    non_label_numbers: Sequence[int],
    label_match_any: bool,
    non_label_match_any: bool,
) -> Tuple[str, str]:
    if non_label_match_any and not label_match_any:
        return (
            "crop_targeting_likely_wrong",
            "Non-label variants matched while label variants did not",
        )

    if not label_numbers and non_label_numbers:
        return (
            "crop_targeting_likely_wrong",
            "Only non-label variants found numeric tokens",
        )

    if label_match_any:
        return (
            "label_signal_present",
            "Label-region variant contains matched numeric signal",
        )

    union_numbers = set(label_numbers) | set(non_label_numbers)
    if expected_pot_number > 0 and expected_pot_number in union_numbers:
        return (
            "pot_number_seen_but_not_matched",
            "Expected pot number appears in OCR tokens but no variant matched",
        )

    if union_numbers:
        return (
            "ambient_numbers_no_pot_signal",
            "OCR saw digits but none support expected pot identity",
        )

    return (
        "no_numeric_signal_any_variant",
        "No numeric OCR tokens were detected in tested variants",
    )


def build_diagnosis_rows(
    sampled_rows: List[Dict[str, str]],
    ocr_details: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for row in sampled_rows:
        key = row_key(row)
        details = ocr_details.get(key, [])
        expected_pot_id = (row.get("pot_id", "") or "").strip()
        expected_pot_number = parse_pot_number(expected_pot_id)

        label_numbers = set()
        non_label_numbers = set()
        label_match_any = False
        non_label_match_any = False
        label_variants_with_digits = 0
        non_label_variants_with_digits = 0

        for detail in details:
            variant = (detail.get("variant", "") or "").strip()
            numbers = parse_numbers((detail.get("numbers_detected", "") or "").strip())
            has_match = parse_int((detail.get("match", "") or "0").strip(), default=0) > 0
            is_label_variant = variant.startswith("label_")

            if numbers:
                if is_label_variant:
                    label_variants_with_digits += 1
                else:
                    non_label_variants_with_digits += 1

            if is_label_variant:
                label_numbers.update(numbers)
                label_match_any = label_match_any or has_match
            else:
                non_label_numbers.update(numbers)
                non_label_match_any = non_label_match_any or has_match

        root_class, root_reason = classify_proxy_root_cause(
            expected_pot_number=expected_pot_number,
            label_numbers=sorted(label_numbers),
            non_label_numbers=sorted(non_label_numbers),
            label_match_any=label_match_any,
            non_label_match_any=non_label_match_any,
        )

        label_crop_path = (row.get("label_crop_path", "") or "").strip()
        center_crop_path = (row.get("center_crop_path", "") or "").strip()
        full_crop_path = (row.get("full_crop_path", "") or "").strip()

        output.append(
            {
                "run_date": (row.get("run_date", "") or "").strip(),
                "row_index": (row.get("row_index", "") or "").strip(),
                "source_asset_id": (row.get("source_asset_id", "") or "").strip(),
                "pot_id": expected_pot_id,
                "pot_number": expected_pot_number,
                "matched_variant_count": parse_int((row.get("matched_variant_count", "") or "0").strip(), default=0),
                "ensemble_numbers_detected": (row.get("ensemble_numbers_detected", "") or "").strip(),
                "label_numbers_detected": ",".join(str(v) for v in sorted(label_numbers)),
                "non_label_numbers_detected": ",".join(str(v) for v in sorted(non_label_numbers)),
                "label_match_any": int(label_match_any),
                "non_label_match_any": int(non_label_match_any),
                "label_variants_with_digits": label_variants_with_digits,
                "non_label_variants_with_digits": non_label_variants_with_digits,
                "proxy_root_cause_class": root_class,
                "proxy_root_cause_reason": root_reason,
                "label_crop_path": label_crop_path,
                "center_crop_path": center_crop_path,
                "full_crop_path": full_crop_path,
                "photo_url": (row.get("photo_url", "") or "").strip(),
                "label_crop_exists": int(bool(label_crop_path and Path(label_crop_path).exists())),
                "full_crop_exists": int(bool(full_crop_path and Path(full_crop_path).exists())),
                "label_crop_has_label_manual": "",
                "full_crop_has_label_manual": "",
                "detected_numbers_source_guess_manual": "",
                "manual_root_cause_override": "",
                "manual_notes": "",
            }
        )

    return output


def build_summary(rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    root_counts = Counter(str(row.get("proxy_root_cause_class", "") or "") for row in rows)
    run_counts = Counter(str(row.get("run_date", "") or "") for row in rows)
    return {
        "sample_rows": len(rows),
        "proxy_root_cause_counts": dict(sorted(root_counts.items())),
        "sample_run_counts": dict(sorted(run_counts.items())),
    }


def to_markdown(summary: Dict[str, object], input_csv: Path, output_csv: Path, output_html: Path) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    sample_rows = int(summary.get("sample_rows", 0) or 0)
    root_counts = summary.get("proxy_root_cause_counts", {})
    if not isinstance(root_counts, dict):
        root_counts = {}
    run_counts = summary.get("sample_run_counts", {})
    if not isinstance(run_counts, dict):
        run_counts = {}

    root_table_lines = ["| Proxy Class | Count |", "|---|---:|"]
    for key, value in sorted(root_counts.items()):
        root_table_lines.append(f"| `{key}` | {value} |")

    run_table_lines = ["| Run Date | Sample Rows |", "|---|---:|"]
    for key, value in sorted(run_counts.items()):
        run_table_lines.append(f"| `{key}` | {value} |")

    return "\n".join(
        [
            "# V1.7 SW-0 OCR Crop Diagnosis",
            "",
            f"Generated (UTC): `{generated_at}`",
            "",
            "## Scope",
            "",
            "Proxy diagnosis packet for Sprint 0 using sampled hard-queue rows.",
            f"- Input queue: `{input_csv}`",
            f"- Output diagnosis CSV: `{output_csv}`",
            f"- Output visual packet: `{output_html}`",
            f"- Sample size: `{sample_rows}`",
            "",
            "## Proxy Root-Cause Distribution",
            "",
            *root_table_lines,
            "",
            "## Sample Distribution by Run",
            "",
            *run_table_lines,
            "",
            "## Interpretation",
            "",
            "- This output is a proxy diagnosis based on OCR variant logs and crop artifacts.",
            "- Complete SW-0 requires manual visual confirmation columns in the CSV to be filled for sampled rows.",
            "- Use the HTML packet for side-by-side label/full crop inspection before deciding final root cause.",
            "",
            "## Next Action",
            "",
            "1. Manually fill `*_manual` columns in the diagnosis CSV.",
            "2. Confirm whether dominant mode is crop-targeting error or label absence/unreadability.",
            "3. Apply HITL-0 UX changes before spending reviewer time.",
        ]
    )


def to_html(rows: Sequence[Dict[str, object]], html_path: Path) -> str:
    def esc(value: object) -> str:
        text = str(value or "")
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def image_markup(raw_path: str, label: str) -> str:
        path = Path(raw_path)
        if not raw_path or not path.exists():
            return "<div class='missing'>No image</div>"
        resolved = Path(path).resolve()
        cwd = Path.cwd().resolve()
        try:
            relative = resolved.relative_to(cwd)
        except ValueError:
            relative = resolved
        url = Path("..") / relative if html_path.parent.name == "tracker" else relative
        url_text = url.as_posix()
        return (
            f"<a href='{esc(url_text)}' target='_blank' rel='noreferrer'>"
            f"<img src='{esc(url_text)}' alt='{esc(label)}' loading='lazy' />"
            "</a>"
        )

    cards = []
    for row in rows:
        cards.append(
            """<article class='card'>
<header>
<h3>{pot_id} <span>{run_date}</span></h3>
<p>row={row_index} | asset={asset}</p>
</header>
<div class='images'>
<figure><figcaption>Label Crop</figcaption>{label_img}</figure>
<figure><figcaption>Center Crop</figcaption>{center_img}</figure>
<figure><figcaption>Full Crop</figcaption>{full_img}</figure>
</div>
<div class='meta'>
<p><strong>Proxy Class:</strong> {proxy_class}</p>
<p><strong>Reason:</strong> {proxy_reason}</p>
<p><strong>Label Numbers:</strong> <code>{label_numbers}</code></p>
<p><strong>Non-label Numbers:</strong> <code>{non_label_numbers}</code></p>
<p><a href='{photo_url}' target='_blank' rel='noreferrer'>Open Original Photo</a></p>
</div>
</article>""".format(
                pot_id=esc(row.get("pot_id", "")),
                run_date=esc(row.get("run_date", "")),
                row_index=esc(row.get("row_index", "")),
                asset=esc(row.get("source_asset_id", "")),
                label_img=image_markup(str(row.get("label_crop_path", "")), "label crop"),
                center_img=image_markup(str(row.get("center_crop_path", "")), "center crop"),
                full_img=image_markup(str(row.get("full_crop_path", "")), "full crop"),
                proxy_class=esc(row.get("proxy_root_cause_class", "")),
                proxy_reason=esc(row.get("proxy_root_cause_reason", "")),
                label_numbers=esc(row.get("label_numbers_detected", "none")),
                non_label_numbers=esc(row.get("non_label_numbers_detected", "none")),
                photo_url=esc(row.get("photo_url", "")),
            )
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    card_html = "\n".join(cards) if cards else "<p>No rows sampled.</p>"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>SW-0 OCR Crop Diagnosis Sample</title>
  <style>
    body {{ margin: 0; font-family: 'Avenir Next', 'Trebuchet MS', sans-serif; background: #f4f0e3; color: #1f2b29; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px; }}
    .card {{ border: 1px solid #d8d1c2; border-radius: 12px; background: #fffdf7; overflow: hidden; }}
    .card header {{ padding: 10px; border-bottom: 1px solid #e8e0ce; background: #f7f2e6; }}
    .card h3 {{ margin: 0 0 4px; }}
    .card h3 span {{ font-size: 0.8rem; color: #5d6d68; margin-left: 5px; }}
    .card p {{ margin: 0; font-size: 0.8rem; color: #4f5f5a; }}
    .images {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; padding: 8px; }}
    figure {{ margin: 0; border: 1px solid #e4dccb; border-radius: 8px; overflow: hidden; background: #f0eadb; }}
    figcaption {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; padding: 4px 6px; background: #faf6ec; border-bottom: 1px solid #e4dccb; }}
    img {{ width: 100%; display: block; }}
    .missing {{ padding: 24px 8px; text-align: center; color: #6c7a74; font-size: 0.78rem; }}
    .meta {{ padding: 8px 10px 10px; display: grid; gap: 4px; border-top: 1px solid #ece4d3; }}
    .meta code {{ background: #f0ead9; padding: 1px 4px; border-radius: 4px; }}
    @media (max-width: 900px) {{ .images {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <h1>SW-0 OCR Crop Diagnosis Sample</h1>
    <p>Generated (UTC): <code>{generated_at}</code></p>
    <p>Proxy packet for manual validation of label/full crop visibility.</p>
    <section class=\"grid\">{card_html}</section>
  </main>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build Sprint 0 OCR crop diagnosis packet from hard-row queue.",
    )
    parser.add_argument(
        "--queue-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/manual_label_queue.csv"),
        help="Input hard-row queue CSV.",
    )
    parser.add_argument(
        "--ocr-detail-csv",
        type=Path,
        default=Path("data/research/v1_6/ocr_recovery/ocr_variant_eval_details.csv"),
        help="OCR variant detail CSV for row-level variant behavior.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of queue rows to sample for SW-0 diagnosis.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/v1_7/sw0_ocr_crop_diagnosis.csv"),
        help="Output diagnosis CSV path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/V1.7-SW0-OCR-CROP-DIAGNOSIS.md"),
        help="Output markdown report path.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/sw0-ocr-diagnosis-sample.html"),
        help="Output HTML visual packet path.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    queue_rows = read_csv_rows(args.queue_csv)
    detail_rows = read_csv_rows(args.ocr_detail_csv) if args.ocr_detail_csv.exists() else []

    detail_by_key: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in detail_rows:
        key = row_key(row)
        detail_by_key[key].append(row)

    sampled_rows = choose_sample_rows(queue_rows, sample_size=args.sample_size)
    diagnosis_rows = build_diagnosis_rows(sampled_rows, detail_by_key)
    summary = build_summary(diagnosis_rows)

    write_csv(
        args.output_csv,
        diagnosis_rows,
        fieldnames=[
            "run_date",
            "row_index",
            "source_asset_id",
            "pot_id",
            "pot_number",
            "matched_variant_count",
            "ensemble_numbers_detected",
            "label_numbers_detected",
            "non_label_numbers_detected",
            "label_match_any",
            "non_label_match_any",
            "label_variants_with_digits",
            "non_label_variants_with_digits",
            "proxy_root_cause_class",
            "proxy_root_cause_reason",
            "label_crop_path",
            "center_crop_path",
            "full_crop_path",
            "photo_url",
            "label_crop_exists",
            "full_crop_exists",
            "label_crop_has_label_manual",
            "full_crop_has_label_manual",
            "detected_numbers_source_guess_manual",
            "manual_root_cause_override",
            "manual_notes",
        ],
    )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        to_markdown(summary, args.queue_csv, args.output_csv, args.output_html),
        encoding="utf-8",
    )

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(to_html(diagnosis_rows, args.output_html), encoding="utf-8")

    print(f"queue_rows={len(queue_rows)}")
    print(f"sample_rows={len(sampled_rows)}")
    print(f"output_csv={args.output_csv}")
    print(f"output_md={args.output_md}")
    print(f"output_html={args.output_html}")
    print(f"proxy_root_cause_counts={summary['proxy_root_cause_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
