#!/usr/bin/env python3
"""Build the Tomato Trails Phase 1 landing page."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from stable_generated_output import stabilize_rendered_text, write_text_if_changed

BUCKET_META: Mapping[str, Mapping[str, str]] = {
    "strong_establishment": {
        "label": "Strong Establishment",
        "tone": "strong",
        "deck": "Clear foliage gain and a stable end-of-phase plant.",
    },
    "modest_establishment": {
        "label": "Modest Establishment",
        "tone": "watch",
        "deck": "Alive and improved, but still small or behind the leaders.",
    },
    "stalled_or_failed": {
        "label": "Stalled or Failed",
        "tone": "stall",
        "deck": "The baseline sprout did not establish cleanly by the phase-one lock.",
    },
    "missing_last_day": {
        "label": "Missing Last Day",
        "tone": "stall",
        "deck": "No canonical last-day image is currently attached to this pot.",
    },
}

PRIORITY_LABELS = {
    "high": "High follow-up priority",
    "medium": "Medium follow-up priority",
    "low": "Low follow-up priority",
}

READINESS_LABELS = {
    "high": "High CV readiness",
    "moderate": "Moderate CV readiness",
    "low": "Low CV readiness",
    "unknown": "Not scored yet",
}

VARIETY_PROFILES: Mapping[str, Mapping[str, str]] = {
    "Azoychka": {
        "type_label": "Yellow/orange heirloom slicer",
        "maturity_label": "Midseason",
        "fog_outlook": "Promising if early vigor holds",
        "expectation": (
            "Phase 1 is mostly strong for Azoychka, but the Sausalito test is whether those "
            "vigorous seedlings can keep sizing up once the marine layer suppresses heat later in the season."
        ),
        "profile_note": "Large-fruited heirlooms still need real warmth to ripen cleanly in the fog belt.",
    },
    "Gold Dust": {
        "type_label": "Yellow line; packet details still being preserved in repo",
        "maturity_label": "Exact DTM not yet confirmed here",
        "fog_outlook": "Encouraging early signal",
        "expectation": (
            "Gold Dust has a strong Phase 1 start, so the next question is whether that early establishment "
            "translates into durable growth once the plants leave the indoor seedling stage."
        ),
        "profile_note": "Keep packet-level growth habit and maturity details attached when they are recovered.",
    },
    "Heinz 9129": {
        "type_label": "Processing / paste line",
        "maturity_label": "Midseason",
        "fog_outlook": "Needs more proof in Sausalito",
        "expectation": (
            "The Phase 1 pair set keeps Heinz 9129 on the watchlist. Processing tomatoes can be productive, "
            "but they still need enough warmth to thicken canopy and move into fruit set without stalling."
        ),
        "profile_note": "Both visible Heinz 9129 pots stayed in the modest tier by the phase-one lock.",
    },
    "Iles Yellow Latvian": {
        "type_label": "Yellow heirloom slicer",
        "maturity_label": "Midseason",
        "fog_outlook": "Mixed but promising",
        "expectation": (
            "This line is mostly positive in Phase 1, but the weaker holdouts suggest it may still need "
            "more heat than the cherry-sized candidates once the season moves beyond seedling establishment."
        ),
        "profile_note": "A good candidate to compare against both the cherry cohort and the larger-fruited watchlist group.",
    },
    "Japanese Black Trifele": {
        "type_label": "Dark pear/plum heirloom",
        "maturity_label": "Midseason",
        "fog_outlook": "Promising early, still unproven later",
        "expectation": (
            "Japanese Black Trifele established well in Phase 1. The real Sausalito question is whether it keeps "
            "enough momentum to ripen reliably in a shorter, cooler light window."
        ),
        "profile_note": "Good establishment does not automatically guarantee clean ripening for darker midseason fruit.",
    },
    "Nikolayev Yellow Cherry": {
        "type_label": "Yellow cherry",
        "maturity_label": "Early to midseason",
        "fog_outlook": "One of the better fits on paper",
        "expectation": (
            "Small-fruited cherries have the strongest structural advantage in Sausalito's fog. "
            "This cohort is already mostly strong in Phase 1, so it should stay near the front of the pack if disease pressure stays manageable."
        ),
        "profile_note": "Cherry fruit size lowers the heat burden per fruit compared with slicers or paste types.",
    },
    "San Francisco Fog": {
        "type_label": "Locally named line; exact packet details not yet preserved",
        "maturity_label": "Packet DTM still needs confirmation",
        "fog_outlook": "Promising local bet with a split seedling signal",
        "expectation": (
            "The name suggests a coastal fit, and the Phase 1 set splits evenly between strong and modest pots. "
            "That makes it an especially useful local experiment: if the stronger plants keep separating from the weaker ones, the variety may still prove adapted."
        ),
        "profile_note": "Keep this line under close observation because its local naming makes the trial evidence especially valuable.",
    },
    "Sasha Altai": {
        "type_label": "Early Siberian/Russian slicer",
        "maturity_label": "Early for a larger-fruited tomato",
        "fog_outlook": "Worth watching closely",
        "expectation": (
            "Sasha Altai should have a cool-climate argument on paper, but the Phase 1 set is mixed because one pot stalled out entirely. "
            "It stays in the experiment's prove-it tier until post-transplant growth is more consistent."
        ),
        "profile_note": "The strong 7T versus failed 16T split makes this one a high-information comparison variety.",
    },
    "Sunset's Red Horizon": {
        "type_label": "Locally named red line; exact packet details still being preserved",
        "maturity_label": "Packet DTM still needs confirmation",
        "fog_outlook": "Leading early signal",
        "expectation": (
            "Sunset's Red Horizon is one of the cleanest Phase 1 performers. "
            "If that early lead continues after transplant, it becomes a serious candidate for a Sausalito-adapted keeper."
        ),
        "profile_note": "Strong seedling establishment alone is not enough; keep watching whether the line stays compact and productive in colder spells.",
    },
    "Taxi": {
        "type_label": "Early determinate yellow slicer",
        "maturity_label": "Early",
        "fog_outlook": "Good climate fit if stems thicken",
        "expectation": (
            "Taxi is usually the kind of early tomato that should make sense in a fog belt, so the mixed Phase 1 result is less a warning than a prompt to watch whether the leggy stems harden up."
        ),
        "profile_note": "The stronger Taxi pot suggests the variety still has upside if transplant conditions stay favorable.",
    },
    "Waimea Wild Cherry": {
        "type_label": "Cherry / wild cherry style line",
        "maturity_label": "Early to midseason",
        "fog_outlook": "Strong structural fit",
        "expectation": (
            "Wild-cherry energy plus a strong Phase 1 result makes Waimea Wild Cherry one of the most naturally fog-friendly profiles in the set. "
            "The main task is to keep it readable and contained enough for later comparisons."
        ),
        "profile_note": "This is already one of the cleaner reference pots for later segmentation and tracking work.",
    },
}

DEFAULT_PROFILE: Mapping[str, str] = {
    "type_label": "Profile details still being attached to the canonical record",
    "maturity_label": "Packet DTM still needs confirmation",
    "fog_outlook": "Needs more context",
    "expectation": (
        "Use the Phase 1 seedling signal as the temporary expectation until the packet-level profile is attached."
    ),
    "profile_note": "Keep the packet photo and seed metadata linked so this profile can be tightened later.",
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_iso_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def display_date(raw: str) -> str:
    if not (raw or "").strip():
        return "Unknown date"
    return parse_iso_date(raw).strftime("%b %d, %Y")


def bool_text(raw: str) -> str:
    value = (raw or "").strip().lower()
    return "yes" if value in {"1", "true", "yes"} else "no"


def percent_text(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def growth_delta_label(value: float | None) -> str:
    if value is None:
        return "No normalized delta yet"
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f}%"


def growth_delta_deck(value: float | None) -> str:
    if value is None:
        return "Not enough aligned history yet for a normalized delta."
    if value >= 0.25:
        return "Directional gain"
    if value >= 0.0:
        return "Slight positive signal"
    if value <= -0.25:
        return "Possible decline or framing drift"
    return "Roughly flat signal"


def pot_sort_key(value: str) -> tuple[int, str]:
    matched = re.fullmatch(r"([0-9]{1,3})T", (value or "").strip())
    if matched:
        return (int(matched.group(1)), value)
    return (10**9, value)


def load_phase_window(path: Path) -> Dict[str, str]:
    for row in read_rows(path):
        if (row.get("phase_id") or "").strip() == "phase_1_seedling":
            return {
                "phase_name": (row.get("phase_name") or "").strip() or "Phase 1 Seedling",
                "start_date": (row.get("phase_start_run_date") or "").strip(),
                "start_label": (row.get("phase_start_label") or "").strip() or "Day 1",
                "end_date": (row.get("phase_end_run_date") or "").strip(),
                "end_label": (row.get("phase_end_label") or "").strip() or "Last Day",
            }
    raise ValueError("phase_1_seedling was not found in the phase timeline")


def load_cv_metrics(path: Path) -> Dict[str, Dict[str, str]]:
    metrics: Dict[str, Dict[str, str]] = {}
    for row in read_rows(path):
        pot_id = (row.get("pot_id") or "").strip()
        if pot_id:
            metrics[pot_id] = row
    return metrics


def build_variety_phase_signal(rows: List[Dict[str, str]]) -> Dict[str, str]:
    counts: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[(row.get("variety_name") or "").strip()][
            (row.get("analysis_bucket") or "").strip()
        ] += 1
    signal: Dict[str, str] = {}
    for name, counter in counts.items():
        strong = counter.get("strong_establishment", 0)
        modest = counter.get("modest_establishment", 0)
        stalled = counter.get("stalled_or_failed", 0)
        total = sum(counter.values())
        watch = modest + stalled
        signal[name] = (
            f"{strong} of {total} pots landed strong"
            if not watch
            else f"{strong} strong, {watch} watchlist pots"
        )
    return signal


def build_pot_records(
    triage_rows: List[Dict[str, str]],
    metrics_by_pot: Mapping[str, Mapping[str, str]],
) -> List[Dict[str, object]]:
    variety_phase_signal = build_variety_phase_signal(triage_rows)
    output: List[Dict[str, object]] = []

    for index, row in enumerate(
        sorted(triage_rows, key=lambda item: pot_sort_key((item.get("pot_id") or "").strip())),
        start=1,
    ):
        pot_id = (row.get("pot_id") or "").strip()
        variety_name = (row.get("variety_name") or "").strip() or "Unknown variety"
        bucket = (row.get("analysis_bucket") or "").strip() or "modest_establishment"
        bucket_meta = BUCKET_META.get(bucket, BUCKET_META["modest_establishment"])
        profile = dict(DEFAULT_PROFILE)
        profile.update(VARIETY_PROFILES.get(variety_name, {}))

        metric_row = metrics_by_pot.get(pot_id, {})
        focus_score = safe_float(metric_row.get("focus_score", ""))
        pot_coverage = safe_float(metric_row.get("pot_coverage", ""))
        in_pot_spill = safe_float(metric_row.get("spill_in_pot_ratio", ""))
        neighbor_spill = safe_float(metric_row.get("neighbor_spill_ratio", ""))
        growth_delta = safe_float(metric_row.get("growth_delta", ""))
        readiness = (metric_row.get("tracking_readiness") or "").strip().lower() or "unknown"

        cv_story_parts = [READINESS_LABELS.get(readiness, READINESS_LABELS["unknown"])]
        if pot_coverage is not None:
            cv_story_parts.append(f"{percent_text(pot_coverage)} in-pot canopy")
        if neighbor_spill is not None:
            cv_story_parts.append(f"{percent_text(neighbor_spill)} neighbor spill")
        if growth_delta is not None:
            cv_story_parts.append(f"{growth_delta_label(growth_delta)} growth signal")
        cv_story = ". ".join(cv_story_parts) + "."

        record = {
            "index": index,
            "pot_id": pot_id,
            "varietal_number": (row.get("varietal_number") or "").strip(),
            "variety_name": variety_name,
            "bucket": bucket,
            "bucket_label": bucket_meta["label"],
            "bucket_tone": bucket_meta["tone"],
            "bucket_deck": bucket_meta["deck"],
            "analysis_notes": (row.get("analysis_notes") or "").strip()
            or bucket_meta["deck"],
            "priority": (row.get("follow_up_priority") or "").strip() or "medium",
            "priority_label": PRIORITY_LABELS.get(
                (row.get("follow_up_priority") or "").strip(), PRIORITY_LABELS["medium"]
            ),
            "is_watchlist": bucket in {"modest_establishment", "stalled_or_failed", "missing_last_day"},
            "day_one_label": display_date((row.get("run_a_date") or "").strip()),
            "day_one_date": (row.get("run_a_date") or "").strip(),
            "day_one_photo_url": (row.get("run_a_photo_url") or "").strip(),
            "day_one_asset_id": (row.get("run_a_asset_id") or "").strip(),
            "day_one_ocr_confirms_pot": bool_text(row.get("run_a_ocr_confirms_pot", "")),
            "last_day_label": display_date((row.get("run_b_date") or "").strip()),
            "last_day_date": (row.get("run_b_date") or "").strip(),
            "last_day_photo_url": (row.get("run_b_photo_url") or "").strip(),
            "last_day_asset_id": (row.get("run_b_asset_id") or "").strip(),
            "last_day_ocr_confirms_pot": bool_text(row.get("run_b_ocr_confirms_pot", "")),
            "type_label": profile["type_label"],
            "maturity_label": profile["maturity_label"],
            "fog_outlook": profile["fog_outlook"],
            "expectation": profile["expectation"],
            "profile_note": profile["profile_note"],
            "variety_phase_signal": variety_phase_signal.get(variety_name, ""),
            "cv_readiness": readiness,
            "cv_readiness_label": READINESS_LABELS.get(readiness, READINESS_LABELS["unknown"]),
            "cv_focus_pct": percent_text(focus_score),
            "cv_coverage_pct": percent_text(pot_coverage),
            "cv_in_pot_spill_pct": percent_text(in_pot_spill),
            "cv_neighbor_spill_pct": percent_text(neighbor_spill),
            "cv_growth_delta_pct": growth_delta_label(growth_delta),
            "cv_growth_delta_deck": growth_delta_deck(growth_delta),
            "cv_next_step": (metric_row.get("next_step_text") or "").strip()
            or "CV follow-up is not attached to this pot yet.",
            "cv_story": cv_story,
            "search_blob": " ".join(
                [
                    pot_id,
                    variety_name,
                    bucket_meta["label"],
                    profile["fog_outlook"],
                    profile["expectation"],
                    (row.get("analysis_notes") or "").strip(),
                ]
            ).lower(),
        }
        output.append(record)
    return output


def build_variety_cards(pot_records: List[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in pot_records:
        grouped[str(row["variety_name"])][str(row["bucket"])] += 1

    cards: List[Dict[str, object]] = []
    for variety_name, counter in grouped.items():
        profile = dict(DEFAULT_PROFILE)
        profile.update(VARIETY_PROFILES.get(variety_name, {}))
        strong = counter.get("strong_establishment", 0)
        modest = counter.get("modest_establishment", 0)
        stalled = counter.get("stalled_or_failed", 0)
        total = sum(counter.values())
        if stalled:
            signal = "Mixed early signal"
        elif strong == total and total > 1:
            signal = "Leading early signal"
        elif strong and modest:
            signal = "Mixed but promising"
        elif strong:
            signal = "Positive early signal"
        else:
            signal = "Needs more proof"
        cards.append(
            {
                "variety_name": variety_name,
                "type_label": profile["type_label"],
                "fog_outlook": profile["fog_outlook"],
                "expectation": profile["expectation"],
                "signal": signal,
                "pot_count": total,
                "strong_count": strong,
                "watch_count": modest + stalled,
            }
        )
    cards.sort(
        key=lambda item: (
            -(int(item["strong_count"])),
            int(item["watch_count"]),
            str(item["variety_name"]),
        )
    )
    return cards


def build_page_stats(
    pot_records: List[Mapping[str, object]],
    metrics_by_pot: Mapping[str, Mapping[str, str]],
    phase_window: Mapping[str, str],
) -> Dict[str, object]:
    bucket_counts = Counter(str(row["bucket"]) for row in pot_records)
    unique_varieties = len({str(row["variety_name"]) for row in pot_records})
    start_date = parse_iso_date(str(phase_window["start_date"]))
    end_date = parse_iso_date(str(phase_window["end_date"]))
    growth_delta_count = sum(
        1 for row in metrics_by_pot.values() if safe_float(row.get("growth_delta", "")) is not None
    )
    return {
        "total_pots": len(pot_records),
        "unique_varieties": unique_varieties,
        "strong_count": bucket_counts.get("strong_establishment", 0),
        "watch_count": bucket_counts.get("modest_establishment", 0)
        + bucket_counts.get("stalled_or_failed", 0),
        "stalled_count": bucket_counts.get("stalled_or_failed", 0),
        "days_between": (end_date - start_date).days,
        "inclusive_days": (end_date - start_date).days + 1,
        "growth_delta_count": growth_delta_count,
        "cv_metric_count": len(metrics_by_pot),
        "phase_name": str(phase_window["phase_name"]),
        "start_label": str(phase_window["start_label"]),
        "start_date_label": display_date(str(phase_window["start_date"])),
        "end_label": str(phase_window["end_label"]),
        "end_date_label": display_date(str(phase_window["end_date"])),
    }


def build_reference_pots(pot_records: List[Mapping[str, object]]) -> List[Dict[str, str]]:
    candidates = [
        row
        for row in pot_records
        if row["bucket"] == "strong_establishment"
        and row["cv_readiness"] in {"high", "moderate"}
    ]
    candidates.sort(
        key=lambda row: (
            row["cv_readiness"] != "high",
            row["cv_focus_pct"] == "n/a",
            row["pot_id"],
        )
    )
    return [
        {
            "pot_id": str(row["pot_id"]),
            "variety_name": str(row["variety_name"]),
            "note": str(row["analysis_notes"]),
        }
        for row in candidates[:6]
    ]


def build_watchlist_pots(pot_records: List[Mapping[str, object]]) -> List[Dict[str, str]]:
    candidates = [row for row in pot_records if bool(row["is_watchlist"])]
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(
        key=lambda row: (
            priority_rank.get(str(row["priority"]), 3),
            pot_sort_key(str(row["pot_id"])),
        )
    )
    return [
        {
            "pot_id": str(row["pot_id"]),
            "variety_name": str(row["variety_name"]),
            "bucket_label": str(row["bucket_label"]),
        }
        for row in candidates
    ]


def build_page(
    pot_records: List[Mapping[str, object]],
    variety_cards: List[Mapping[str, object]],
    stats: Mapping[str, object],
    reference_pots: List[Mapping[str, str]],
    watchlist_pots: List[Mapping[str, str]],
) -> str:
    pots_json = json.dumps(pot_records, ensure_ascii=True)
    varieties_json = json.dumps(variety_cards, ensure_ascii=True)
    stats_json = json.dumps(stats, ensure_ascii=True)
    reference_json = json.dumps(reference_pots, ensure_ascii=True)
    watchlist_json = json.dumps(watchlist_pots, ensure_ascii=True)

    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>K's Tomato Trails 2026: Phase 1 Landing Page</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {
      --paper: #f5efe2;
      --paper-strong: #fff9ef;
      --mist: #d7e2dd;
      --fog: #aab8b2;
      --moss: #2f604a;
      --forest: #214233;
      --tomato: #b84831;
      --tomato-deep: #8c3325;
      --sun: #cf8a2d;
      --stall: #823748;
      --ink: #1d241f;
      --muted: #5d675e;
      --line: rgba(29, 36, 31, 0.12);
      --shadow: 0 22px 50px rgba(38, 44, 38, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      margin: 0;
      color: var(--ink);
      font-family: "Instrument Sans", "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(900px 460px at 0% 0%, rgba(207, 138, 45, 0.15), transparent 60%),
        radial-gradient(1000px 480px at 100% 0%, rgba(47, 96, 74, 0.18), transparent 65%),
        linear-gradient(180deg, #efe7d6 0%, #f7f1e6 42%, #f1ebdd 100%);
    }

    body.lightbox-open {
      overflow: hidden;
    }

    a {
      color: inherit;
    }

    button,
    input {
      font: inherit;
    }

    .shell {
      max-width: 1400px;
      margin: 0 auto;
      padding: 22px 18px 48px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      padding: 26px;
      border-radius: 30px;
      border: 1px solid rgba(29, 36, 31, 0.08);
      background:
        linear-gradient(145deg, rgba(255, 249, 239, 0.92), rgba(243, 234, 220, 0.92)),
        linear-gradient(120deg, rgba(47, 96, 74, 0.10), rgba(184, 72, 49, 0.08));
      box-shadow: var(--shadow);
    }

    .hero::before {
      content: "";
      position: absolute;
      inset: auto -6% -24% auto;
      width: 360px;
      height: 360px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(47, 96, 74, 0.24) 0%, rgba(47, 96, 74, 0) 68%);
      pointer-events: none;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: -18% auto auto -8%;
      width: 320px;
      height: 320px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(207, 138, 45, 0.20) 0%, rgba(207, 138, 45, 0) 70%);
      pointer-events: none;
    }

    .hero-top {
      position: relative;
      z-index: 1;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }

    .nav-links {
      display: inline-flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .nav-link {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.74);
      border: 1px solid rgba(29, 36, 31, 0.08);
      color: var(--forest);
      text-decoration: none;
      font-size: 0.92rem;
      font-weight: 600;
    }

    .eyebrow {
      margin: 0 0 10px;
      color: var(--forest);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-size: 0.8rem;
      font-weight: 700;
    }

    .hero-grid {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.9fr);
      gap: 20px;
      align-items: start;
    }

    h1 {
      margin: 0;
      max-width: 16ch;
      font-family: "Fraunces", "Iowan Old Style", Georgia, serif;
      font-size: clamp(2.2rem, 5vw, 4.4rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }

    .lede {
      max-width: 70ch;
      margin: 16px 0 0;
      color: var(--muted);
      font-size: 1.06rem;
      line-height: 1.7;
    }

    .hero-meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 22px;
    }

    .hero-stat {
      padding: 16px 16px 14px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(29, 36, 31, 0.08);
      backdrop-filter: blur(8px);
    }

    .hero-stat-label {
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-size: 0.72rem;
      color: var(--muted);
      font-weight: 700;
    }

    .hero-stat-value {
      margin: 8px 0 0;
      font-family: "Fraunces", Georgia, serif;
      font-size: 1.75rem;
      line-height: 1;
    }

    .hero-aside {
      display: grid;
      gap: 14px;
    }

    .phase-card,
    .section-card,
    .toolbar-card,
    .variety-board,
    .method-card,
    .gallery-shell {
      background: rgba(255, 252, 247, 0.82);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }

    .phase-card {
      padding: 20px;
      background:
        radial-gradient(circle at top right, rgba(47, 96, 74, 0.14), transparent 42%),
        rgba(255, 252, 247, 0.86);
    }

    .phase-card h2,
    .section-card h2,
    .variety-board h2,
    .gallery-shell h2,
    .method-card h2 {
      margin: 0;
      font-family: "Fraunces", Georgia, serif;
      font-size: 1.34rem;
      line-height: 1.1;
    }

    .phase-card p,
    .section-card p,
    .method-card p {
      color: var(--muted);
      line-height: 1.65;
    }

    .phase-anchors {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }

    .anchor-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(245, 239, 226, 0.9);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .anchor-row strong {
      display: block;
      font-size: 0.82rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .anchor-row span {
      display: block;
      margin-top: 4px;
      font-weight: 700;
    }

    .signal-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }

    .signal-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 0.9rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .signal-pill strong {
      font-family: "Fraunces", Georgia, serif;
      font-size: 1rem;
    }

    .story-grid,
    .method-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }

    .section-card,
    .method-card {
      padding: 20px;
    }

    .section-card ul,
    .method-card ul {
      margin: 14px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.6;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }

    .mini-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(29, 36, 31, 0.08);
      font-size: 0.9rem;
      color: var(--forest);
    }

    .mini-chip strong {
      font-family: "Fraunces", Georgia, serif;
      font-size: 1rem;
    }

    .variety-board {
      margin-top: 18px;
      padding: 22px;
      background:
        radial-gradient(circle at top left, rgba(47, 96, 74, 0.12), transparent 38%),
        rgba(255, 252, 247, 0.86);
    }

    .section-head {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      align-items: end;
      margin-bottom: 16px;
    }

    .section-head p {
      margin: 8px 0 0;
      color: var(--muted);
    }

    .variety-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
    }

    .variety-card {
      padding: 16px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .variety-card h3 {
      margin: 6px 0 0;
      font-size: 1.02rem;
    }

    .variety-meta {
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .variety-meta div {
      padding: 10px 11px;
      border-radius: 16px;
      background: rgba(245, 239, 226, 0.9);
      border: 1px solid rgba(29, 36, 31, 0.06);
    }

    .variety-meta dt {
      margin: 0;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .variety-meta dd {
      margin: 6px 0 0;
      font-weight: 700;
    }

    .toolbar-card {
      position: sticky;
      top: 10px;
      z-index: 6;
      margin-top: 18px;
      padding: 18px;
      backdrop-filter: blur(12px);
      background: rgba(255, 251, 245, 0.88);
    }

    .toolbar-top {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }

    .search-input {
      flex: 1 1 260px;
      padding: 14px 16px;
      border-radius: 999px;
      border: 1px solid rgba(29, 36, 31, 0.12);
      background: rgba(255, 255, 255, 0.92);
      color: var(--ink);
      min-width: 240px;
    }

    .filter-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .filter-btn {
      padding: 11px 14px;
      border-radius: 999px;
      border: 1px solid rgba(29, 36, 31, 0.10);
      background: rgba(255, 255, 255, 0.88);
      color: var(--forest);
      cursor: pointer;
      font-weight: 600;
    }

    .filter-btn.active {
      background: var(--forest);
      border-color: var(--forest);
      color: #fff;
    }

    .toolbar-bottom {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px 16px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .gallery-shell {
      margin-top: 16px;
      padding: 18px;
    }

    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
    }

    .empty-state {
      padding: 34px 20px;
      border-radius: 20px;
      text-align: center;
      color: var(--muted);
      background: rgba(245, 239, 226, 0.9);
      border: 1px dashed rgba(29, 36, 31, 0.14);
    }

    .pot-card {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 18px;
      border-radius: 24px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(250, 246, 238, 0.96));
      border: 1px solid rgba(29, 36, 31, 0.10);
      box-shadow: 0 16px 34px rgba(38, 44, 38, 0.08);
    }

    .pot-card.strong {
      box-shadow: 0 16px 34px rgba(47, 96, 74, 0.14);
    }

    .pot-card.watch {
      box-shadow: 0 16px 34px rgba(156, 106, 45, 0.14);
    }

    .pot-card.stall {
      box-shadow: 0 16px 34px rgba(130, 55, 72, 0.14);
    }

    .card-header {
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: start;
    }

    .card-kicker {
      margin: 0;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.74rem;
      font-weight: 700;
    }

    .card-header h3 {
      margin: 6px 0 0;
      font-size: 1.16rem;
      line-height: 1.2;
    }

    .bucket-pill {
      white-space: nowrap;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }

    .bucket-pill.strong {
      background: rgba(47, 96, 74, 0.12);
      color: var(--moss);
    }

    .bucket-pill.watch {
      background: rgba(207, 138, 45, 0.16);
      color: #85561f;
    }

    .bucket-pill.stall {
      background: rgba(130, 55, 72, 0.14);
      color: var(--stall);
    }

    .photo-surface {
      position: relative;
      display: block;
      width: 100%;
      padding: 0;
      border: 0;
      background: transparent;
      cursor: zoom-in;
      text-align: left;
    }

    .flip-shell {
      position: relative;
      aspect-ratio: 4 / 5;
      perspective: 1400px;
    }

    .flip-stage {
      position: absolute;
      inset: 0;
      transform-style: preserve-3d;
      transition: transform 0.8s ease;
    }

    .flip-stage.is-flipped {
      transform: rotateY(180deg);
    }

    .face {
      position: absolute;
      inset: 0;
      margin: 0;
      overflow: hidden;
      border-radius: 22px;
      border: 1px solid rgba(29, 36, 31, 0.10);
      backface-visibility: hidden;
      background: linear-gradient(180deg, rgba(215, 226, 221, 0.72), rgba(245, 239, 226, 0.88));
    }

    .face.back {
      transform: rotateY(180deg);
    }

    .face img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .face-copy {
      position: absolute;
      inset: auto 14px 14px 14px;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 12px;
    }

    .face-label {
      display: inline-flex;
      flex-direction: column;
      gap: 3px;
      padding: 9px 12px;
      border-radius: 16px;
      background: rgba(20, 22, 20, 0.64);
      color: #fff;
      max-width: calc(100% - 86px);
    }

    .face-label strong {
      font-size: 0.9rem;
    }

    .face-label span {
      font-size: 0.74rem;
      color: rgba(255, 255, 255, 0.82);
    }

    .surface-hint {
      position: absolute;
      top: 14px;
      right: 14px;
      padding: 7px 11px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.84);
      color: var(--forest);
      font-size: 0.8rem;
      font-weight: 700;
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .card-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .solid-btn,
    .ghost-btn,
    .link-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 11px 14px;
      border-radius: 999px;
      cursor: pointer;
      text-decoration: none;
      font-weight: 700;
    }

    .solid-btn {
      border: 1px solid var(--forest);
      background: var(--forest);
      color: #fff;
    }

    .ghost-btn {
      border: 1px solid rgba(29, 36, 31, 0.12);
      background: rgba(255, 255, 255, 0.78);
      color: var(--forest);
    }

    .link-btn {
      border: 1px solid rgba(29, 36, 31, 0.10);
      background: rgba(255, 255, 255, 0.84);
      color: var(--forest);
    }

    .card-summary {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      min-height: 4.2em;
    }

    .card-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin: 0;
    }

    .card-metrics div {
      padding: 12px 12px 11px;
      border-radius: 18px;
      background: rgba(245, 239, 226, 0.92);
      border: 1px solid rgba(29, 36, 31, 0.06);
    }

    .card-metrics dt {
      margin: 0;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .card-metrics dd {
      margin: 6px 0 0;
      font-weight: 700;
      line-height: 1.35;
    }

    .method-grid {
      margin-top: 18px;
    }

    .method-card a {
      color: var(--forest);
      font-weight: 700;
    }

    .footer-note {
      margin-top: 20px;
      color: var(--muted);
      font-size: 0.9rem;
      text-align: right;
    }

    .lightbox[hidden] {
      display: none;
    }

    .lightbox {
      position: fixed;
      inset: 0;
      z-index: 30;
    }

    .lightbox-scrim {
      position: absolute;
      inset: 0;
      background: rgba(17, 20, 18, 0.72);
      backdrop-filter: blur(14px);
    }

    .lightbox-panel {
      position: relative;
      width: min(1320px, calc(100vw - 28px));
      max-height: calc(100vh - 28px);
      margin: 14px auto;
      overflow: auto;
      padding: 20px;
      border-radius: 28px;
      border: 1px solid rgba(255, 255, 255, 0.10);
      background: rgba(252, 248, 242, 0.96);
      box-shadow: 0 30px 60px rgba(0, 0, 0, 0.22);
    }

    .lightbox-close {
      position: sticky;
      top: 0;
      float: right;
      z-index: 1;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid rgba(29, 36, 31, 0.12);
      background: rgba(255, 255, 255, 0.92);
      color: var(--forest);
      cursor: pointer;
      font-weight: 700;
    }

    .lightbox-layout {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.9fr);
      gap: 20px;
      clear: both;
    }

    .comparison-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .comparison-card {
      margin: 0;
      padding: 0;
      overflow: hidden;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(29, 36, 31, 0.10);
    }

    .comparison-card img {
      width: 100%;
      aspect-ratio: 4 / 5;
      object-fit: cover;
      display: block;
      background: linear-gradient(180deg, rgba(215, 226, 221, 0.72), rgba(245, 239, 226, 0.88));
    }

    .comparison-copy {
      padding: 14px 16px 16px;
    }

    .comparison-copy strong {
      display: block;
      font-size: 0.98rem;
    }

    .comparison-copy span {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.88rem;
    }

    .lightbox-copy {
      display: grid;
      gap: 14px;
      align-content: start;
    }

    .lightbox-kicker {
      margin: 0;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .lightbox-title {
      margin: 0;
      font-family: "Fraunces", Georgia, serif;
      font-size: clamp(1.8rem, 2vw, 2.4rem);
      line-height: 1.05;
    }

    .lightbox-subtitle {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }

    .detail-block {
      padding: 16px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .detail-block h3 {
      margin: 0;
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--forest);
    }

    .detail-block p {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.65;
    }

    .detail-stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }

    .detail-stats div {
      padding: 12px;
      border-radius: 16px;
      background: rgba(245, 239, 226, 0.9);
      border: 1px solid rgba(29, 36, 31, 0.06);
    }

    .detail-stats dt {
      margin: 0;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .detail-stats dd {
      margin: 7px 0 0;
      font-weight: 700;
      line-height: 1.35;
    }

    .lightbox-footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid rgba(29, 36, 31, 0.08);
    }

    .lightbox-position {
      color: var(--muted);
      font-weight: 600;
    }

    @media (max-width: 1100px) {
      .hero-grid,
      .lightbox-layout,
      .story-grid,
      .method-grid {
        grid-template-columns: 1fr;
      }

      .hero-meta {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 820px) {
      .comparison-grid,
      .card-metrics,
      .detail-stats {
        grid-template-columns: 1fr;
      }

      .hero {
        padding: 22px;
      }

      .hero-meta {
        grid-template-columns: 1fr;
      }

      .toolbar-card {
        position: static;
      }
    }

    @media (max-width: 620px) {
      .shell {
        padding: 16px 12px 36px;
      }

      .hero,
      .section-card,
      .toolbar-card,
      .variety-board,
      .gallery-shell,
      .method-card,
      .lightbox-panel {
        border-radius: 22px;
      }

      .gallery {
        grid-template-columns: 1fr;
      }

      .card-header {
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-top">
        <div class="nav-links">
          <a class="nav-link" href="./index.html">Back to Index</a>
          <a class="nav-link" href="./v1-10-pot-cv-research.html">CV Research Board</a>
        </div>
      </div>

      <div class="hero-grid">
        <div>
          <p class="eyebrow">K's Tomato Trails 2026</p>
          <h1>Phase 1: seedling growth from day 1 to the lock.</h1>
          <p class="lede">
            This landing page keeps the project story intact while turning the tomato view into a Phase 1 comparison board.
            We are still in the seedling stage: every pot card leads with the last day of Phase 1, and a flip reveals the day-one frame so the change is easy to read at a glance.
          </p>

          <div class="hero-meta">
            <div class="hero-stat">
              <p class="hero-stat-label">Phase Window</p>
              <p class="hero-stat-value">__DAYS_BETWEEN__ days</p>
            </div>
            <div class="hero-stat">
              <p class="hero-stat-label">Locked Pots</p>
              <p class="hero-stat-value">__TOTAL_POTS__</p>
            </div>
            <div class="hero-stat">
              <p class="hero-stat-label">Strong Starts</p>
              <p class="hero-stat-value">__STRONG_COUNT__</p>
            </div>
            <div class="hero-stat">
              <p class="hero-stat-label">Watchlist</p>
              <p class="hero-stat-value">__WATCH_COUNT__</p>
            </div>
          </div>
        </div>

        <aside class="hero-aside">
          <div class="phase-card">
            <h2>What this page is showing</h2>
            <p>
              Phase 1 is the seedling-establishment chapter of Tomato Trails. The lock anchors are the canonical
              <strong>__START_LABEL__</strong> run on <strong>__START_DATE_LABEL__</strong> and the
              <strong>__END_LABEL__</strong> run on <strong>__END_DATE_LABEL__</strong>.
              That gives us a __DAYS_BETWEEN__-day comparison window, or __INCLUSIVE_DAYS__ observation days inclusive.
            </p>

            <div class="phase-anchors">
              <div class="anchor-row">
                <div>
                  <strong>Start Anchor</strong>
                  <span>__START_LABEL__</span>
                </div>
                <div>__START_DATE_LABEL__</div>
              </div>
              <div class="anchor-row">
                <div>
                  <strong>End Anchor</strong>
                  <span>__END_LABEL__</span>
                </div>
                <div>__END_DATE_LABEL__</div>
              </div>
            </div>

            <div class="signal-strip">
              <span class="signal-pill"><strong>__UNIQUE_VARIETIES__</strong> varieties</span>
              <span class="signal-pill"><strong>__STALLED_COUNT__</strong> stalled</span>
              <span class="signal-pill"><strong>__GROWTH_DELTA_COUNT__</strong> CV growth deltas</span>
            </div>
          </div>
        </aside>
      </div>
    </header>

    <section class="story-grid">
      <article class="section-card">
        <h2>Project frame</h2>
        <p>
          Tomato Trails is a citizen-science backyard trial asking which varieties can really hold up in Sausalito's cool, humid fog belt.
          The page below is intentionally narrow: it is the locked seedling story, not the whole season.
        </p>
        <p>
          The strongest Phase 1 use cases are survival checks, reference-pot selection, and deciding which seedlings need closer human follow-up before the next stage.
        </p>
      </article>

      <article class="section-card">
        <h2>Reference cohort</h2>
        <p>
          These are the clearest Phase 1 examples to reuse in future reporting and segmentation work. They combine strong establishment with at least usable CV framing.
        </p>
        <div class="chip-row" id="reference-chips"></div>
      </article>

      <article class="section-card">
        <h2>Follow-up queue</h2>
        <p>
          The watchlist is where the trial gets decision-useful: modest growers, the single stalled pot, and any seedling that needs a tighter future capture or in-person check.
        </p>
        <div class="chip-row" id="watchlist-chips"></div>
      </article>
    </section>

    <section class="variety-board">
      <div class="section-head">
        <div>
          <h2>Variety outlooks for Sausalito fog</h2>
          <p>
            These cards preserve the varietal read alongside the Phase 1 signal. The outlook is intentionally directional until later phases tell us who can really set and ripen.
          </p>
        </div>
      </div>
      <div class="variety-grid" id="variety-grid"></div>
    </section>

    <section class="toolbar-card">
      <div class="toolbar-top">
        <input
          id="search-input"
          class="search-input"
          type="search"
          placeholder="Search pot, variety, fog outlook, or assessment"
          aria-label="Search pots"
        />
        <div class="filter-row">
          <button class="filter-btn active" data-filter="all" type="button">All Pots</button>
          <button class="filter-btn" data-filter="strong_establishment" type="button">Strong</button>
          <button class="filter-btn" data-filter="watchlist" type="button">Watchlist</button>
          <button class="filter-btn" data-filter="stalled_or_failed" type="button">Stalled</button>
        </div>
      </div>
      <div class="toolbar-bottom">
        <span id="shown-count">Showing __TOTAL_POTS__ of __TOTAL_POTS__ pots</span>
        <span>Front of every card = __END_LABEL__. Flip the image to revisit __START_LABEL__.</span>
      </div>
    </section>

    <section class="gallery-shell">
      <div class="section-head">
        <div>
          <h2>Pot-by-pot comparisons</h2>
          <p>
            Each card starts on the last-day frame so the current seedling state is the primary visual. Flip the card to see where that pot started.
          </p>
        </div>
      </div>
      <div class="gallery" id="gallery"></div>
    </section>

    <section class="method-grid">
      <article class="method-card">
        <h2>What is reliable now</h2>
        <p>
          The manual Phase 1 triage is the canonical growth read for this page. It is strong enough for establishment buckets, watchlist selection,
          visible mold-risk cues, and picking reference pots for future modeling work.
        </p>
        <ul>
          <li>Reliable now: strong vs modest vs stalled establishment</li>
          <li>Reliable now: early variety signal and watchlist generation</li>
          <li>Not yet reliable: exact cross-run size or biomass scoring from raw pixels</li>
        </ul>
      </article>

      <article class="method-card">
        <h2>CV strategy for next phase</h2>
        <p>
          Because the camera angle and distance drift between the anchor captures, the next quantitative pass should align the pair first and only then measure plant material inside the target pot.
        </p>
        <ul>
          <li>Register image pairs first to absorb framing drift before any growth math.</li>
          <li>Keep the measurement inside the pot region so neighbor foliage does not fake growth.</li>
          <li>Track canopy coverage, spill, plant count, and chlorosis together instead of relying on a single score.</li>
        </ul>
      </article>

      <article class="method-card">
        <h2>Where a VLM helps</h2>
        <p>
          A vision-language model is useful here, but as a secondary layer. It should comment on legginess, empty pots, possible mold, or multi-stem competition after the numeric CV pipeline has done the measurement work.
        </p>
        <ul>
          <li>Good use: draft qualitative notes and anomaly QA</li>
          <li>Good use: compare the two images and describe visible progression</li>
          <li>Not the primary tool for: numeric growth scoring or area estimation</li>
        </ul>
        <p><a href="./v1-10-pot-cv-research.html">Open the deeper pot-CV research page</a></p>
      </article>
    </section>

    <p class="footer-note">Generated at __GENERATED_AT__</p>
  </div>

  <div class="lightbox" id="lightbox" hidden>
    <div class="lightbox-scrim" data-close-lightbox></div>
    <div class="lightbox-panel" role="dialog" aria-modal="true" aria-labelledby="lightbox-title">
      <button class="lightbox-close" id="lightbox-close" type="button">Close</button>
      <div class="lightbox-layout">
        <div class="comparison-grid">
          <figure class="comparison-card">
            <img id="lightbox-day-one-img" alt="" />
            <figcaption class="comparison-copy">
              <strong id="lightbox-day-one-heading"></strong>
              <span id="lightbox-day-one-subtitle"></span>
            </figcaption>
          </figure>
          <figure class="comparison-card">
            <img id="lightbox-last-day-img" alt="" />
            <figcaption class="comparison-copy">
              <strong id="lightbox-last-day-heading"></strong>
              <span id="lightbox-last-day-subtitle"></span>
            </figcaption>
          </figure>
        </div>

        <aside class="lightbox-copy">
          <p class="lightbox-kicker" id="lightbox-kicker"></p>
          <h2 class="lightbox-title" id="lightbox-title"></h2>
          <p class="lightbox-subtitle" id="lightbox-subtitle"></p>

          <div class="detail-block">
            <h3>Phase 1 assessment</h3>
            <p id="lightbox-assessment"></p>
            <div class="detail-stats">
              <div><dt>Bucket</dt><dd id="lightbox-bucket"></dd></div>
              <div><dt>Follow-up</dt><dd id="lightbox-priority"></dd></div>
            </div>
          </div>

          <div class="detail-block">
            <h3>Varietal outlook</h3>
            <p id="lightbox-expectation"></p>
            <div class="detail-stats">
              <div><dt>Type</dt><dd id="lightbox-type"></dd></div>
              <div><dt>Maturity</dt><dd id="lightbox-maturity"></dd></div>
              <div><dt>Fog outlook</dt><dd id="lightbox-fog"></dd></div>
              <div><dt>Phase signal</dt><dd id="lightbox-variety-signal"></dd></div>
            </div>
            <p id="lightbox-profile-note"></p>
          </div>

          <div class="detail-block">
            <h3>Growth analysis signal</h3>
            <p id="lightbox-cv-story"></p>
            <div class="detail-stats">
              <div><dt>CV readiness</dt><dd id="lightbox-cv-readiness"></dd></div>
              <div><dt>Focus</dt><dd id="lightbox-cv-focus"></dd></div>
              <div><dt>Coverage</dt><dd id="lightbox-cv-coverage"></dd></div>
              <div><dt>Neighbor spill</dt><dd id="lightbox-cv-neighbor"></dd></div>
              <div><dt>In-pot spill</dt><dd id="lightbox-cv-inpot"></dd></div>
              <div><dt>Growth delta</dt><dd id="lightbox-cv-growth"></dd></div>
            </div>
            <p id="lightbox-cv-next"></p>
          </div>
        </aside>
      </div>

      <div class="lightbox-footer">
        <button class="ghost-btn" id="lightbox-prev" type="button">Previous</button>
        <span class="lightbox-position" id="lightbox-position"></span>
        <button class="ghost-btn" id="lightbox-next" type="button">Next</button>
      </div>
    </div>
  </div>

  <script>
    const pageData = {
      pots: __POTS_JSON__,
      varieties: __VARIETIES_JSON__,
      stats: __STATS_JSON__,
      referencePots: __REFERENCE_JSON__,
      watchlistPots: __WATCHLIST_JSON__
    };

    const state = {
      filter: "all",
      query: "",
      flippedPotIds: new Set(),
      activePotId: null
    };

    const potMap = new Map(pageData.pots.map((pot) => [pot.pot_id, pot]));
    const searchInput = document.getElementById("search-input");
    const gallery = document.getElementById("gallery");
    const shownCount = document.getElementById("shown-count");
    const filterButtons = Array.from(document.querySelectorAll(".filter-btn"));
    const lightbox = document.getElementById("lightbox");
    const lightboxClose = document.getElementById("lightbox-close");
    const lightboxPrev = document.getElementById("lightbox-prev");
    const lightboxNext = document.getElementById("lightbox-next");

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function renderMiniChips(targetId, items, formatter) {
      const target = document.getElementById(targetId);
      target.innerHTML = items
        .map((item) => formatter(item))
        .join("");
    }

    function renderReferenceChips() {
      renderMiniChips("reference-chips", pageData.referencePots, (item) => (
        `<span class="mini-chip"><strong>${escapeHtml(item.pot_id)}</strong>${escapeHtml(item.variety_name)}</span>`
      ));
    }

    function renderWatchlistChips() {
      renderMiniChips("watchlist-chips", pageData.watchlistPots, (item) => (
        `<span class="mini-chip"><strong>${escapeHtml(item.pot_id)}</strong>${escapeHtml(item.bucket_label)}</span>`
      ));
    }

    function renderVarietyGrid() {
      const target = document.getElementById("variety-grid");
      target.innerHTML = pageData.varieties.map((item) => `
        <article class="variety-card">
          <p class="card-kicker">${escapeHtml(item.signal)}</p>
          <h3>${escapeHtml(item.variety_name)}</h3>
          <p>${escapeHtml(item.expectation)}</p>
          <div class="variety-meta">
            <div><dt>Fog outlook</dt><dd>${escapeHtml(item.fog_outlook)}</dd></div>
            <div><dt>Type</dt><dd>${escapeHtml(item.type_label)}</dd></div>
            <div><dt>Strong pots</dt><dd>${escapeHtml(item.strong_count)}</dd></div>
            <div><dt>Watchlist pots</dt><dd>${escapeHtml(item.watch_count)}</dd></div>
          </div>
        </article>
      `).join("");
    }

    function matchesFilter(pot) {
      if (state.filter === "all") {
        return true;
      }
      if (state.filter === "watchlist") {
        return Boolean(pot.is_watchlist);
      }
      return pot.bucket === state.filter;
    }

    function matchesQuery(pot) {
      if (!state.query) {
        return true;
      }
      return String(pot.search_blob || "").includes(state.query);
    }

    function getVisiblePots() {
      return pageData.pots.filter((pot) => matchesFilter(pot) && matchesQuery(pot));
    }

    function renderGallery() {
      const visible = getVisiblePots();
      shownCount.textContent = `Showing ${visible.length} of ${pageData.stats.total_pots} pots`;

      if (!visible.length) {
        gallery.innerHTML = "<div class='empty-state'>No pots match the current search and filter combination.</div>";
        return;
      }

      gallery.innerHTML = visible.map((pot) => {
        const isFlipped = state.flippedPotIds.has(pot.pot_id);
        const flipLabel = isFlipped ? `Flip back to ${pageData.stats.end_label}` : `Flip to ${pageData.stats.start_label}`;
        return `
          <article class="pot-card ${escapeHtml(pot.bucket_tone)}">
            <div class="card-header">
              <div>
                <p class="card-kicker">Pot ${escapeHtml(pot.pot_id)} · Varietal ${escapeHtml(pot.varietal_number)}</p>
                <h3>${escapeHtml(pot.variety_name)}</h3>
              </div>
              <span class="bucket-pill ${escapeHtml(pot.bucket_tone)}">${escapeHtml(pot.bucket_label)}</span>
            </div>

            <button class="photo-surface js-open-detail" type="button" data-pot-id="${escapeHtml(pot.pot_id)}">
              <div class="flip-shell">
                <div class="flip-stage ${isFlipped ? "is-flipped" : ""}">
                  <figure class="face front">
                    ${pot.last_day_photo_url ? `<img src="${escapeHtml(pot.last_day_photo_url)}" alt="${escapeHtml(`${pot.variety_name} ${pageData.stats.end_label}`)}" loading="lazy" />` : ""}
                    <div class="face-copy">
                      <div class="face-label">
                        <strong>${escapeHtml(pageData.stats.end_label)}</strong>
                        <span>${escapeHtml(pot.last_day_label)}</span>
                      </div>
                    </div>
                  </figure>
                  <figure class="face back">
                    ${pot.day_one_photo_url ? `<img src="${escapeHtml(pot.day_one_photo_url)}" alt="${escapeHtml(`${pot.variety_name} ${pageData.stats.start_label}`)}" loading="lazy" />` : ""}
                    <div class="face-copy">
                      <div class="face-label">
                        <strong>${escapeHtml(pageData.stats.start_label)}</strong>
                        <span>${escapeHtml(pot.day_one_label)}</span>
                      </div>
                    </div>
                  </figure>
                </div>
              </div>
              <span class="surface-hint">Open comparison</span>
            </button>

            <div class="card-actions">
              <button class="ghost-btn js-flip" type="button" data-pot-id="${escapeHtml(pot.pot_id)}">${escapeHtml(flipLabel)}</button>
              <button class="solid-btn js-open-detail" type="button" data-pot-id="${escapeHtml(pot.pot_id)}">Detailed view</button>
            </div>

            <p class="card-summary">${escapeHtml(pot.analysis_notes)}</p>

            <dl class="card-metrics">
              <div><dt>Fog outlook</dt><dd>${escapeHtml(pot.fog_outlook)}</dd></div>
              <div><dt>CV readiness</dt><dd>${escapeHtml(pot.cv_readiness_label)}</dd></div>
              <div><dt>Follow-up</dt><dd>${escapeHtml(pot.priority_label)}</dd></div>
            </dl>
          </article>
        `;
      }).join("");
    }

    function setFilter(nextFilter) {
      state.filter = nextFilter;
      filterButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.filter === nextFilter);
      });
      renderGallery();
    }

    function openLightbox(potId) {
      if (!potMap.has(potId)) {
        return;
      }
      state.activePotId = potId;
      renderLightbox();
      lightbox.hidden = false;
      document.body.classList.add("lightbox-open");
    }

    function closeLightbox() {
      lightbox.hidden = true;
      document.body.classList.remove("lightbox-open");
      state.activePotId = null;
    }

    function renderLightbox() {
      const pot = potMap.get(state.activePotId);
      if (!pot) {
        return;
      }
      const visible = getVisiblePots();
      const position = Math.max(visible.findIndex((item) => item.pot_id === pot.pot_id), 0);

      document.getElementById("lightbox-kicker").textContent = `Pot ${pot.pot_id} · Varietal ${pot.varietal_number}`;
      document.getElementById("lightbox-title").textContent = pot.variety_name;
      document.getElementById("lightbox-subtitle").textContent = `${pot.bucket_deck} ${pot.analysis_notes}`;

      const dayOneImg = document.getElementById("lightbox-day-one-img");
      dayOneImg.src = pot.day_one_photo_url || "";
      dayOneImg.alt = `${pot.variety_name} on ${pageData.stats.start_label}`;
      document.getElementById("lightbox-day-one-heading").textContent = pageData.stats.start_label;
      document.getElementById("lightbox-day-one-subtitle").textContent = `${pot.day_one_label} · OCR pot match: ${pot.day_one_ocr_confirms_pot}`;

      const lastDayImg = document.getElementById("lightbox-last-day-img");
      lastDayImg.src = pot.last_day_photo_url || "";
      lastDayImg.alt = `${pot.variety_name} on ${pageData.stats.end_label}`;
      document.getElementById("lightbox-last-day-heading").textContent = pageData.stats.end_label;
      document.getElementById("lightbox-last-day-subtitle").textContent = `${pot.last_day_label} · OCR pot match: ${pot.last_day_ocr_confirms_pot}`;

      document.getElementById("lightbox-assessment").textContent = pot.analysis_notes;
      document.getElementById("lightbox-bucket").textContent = pot.bucket_label;
      document.getElementById("lightbox-priority").textContent = pot.priority_label;

      document.getElementById("lightbox-expectation").textContent = pot.expectation;
      document.getElementById("lightbox-type").textContent = pot.type_label;
      document.getElementById("lightbox-maturity").textContent = pot.maturity_label;
      document.getElementById("lightbox-fog").textContent = pot.fog_outlook;
      document.getElementById("lightbox-variety-signal").textContent = pot.variety_phase_signal;
      document.getElementById("lightbox-profile-note").textContent = pot.profile_note;

      document.getElementById("lightbox-cv-story").textContent = pot.cv_story;
      document.getElementById("lightbox-cv-readiness").textContent = pot.cv_readiness_label;
      document.getElementById("lightbox-cv-focus").textContent = pot.cv_focus_pct;
      document.getElementById("lightbox-cv-coverage").textContent = pot.cv_coverage_pct;
      document.getElementById("lightbox-cv-neighbor").textContent = pot.cv_neighbor_spill_pct;
      document.getElementById("lightbox-cv-inpot").textContent = pot.cv_in_pot_spill_pct;
      document.getElementById("lightbox-cv-growth").textContent = `${pot.cv_growth_delta_pct} · ${pot.cv_growth_delta_deck}`;
      document.getElementById("lightbox-cv-next").textContent = pot.cv_next_step;

      document.getElementById("lightbox-position").textContent = `${position + 1} of ${visible.length}`;
    }

    function stepLightbox(delta) {
      const visible = getVisiblePots();
      if (!visible.length || !state.activePotId) {
        return;
      }
      const currentIndex = visible.findIndex((item) => item.pot_id === state.activePotId);
      const nextIndex = currentIndex === -1 ? 0 : (currentIndex + delta + visible.length) % visible.length;
      openLightbox(visible[nextIndex].pot_id);
    }

    searchInput.addEventListener("input", (event) => {
      state.query = String(event.target.value || "").trim().toLowerCase();
      renderGallery();
    });

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => setFilter(button.dataset.filter || "all"));
    });

    gallery.addEventListener("click", (event) => {
      const flipButton = event.target.closest(".js-flip");
      if (flipButton) {
        const potId = flipButton.dataset.potId;
        if (state.flippedPotIds.has(potId)) {
          state.flippedPotIds.delete(potId);
        } else {
          state.flippedPotIds.add(potId);
        }
        renderGallery();
        return;
      }

      const detailButton = event.target.closest(".js-open-detail");
      if (detailButton) {
        openLightbox(detailButton.dataset.potId || "");
      }
    });

    lightbox.addEventListener("click", (event) => {
      if (event.target.matches("[data-close-lightbox]")) {
        closeLightbox();
      }
    });

    lightboxClose.addEventListener("click", closeLightbox);
    lightboxPrev.addEventListener("click", () => stepLightbox(-1));
    lightboxNext.addEventListener("click", () => stepLightbox(1));

    document.addEventListener("keydown", (event) => {
      if (lightbox.hidden) {
        return;
      }
      if (event.key === "Escape") {
        closeLightbox();
      } else if (event.key === "ArrowLeft") {
        stepLightbox(-1);
      } else if (event.key === "ArrowRight") {
        stepLightbox(1);
      }
    });

    renderReferenceChips();
    renderWatchlistChips();
    renderVarietyGrid();
    renderGallery();
  </script>
</body>
</html>
"""

    return (
        template.replace("__POTS_JSON__", pots_json)
        .replace("__VARIETIES_JSON__", varieties_json)
        .replace("__STATS_JSON__", stats_json)
        .replace("__REFERENCE_JSON__", reference_json)
        .replace("__WATCHLIST_JSON__", watchlist_json)
        .replace("__TOTAL_POTS__", str(stats["total_pots"]))
        .replace("__UNIQUE_VARIETIES__", str(stats["unique_varieties"]))
        .replace("__STRONG_COUNT__", str(stats["strong_count"]))
        .replace("__WATCH_COUNT__", str(stats["watch_count"]))
        .replace("__STALLED_COUNT__", str(stats["stalled_count"]))
        .replace("__DAYS_BETWEEN__", str(stats["days_between"]))
        .replace("__INCLUSIVE_DAYS__", str(stats["inclusive_days"]))
        .replace("__GROWTH_DELTA_COUNT__", str(stats["growth_delta_count"]))
        .replace("__START_LABEL__", str(stats["start_label"]))
        .replace("__START_DATE_LABEL__", str(stats["start_date_label"]))
        .replace("__END_LABEL__", str(stats["end_label"]))
        .replace("__END_DATE_LABEL__", str(stats["end_date_label"]))
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the Phase 1 landing page for Tomato Trails."
    )
    parser.add_argument(
        "--triage-csv",
        type=Path,
        default=Path("data/research/phase1_day1_vs_lastday_manual_triage.csv"),
        help="Canonical Phase 1 pair triage CSV.",
    )
    parser.add_argument(
        "--cv-metrics-csv",
        type=Path,
        default=Path("data/research/v1_10/pot_cv_metrics.csv"),
        help="Pot-level CV metrics used for growth-analysis guidance.",
    )
    parser.add_argument(
        "--phase-timeline-csv",
        type=Path,
        default=Path("data/intake/google_photos/manual_phase_timeline.csv"),
        help="Phase timeline CSV for anchor labels and dates.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("tracker/tomato-trails-view.html"),
        help="Output HTML file.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    triage_rows = read_rows(args.triage_csv)
    metrics_by_pot = load_cv_metrics(args.cv_metrics_csv)
    phase_window = load_phase_window(args.phase_timeline_csv)
    pot_records = build_pot_records(triage_rows, metrics_by_pot)
    variety_cards = build_variety_cards(pot_records)
    stats = build_page_stats(pot_records, metrics_by_pot, phase_window)
    reference_pots = build_reference_pots(pot_records)
    watchlist_pots = build_watchlist_pots(pot_records)
    page = build_page(pot_records, variety_cards, stats, reference_pots, watchlist_pots)
    page = stabilize_rendered_text(args.output_html, page)
    write_text_if_changed(args.output_html, page)

    print(f"triage_csv={args.triage_csv}")
    print(f"triage_rows={len(triage_rows)}")
    print(f"cv_metrics_rows={len(metrics_by_pot)}")
    print(f"output_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
