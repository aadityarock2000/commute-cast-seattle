# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Project Is

CommuteCast Seattle is a Seattle public transit reliability ML project. The core idea is **not** to show schedules or ETAs — it is to estimate **risk and confidence around ETAs**.

Example of what it does:
> Normal transit apps say: "Your bus arrives at 8:27."
> This project says: "Expected arrival 8:27, but 32% chance you arrive after 8:30."

It is a **decision-support tool for commuters under uncertainty** — helping people decide which transit option to take based on reliability, not just schedule.

**Current status:** Data collection phase. GitHub Actions is collecting real-time snapshots every 5 minutes and committing them to `data/snapshots/`. No training dataset or ML model has been built yet.

---

## ML Framing

- **Problem type:** Binary classification
- **Prediction target:** Will this bus arrival be more than 5 minutes late?
  - `1` = `arrival_delay > 300` seconds (late)
  - `0` = otherwise (on time or early)
- **Unit of prediction:** One stop event (a specific trip arriving at a specific stop)
- **Future extensions:** regression for exact delay minutes, transfer miss prediction, buffer time recommendation

---

## Environment Setup

Uses `uv` as the package manager (faster than pip). Python 3.11.

```bash
uv venv --python 3.11
.venv\Scripts\activate        # Windows
uv pip install -r requirements.txt
```

> `uv venv` on this machine picks up Anaconda's Python by default unless `--python 3.11` is specified explicitly. Always use `--python 3.11` to get a clean environment.

---

## Running Scripts

```bash
# Re-validate data sources (re-downloads GTFS zip + raw real-time JSON snapshots)
python scripts/check_data_sources.py

# Collect one real-time snapshot now (appends rows to data/snapshots/YYYY-MM-DD.csv)
python scripts/collect_snapshot.py

# Local loop collector (not needed — GitHub Actions handles continuous collection)
python scripts/run_collector.py
python scripts/run_collector.py --interval 2
```

---

## Data Collection Strategy

