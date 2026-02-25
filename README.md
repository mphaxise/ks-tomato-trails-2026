# 🍅 Fog Tomato Trials

**A citizen science project tracking which tomato varieties thrive in Sausalito's coastal fog belt.**

Sausalito sits in one of the Bay Area's most challenging microclimates for tomatoes — persistent summer fog, cool temperatures, and high humidity create conditions that most tomato varieties struggle with. This project systematically tests 12 varieties head-to-head to find the ones that actually produce.

---

## What This Is

A structured observation system for a backyard grower in Sausalito to:
- Track growth, health, and fruit production across 12 tomato varieties
- Identify which varieties succeed in low-heat, high-fog conditions
- Build a reusable data set future growers in similar microclimates can learn from

## Repository Structure

```
fog-tomato-trials/
├── README.md               ← You are here
├── docs/
│   ├── STRATEGY.md         ← Overall project approach and goals
│   ├── VARIETIES.md        ← The 12 varieties being tested + fog-belt suitability profiles
│   ├── DATA_SCHEMA.md      ← What to measure, how often, and why
│   ├── CLIMATE_RESEARCH.md ← Fog-belt tomato science (why fog is hard, what helps)
│   └── SUCCESS_METRICS.md  ← How we define "winner" at season's end
├── data/
│   ├── varieties.json      ← Machine-readable variety registry
│   └── observations/       ← Weekly observation logs (CSV per variety)
├── logs/
│   └── README.md           ← Field notes and freeform observations
└── tracker/
    └── README.md           ← Future app: web-based logging interface
```

## Season Overview

| Parameter | Value |
|---|---|
| Location | Sausalito, CA (fog belt) |
| Varieties | 12 (see VARIETIES.md) |
| Season start | Spring 2026 (transplant after last frost) |
| Data collection | Weekly, May–October |
| Primary goal | Identify top 3 fog-belt performers |

## Quick Start

1. Read `docs/STRATEGY.md` for the overall plan
2. Register your 12 varieties in `data/varieties.json`
3. Start weekly logs in `data/observations/`
4. End-of-season scoring in `docs/SUCCESS_METRICS.md`

---

*Built with 🌫️ for growers where the fog never really lifts.*
