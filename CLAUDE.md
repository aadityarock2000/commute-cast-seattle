# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CommuteCast Seattle is an early-stage data science / ML project for **Seattle public transit reliability prediction**. The core goal is not to show schedules or live arrivals, but to estimate **confidence / risk around ETAs** — e.g., "32% chance you arrive after 8:30."

**Current status:** Data ingestion and source validation phase. Static GTFS and real-time feeds have been successfully accessed. No modeling dataset or ML model exists yet.

## Running Scripts

```bash
# Install dependencies
pip install -r requirements.txt

# Run the data source validation script
python scripts/check_data_sources.py
```

## Data Sources

**Static GTFS** (schedule layer) — downloaded from King County Metro:
- `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`
- Source: `https://metro.kingcounty.gov/gtfs/google_transit.zip`

**Real-time GTFS-RT** (live operations layer) — JSON from S3:
- Trip updates: `tripupdates_pb.json`
- Vehicle positions: `vehiclepositions_pb.json`
- Service alerts: `alerts_pb.json`
- Base URL: `https://s3.amazonaws.com/kcm-alerts-realtime-prod/`

> Note: Older endpoint names like `trip-updates.json` return 403. Use the `_pb.json` variants.

Raw data is saved under `data/raw/`.

## Architecture

The single script `scripts/check_data_sources.py` does the following in sequence:
1. Downloads the GTFS static zip and reads `routes`, `stops`, `trips`, `stop_times` into pandas
2. Saves sample CSVs to `data/raw/`
3. Downloads the three real-time JSON feeds using a retry-enabled `requests.Session`
4. Inspects top-level structure of each real-time payload (entity count, first entity preview)

HTTP requests use a retry adapter (5 retries, exponential backoff) and a custom `User-Agent` header.

## What Comes Next

The project roadmap (not yet built):
1. Schema exploration notebook — inspect columns, identify join keys between static `trip_id`/`stop_id` and real-time entities
2. Narrow scope to one or a few routes/corridors
3. Define the prediction unit (trip event or stop event) and binary label (late > 5 min?)
4. Build a merged modeling table: scheduled info + real-time delay + timestamps
5. Collect repeated real-time snapshots over time for historical training data
6. Train a binary late-arrival classifier
