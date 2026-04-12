# Datasets Reference

This document describes every data source in the project — what it is, where it comes from, how it is collected, its schema, and which columns matter for modeling.

---

## 1. Static GTFS — `data/raw/google_transit.zip`

**What it is:** The official King County Metro transit schedule. A zip archive containing plain-text CSV files that describe the entire fixed schedule — every route, stop, trip, and timetable.

**Collection type:** One-time download, refresh every few weeks when Metro updates their schedules.

**Source URL:** `https://metro.kingcounty.gov/gtfs/google_transit.zip`

**How to re-download:** Run `python scripts/check_data_sources.py`

**Why it matters:** This is the "what should happen" baseline. Every real-time delay is measured against this schedule. Without it, you have no reference point for whether a bus is early or late.

> The zip is excluded from git (16.8MB). Re-download it locally when needed.

---

### 1a. `routes.txt`

A lookup table of every transit route in the system.

| Column | Type | Description |
|---|---|---|
| `route_id` | string | Unique route identifier (e.g. `100001`) — **primary key**, joins to `trips.txt` |
| `route_short_name` | string | The number/letter on the bus (e.g. `44`, `E Line`) |
| `route_long_name` | string | Human-readable description (e.g. "Ballard - Montlake") |
| `route_type` | int | Mode: `0` = streetcar, `3` = bus, `4` = ferry |
| `agency_id` | string | Operator: `1` = King County Metro, `40` = Sound Transit, `23` = Seattle Streetcar |

**Rows:** ~130 routes  
**Useful for modeling:** `route_id` (join key), `route_short_name` (human label)

---

### 1b. `stops.txt`

Every physical bus stop in the system.

| Column | Type | Description |
|---|---|---|
| `stop_id` | string | Unique stop identifier (e.g. `2010`) — **primary key**, joins to `stop_times.txt` and real-time feed |
| `stop_name` | string | Human-readable name (e.g. "1st Ave & Spring St") |
| `stop_lat` | float | GPS latitude |
| `stop_lon` | float | GPS longitude |
| `wheelchair_boarding` | int | `1` = accessible, `0` = not |

**Rows:** ~10,000+ stops  
**Useful for modeling:** `stop_id` (join key), `stop_lat`/`stop_lon` (optional spatial features)

---

### 1c. `trips.txt`

Each row is one specific run of a route. A route runs many times per day — each of those runs is a separate trip.

| Column | Type | Description |
|---|---|---|
| `trip_id` | string | Unique trip identifier — **the most important join key in the project**. Connects static schedule to real-time feed. |
| `route_id` | string | Which route this trip belongs to — joins to `routes.txt` |
| `service_id` | string | Links to `calendar.txt` to determine which days this trip runs |
| `direction_id` | int | `0` = outbound, `1` = inbound |
| `shape_id` | string | Links to the geographic path of the trip (not used for modeling) |

**Rows:** Tens of thousands of trips  
**Useful for modeling:** `trip_id` (join key), `route_id`, `direction_id`, `service_id`

---

### 1d. `stop_times.txt`

The most data-dense table. Each row is one stop on one trip — the scheduled arrival/departure for that trip at that stop.

| Column | Type | Description |
|---|---|---|
| `trip_id` | string | Which trip — joins to `trips.txt` and real-time feed |
| `stop_id` | string | Which stop — joins to `stops.txt` and real-time feed |
| `stop_sequence` | int | Order of this stop within the trip (1 = first stop) |
| `arrival_time` | string | Scheduled arrival as `HH:MM:SS`. Trips past midnight use values like `25:10:00` |
| `departure_time` | string | Scheduled departure as `HH:MM:SS` |

**Rows:** Millions of stop events  
**Useful for modeling:** `trip_id` + `stop_id` (composite join key), `arrival_time` (scheduled baseline), `stop_sequence` (proxy for how far into a trip the bus is)

> **Note on time format:** `arrival_time` is a string, not a Python datetime. Values ≥ `24:00:00` represent service that runs past midnight (e.g., a trip starting at 11:45pm with stops at `25:10:00` = 1:10am next day). Parse carefully.

---

### 1e. `calendar.txt`

Maps each `service_id` to the days of the week it operates, and its valid date range.

| Column | Type | Description |
|---|---|---|
| `service_id` | string | Joins to `trips.txt` |
| `monday` | int | `1` = runs on Mondays, `0` = does not |
| `tuesday` | int | Same pattern |
| `wednesday` | int | Same pattern |
| `thursday` | int | Same pattern |
| `friday` | int | Same pattern |
| `saturday` | int | Same pattern |
| `sunday` | int | Same pattern |
| `start_date` | string | First date this service is valid (`YYYYMMDD`) |
| `end_date` | string | Last date this service is valid (`YYYYMMDD`) |

**Useful for modeling:** Join `trips → calendar` via `service_id` to extract `day_of_week` as a feature. Monday morning rush hour behaves very differently from Saturday afternoon.

---

## 2. Real-time GTFS-RT Feeds — `data/raw/`

**What they are:** Live snapshots of current transit operations, published by King County Metro to a public S3 bucket. Updated roughly every 30 seconds by the agency.