**GitHub Actions is the primary collector.** The workflow `.github/workflows/collect_snapshots.yml` runs every 5 minutes (GitHub's minimum interval), fetches the real-time trip updates feed, and commits flattened rows to `data/snapshots/`. No local machine needs to stay on.

- ~288 snapshots/day × ~23,000 rows/snapshot ≈ **6.6 million rows/day**
- After 1 week: ~46 million rows — enough to train a first model
- All snapshot CSVs are committed to the repo and available via `git pull`

**Future plan (post first model):** Move to a cloud VM (e.g., DigitalOcean $5/month or Oracle Cloud free tier) running the collector every 3 minutes, storing to a database (SQLite or Postgres). GitHub Actions is a temporary solution for bootstrapping.

---

## Data Sources

### Static GTFS — `data/raw/google_transit.zip`
The official King County Metro schedule. One-time download, refresh every few weeks when Metro updates schedules.

**Source:** `https://metro.kingcounty.gov/gtfs/google_transit.zip`  
**Re-download:** `python scripts/check_data_sources.py`  
**Excluded from git** (16.8MB — too large for GitHub)

Key tables and their roles:

| File | Role | Key columns |
|---|---|---|
| `routes.txt` | Route directory | `route_id` (PK), `route_short_name` |
| `stops.txt` | Physical stop locations | `stop_id` (PK), `stop_lat`, `stop_lon` |
| `trips.txt` | One row per bus run | `trip_id` (PK, **main join key**), `route_id`, `service_id`, `direction_id` |
| `stop_times.txt` | Scheduled arrivals | `trip_id` + `stop_id` (composite key), `arrival_time`, `stop_sequence` |
| `calendar.txt` | Service patterns | `service_id`, weekday boolean columns |

`trip_id` is the single most important column — it is the join key between static schedule data and the real-time feed. **Confirmed 100% match rate.**

### Real-time GTFS-RT — King County Metro S3
Live operations data. Base URL: `https://s3.amazonaws.com/kcm-alerts-realtime-prod/`

> **Always use `_pb.json` suffix.** Old names (`trip-updates.json`, etc.) return 403.

| Feed | Filename | Used for |
|---|---|---|
| Trip updates | `tripupdates_pb.json` | **Primary feed.** Per-stop delay in seconds for every active trip |
| Vehicle positions | `vehiclepositions_pb.json` | GPS position of each active bus (future feature) |
| Service alerts | `alerts_pb.json` | Disruptions, detours (future feature) |

### Snapshot Data — `data/snapshots/YYYY-MM-DD.csv`
The accumulated training data. One CSV per calendar day (UTC). Committed to the repo by GitHub Actions automatically.

**Schema:**

| Column | Type | Description |
|---|---|---|
| `collected_at` | string | ISO 8601 UTC timestamp of fetch |
| `feed_timestamp` | int | Unix timestamp from feed header |
| `trip_id` | string | Joins to `trips.txt` |
| `route_id` | string | Joins to `routes.txt` |
| `direction_id` | int | `0` = outbound, `1` = inbound |
| `stop_id` | string | Joins to `stops.txt` and `stop_times.txt` |
| `stop_sequence` | int | Position of stop within the trip |
| `arrival_delay` | int | **Seconds late (+) or early (-). The core training signal.** |

Rows with no `arrival_delay` are skipped at collection time (~1.9% of raw entities).

---

## Codebase Architecture

### `scripts/check_data_sources.py`
One-time source validation script. Downloads GTFS zip, loads `routes`, `stops`, `trips`, `stop_times` into pandas, downloads the three real-time JSON feeds, and inspects structure. Saves sample CSVs to `data/raw/`.

### `scripts/collect_snapshot.py`
Single-fetch snapshot collector. Used by both the local runner and GitHub Actions.
- Fetches `tripupdates_pb.json` using a retry-enabled session
- Flattens `entity → trip_update → stop_time_update` into rows
- Appends to `data/snapshots/YYYY-MM-DD.csv` (creates file + header if new)
- Exits cleanly on fetch failure so GitHub Actions job still succeeds

### `scripts/run_collector.py`
Local loop wrapper. Calls `collect_snapshot.main()` every N minutes. Not needed now that GitHub Actions is the collector, but kept for local testing or future use.

### `.github/workflows/collect_snapshots.yml`
GitHub Actions workflow. Runs every 5 minutes on a cron schedule. Calls `collect_snapshot.py` then commits new rows with `git pull --rebase` before push to handle any concurrent commits. Requires `permissions: contents: write`. No secrets needed — the feed is a public URL.

### `notebooks/01_schema_exploration.ipynb`
Schema exploration notebook. Run this when returning to the project to re-familiarize with the data. Confirms join keys, inspects columns, checks delay statistics, validates `trip_id` match rate.

### `docs/datasets.md`
Detailed reference for every dataset — full schemas, collection type, JSON structures, join map. Read this before building the training dataset.

**HTTP pattern used across all scripts:** `build_session()` creates a `requests.Session` with a `Retry` adapter (5 retries, 1.5x exponential backoff, retries on 429/500/502/503/504) and a custom `User-Agent` header. Always use this pattern for fetching feeds — do not use bare `requests.get()`.

---

## Confirmed Schema Facts

These were validated by running `notebooks/01_schema_exploration.ipynb`:

- `trip_id` match rate (static ↔ real-time): **100%** — safe to join directly
- `arrival_delay` null rate: **1.9%** — signal is strong, nulls are skipped at collection
- `arrival_time` format in `stop_times.txt`: `HH:MM:SS` strings — **not** Python datetimes
- Past-midnight trips use values like `25:10:00` — parse carefully when converting to timestamps
- `calendar.txt` exists and maps `service_id` → weekday boolean columns (monday, tuesday, etc.)

---

## Join Map

```
routes.txt ──(route_id)──> trips.txt ──(service_id)──> calendar.txt
                               │
                           (trip_id)
                               │
                        stop_times.txt ──(stop_id)──> stops.txt
                               │
                      (trip_id + stop_id)
                               │
                   data/snapshots/YYYY-MM-DD.csv
                   (arrival_delay = training signal)
```

---

## Next Steps

1. ~~Schema exploration~~ — done (`notebooks/01_schema_exploration.ipynb`)
2. ~~Snapshot collector~~ — done (GitHub Actions, every 5 min)
3. **Build merged modeling table** — load snapshot CSVs, join with `stop_times.txt` on `trip_id` + `stop_id`, join with `trips.txt` + `calendar.txt` for day-of-week features
4. **Add features** — hour of day, day of week, route, direction, stop sequence position
5. **Define label** — `is_late = arrival_delay > 300`
6. **Train first model** — binary classifier (logistic regression or gradient boosted tree as baseline)
7. **Cloud upgrade** — move continuous collection to a cloud VM at 3-min intervals with a database backend
