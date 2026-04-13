# CommuteCast Seattle

*By Aaditya Parthasarathy*

A Seattle public transit reliability prediction project. The goal is to estimate **risk around ETAs**, not just show schedules — e.g., "Expected arrival 8:27, but 32% chance you arrive after 8:30."

## What it does

Normal transit apps give you an ETA. This project estimates the **probability you'll be late** by combining King County Metro's fixed schedule (GTFS) with historical real-time delay data (GTFS-RT).

The first ML target: binary classification — will this bus arrival be more than 5 minutes late?

## Project Status

- [x] Data source validation (static GTFS + real-time feeds)
- [x] Schema exploration — confirmed 100% `trip_id` join rate between static and real-time data
- [x] Snapshot collector — running locally and via GitHub Actions every 15 min
- [ ] Build merged training dataset
- [ ] Train binary late-arrival classifier

## Data

**Static schedule** — `google_transit.zip` from King County Metro  
**Live delays** — GTFS-RT trip updates feed (King County Metro S3)  
**Snapshot history** — `data/snapshots/YYYY-MM-DD.csv`, collected continuously

Each snapshot row: `trip_id, route_id, direction_id, stop_id, stop_sequence, arrival_delay (seconds)`

## Setup

```bash
uv venv --python 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt
```

## Running

```bash
# Collect one snapshot
python scripts/collect_snapshot.py

# Run local loop collector (every 5 min by default)
python scripts/run_collector.py

# Re-validate data sources
python scripts/check_data_sources.py
```

## Automated Collection

A GitHub Actions workflow (`.github/workflows/collect_snapshots.yml`) collects a snapshot every 15 minutes and commits the rows to `data/snapshots/` automatically — no server required.