**Collection type:** Point-in-time snapshots. The files in `data/raw/` are single captures from the initial project setup. For training data, use the accumulated snapshots in `data/snapshots/` instead.

**Base URL:** `https://s3.amazonaws.com/kcm-alerts-realtime-prod/`

> **Important:** Older endpoint names (`trip-updates.json`, `vehicle-positions.json`) return 403. Always use the `_pb.json` suffix variants.

---

### 2a. `realtime_trip_updates.json` → `tripupdates_pb.json`

**The most important real-time feed.** Contains live delay predictions for every active trip, broken down by stop.

**Top-level structure:**
```json
{
  "header": {
    "gtfs_realtime_version": "2.0",
    "timestamp": 1774224407      ← Unix timestamp of this snapshot
  },
  "entity": [ ... ]              ← one entry per active trip
}
```

**Per-entity structure:**
```json
{
  "id": "1774224407_727453249",
  "trip_update": {
    "trip": {
      "trip_id": "727453249",    ← joins to trips.txt
      "route_id": "100001",      ← joins to routes.txt
      "direction_id": 1,
      "start_date": "20260322",
      "schedule_relationship": "SCHEDULED"
    },
    "stop_time_update": [
      {
        "stop_sequence": 1,
        "stop_id": "2010",       ← joins to stops.txt
        "arrival": {
          "delay": -667,         ← seconds early (negative) or late (positive)
          "time": 1774223933     ← predicted arrival as Unix timestamp
        },
        "departure": { ... }
      }
    ]
  }
}
```

**Key fields:**
| Field | Description |
|---|---|
| `header.timestamp` | When this snapshot was generated (Unix seconds) |
| `trip_update.trip.trip_id` | **Join key to static GTFS** — confirmed 100% match rate |
| `trip_update.trip.route_id` | Route identifier |
| `trip_update.trip.direction_id` | 0 = outbound, 1 = inbound |
| `stop_time_update[].stop_id` | Stop identifier — joins to `stops.txt` |
| `stop_time_update[].stop_sequence` | Order of stop within trip |
| `stop_time_update[].arrival.delay` | **The core signal.** Seconds late (positive) or early (negative). Null rate: ~1.9% |

---

### 2b. `realtime_vehicle_positions.json` → `vehiclepositions_pb.json`

GPS positions of all active vehicles, updated in near-real-time.

**Per-entity structure:**
```json
{
  "vehicle": {
    "trip": {
      "trip_id": "727453249",
      "route_id": "100001",
      "direction_id": 1
    },
    "vehicle": { "id": "7104", "label": "7104" },
    "position": {
      "latitude": 47.6452,
      "longitude": -122.370148
    },
    "current_stop_sequence": 2,
    "stop_id": "2020",
    "current_status": "STOPPED_AT",   ← or "IN_TRANSIT_TO"
    "timestamp": 1774224396
  }
}
```

**Useful for modeling (future):** Vehicle position relative to next stop could serve as a real-time feature at inference time. Not needed for the initial training dataset.

---

### 2c. `realtime_alerts.json` → `alerts_pb.json`

Active service disruptions — detours, cancellations, delays caused by incidents.

Not used in the initial model. Could be incorporated later as a binary feature (e.g., "is there an active alert on this route?").

---

## 3. Snapshot Collection — `data/snapshots/`

**What it is:** The accumulated training data. Each file is one day's worth of flattened real-time trip update rows, collected every 5 minutes locally and every 15 minutes via GitHub Actions.

**Collection type:** Continuous, ongoing. Files grow daily and are committed to the repo automatically.

**File naming:** `YYYY-MM-DD.csv` (one file per calendar day, UTC)

**Schema:**

| Column | Type | Description |
|---|---|---|
| `collected_at` | string | ISO 8601 UTC timestamp of when this snapshot was fetched (e.g. `2026-04-12T23:36:17+00:00`) |
| `feed_timestamp` | int | Unix timestamp from the feed header — when Metro generated the snapshot |
| `trip_id` | string | Joins to `trips.txt` — 100% match rate confirmed |
| `route_id` | string | Joins to `routes.txt` |
| `direction_id` | int | `0` = outbound, `1` = inbound |
| `stop_id` | string | Joins to `stops.txt` and `stop_times.txt` |
| `stop_sequence` | int | Position of this stop within the trip |
| `arrival_delay` | int | **Seconds late (positive) or early (negative).** This is the raw signal the model is built on. |

**Rows per snapshot:** ~23,000–25,000 (varies by time of day and day of week)

**How to use for training:**
1. Load all daily CSVs and concatenate
2. Join on `trip_id` + `stop_id` to `stop_times.txt` to get `scheduled_arrival_time`
3. Join on `trip_id` to `trips.txt` to get `service_id`, then to `calendar.txt` for day-of-week
4. Derive label: `is_late = arrival_delay > 300`

---

## Join Map

```
routes.txt ──(route_id)──────────────> trips.txt
                                           │
                              (service_id) │ (trip_id)
                                           │
                                    calendar.txt    stop_times.txt ──(stop_id)──> stops.txt
                                                          │
                                                      (trip_id + stop_id)
                                                          │
                                              data/snapshots/YYYY-MM-DD.csv
                                              (arrival_delay = training signal)
```
