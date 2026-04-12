# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CommuteCast Seattle is an early-stage data science / ML project for **Seattle public transit reliability prediction**. The core goal is not to show schedules or live arrivals, but to estimate **confidence / risk around ETAs** — e.g., "32% chance you arrive after 8:30."

**Current status:** Snapshot collection phase. Static GTFS and real-time feeds are validated. A snapshot collector is running locally and via GitHub Actions to accumulate training data. No modeling dataset or ML model exists yet.

## Running Scripts

```bash
# Install dependencies (use uv for speed)
uv venv --python 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt

# Validate data sources (re-downloads GTFS zip + real-time feeds)
python scripts/check_data_sources.py

# Collect one real-time snapshot (appends to data/snapshots/YYYY-MM-DD.csv)
python scripts/collect_snapshot.py

# Run the local loop collector (default: every 5 min, Ctrl+C to stop)
python scripts/run_collector.py
python scripts/run_collector.py --interval 2  # every 2 minutes
```

## Data Sources

**Static GTFS** (`data/raw/google_transit.zip`) — the fixed schedule, downloaded from King County Metro:
- `routes.txt` — every bus route
- `stops.txt` — every stop with GPS coordinates
- `trips.txt` — every individual run of every route; `trip_id` is the primary join key
- `stop_times.txt` — scheduled arrival/departure at every stop for every trip
- `calendar.txt` — maps `service_id` to days of the week (weekday/weekend patterns)
- Source: `https://metro.kingcounty.gov/gtfs/google_transit.zip`
- Re-download when King County Metro updates schedules (every few weeks)

**Real-time GTFS-RT** (live operations layer) — JSON from S3:
- Trip updates: `tripupdates_pb.json` — per-stop delay in seconds for active trips
- Vehicle positions: `vehiclepositions_pb.json`
- Service alerts: `alerts_pb.json`
- Base URL: `https://s3.amazonaws.com/kcm-alerts-realtime-prod/`

> Note: Older endpoint names like `trip-updates.json` return 403. Use the `_pb.json` variants.

**Snapshot data** (`data/snapshots/YYYY-MM-DD.csv`) — flattened real-time rows collected over time:
- Columns: `collected_at, feed_timestamp, trip_id, route_id, direction_id, stop_id, stop_sequence, arrival_delay`
- `arrival_delay` is in seconds (negative = early, positive = late)
- These files are committed to the repo and are the source for the future training dataset

## Architecture

### `scripts/check_data_sources.py`
One-time source validation. Downloads the GTFS zip, reads core tables into pandas, downloads the three real-time JSON feeds, and inspects their structure. Saves sample CSVs to `data/raw/`.

### `scripts/collect_snapshot.py`
Single-fetch snapshot collector. Fetches `tripupdates_pb.json`, flattens all `stop_time_update` entries into rows, and appends to `data/snapshots/YYYY-MM-DD.csv`. Skips rows with no `arrival_delay`. Called by both the local loop and GitHub Actions.

### `scripts/run_collector.py`
Local loop runner. Calls `collect_snapshot.main()` every N minutes until Ctrl+C.

### `.github/workflows/collect_snapshots.yml`
GitHub Actions workflow that runs every 15 minutes, calls `collect_snapshot.py`, and commits new rows back to the repo. Uses `git pull --rebase` before push to handle concurrent local/remote commits. No secrets required — the data source is a public S3 URL.

### `notebooks/01_schema_exploration.ipynb`
Schema exploration notebook. Inspects columns in all GTFS tables, validates `trip_id` join between static and real-time data (confirmed 100% match rate), checks `arrival_delay` null rate (1.9%), and confirms `arrival_time` format (`HH:MM:SS` strings).

HTTP requests use a retry adapter (5 retries, exponential backoff) and a custom `User-Agent` header. This pattern lives in `build_session()` inside each script.

## Key Schema Facts (confirmed)

- `trip_id` match rate between static GTFS and real-time feed: **100%**
- `arrival_delay` null rate: **1.9%** (signal is strong)
- `arrival_time` in `stop_times.txt`: `HH:MM:SS` strings (some past-midnight trips use `25:xx:xx`)
- `calendar.txt` maps `service_id` → weekday boolean columns

## Roadmap

1. ~~Schema exploration~~ — done (`notebooks/01_schema_exploration.ipynb`)
2. ~~Snapshot collector~~ — done (local + GitHub Actions)
3. Build merged modeling table — join `data/snapshots/` with `stop_times.txt` on `trip_id` + `stop_id`
4. Add features: hour of day, day of week, route, direction, stop sequence position
5. Define binary label: `is_late = arrival_delay > 300` (5 min)
6. Train a binary late-arrival classifier
