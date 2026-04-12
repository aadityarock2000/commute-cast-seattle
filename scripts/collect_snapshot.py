"""
Fetches one real-time GTFS-RT trip-updates snapshot from King County Metro
and appends the flattened stop-time rows to a daily CSV in data/snapshots/.

Usage:
    python scripts/collect_snapshot.py

Called by:
    - scripts/run_collector.py  (local loop)
    - .github/workflows/collect_snapshots.yml  (GitHub Actions every 15 min)
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TRIP_UPDATES_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates_pb.json"

SNAPSHOTS_DIR = Path(__file__).parent.parent / "data" / "snapshots"

CSV_COLUMNS = [
    "collected_at",
    "feed_timestamp",
    "trip_id",
    "route_id",
    "direction_id",
    "stop_id",
    "stop_sequence",
    "arrival_delay",
]


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CommuteCast/0.1"
    })
    return session


def fetch_trip_updates(session: requests.Session) -> dict | None:
    try:
        r = session.get(TRIP_UPDATES_URL, timeout=(10, 60))
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"WARNING: failed to fetch trip updates: {e}", file=sys.stderr)
        return None


def flatten_entities(payload: dict, collected_at: str) -> list[dict]:
    feed_timestamp = payload.get("header", {}).get("timestamp", "")
    rows = []
    for entity in payload.get("entity", []):
        tu = entity.get("trip_update", {})
        trip = tu.get("trip", {})
        trip_id    = trip.get("trip_id", "")
        route_id   = trip.get("route_id", "")
        direction  = trip.get("direction_id", "")
        for stu in tu.get("stop_time_update", []):
            arrival = stu.get("arrival") or {}
            delay = arrival.get("delay")
            if delay is None:
                continue  # skip stops with no delay signal
            rows.append({
                "collected_at":   collected_at,
                "feed_timestamp": feed_timestamp,
                "trip_id":        trip_id,
                "route_id":       route_id,
                "direction_id":   direction,
                "stop_id":        stu.get("stop_id", ""),
                "stop_sequence":  stu.get("stop_sequence", ""),
                "arrival_delay":  delay,
            })
    return rows


def append_to_csv(rows: list[dict], date_str: str) -> Path:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SNAPSHOTS_DIR / f"{date_str}.csv"
    write_header = not out_path.exists() or out_path.stat().st_size == 0
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    return out_path


def main() -> None:
    now_utc = datetime.now(timezone.utc)
    collected_at = now_utc.isoformat(timespec="seconds")
    date_str = now_utc.strftime("%Y-%m-%d")

    session = build_session()
    payload = fetch_trip_updates(session)
    if payload is None:
        print(f"[{collected_at}] Skipped — fetch failed.")
        return

    rows = flatten_entities(payload, collected_at)
    if not rows:
        print(f"[{collected_at}] No rows with delay data found.")
        return

    out_path = append_to_csv(rows, date_str)
    print(f"[{collected_at}] Appended {len(rows):,} rows to {out_path}")


if __name__ == "__main__":
    main()
