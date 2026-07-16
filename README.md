# spread-vs-growth

This repository supports figures, animations, and longer-running analyses for a talk comparing wildfire spread rate and growth rate.

The working question is:

> When are wildfire dynamics better understood as spread, and when are they better understood as growth?

The current talk storyboard is **ESA 2026 Fire Metabolism**, a 12-slide sequence that starts from the spread-vs-growth distinction and builds toward a metabolic view of extreme wildfire.

## Repository Layout

```text
docs/                 MkDocs website and project notes
src/spread_vs_growth/ Shared Python helpers for scripts and notebooks
scripts/              Reproducible figure and animation entry points
notebooks/            Exploratory work and draft figure development
data/                 Local data workspace; large contents are ignored
outputs/              Rendered figures, frames, and animations; ignored by git
tmp/                  Temporary renders and inspection artifacts; ignored by git
AGENTS.md             Agent instructions for working in this repository
PROMPT_LOG.md         Prompt-to-change history for substantive agent work
```

Large data files, animation frames, and rendered outputs should stay out of git unless they are intentionally curated for the website under `docs/assets/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Preview The Website

```bash
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

The published site is configured for:

```text
https://cu-esiil.github.io/spread-vs-growth/
```
