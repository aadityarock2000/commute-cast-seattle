###
# This script is used to check the data sources for the project.
# It will download the data from the URLs and save it to the raw data directory.
###




from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import pandas as pd
import requests

# Making sure the raw data directory exists
DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# GTFS_ZIP_URL = "https://metro.kingcounty.gov/gtfs/google_transit.zip"

# # These feed links are publicly exposed from King County Metro's developer page.
# TRIP_UPDATES_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/trip-updates.json"
# VEHICLE_POSITIONS_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehicle-positions.json"
# SERVICE_ALERTS_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/alerts.json"

# We now have a bunch of URLs to extract data from
# We'll need to download the data from these URLs and save it to the raw data directory

# GTFS_ZIP_URL is the URL for the GTFS zip file - Static data
# TRIP_UPDATES_URL is the URL for the trip updates feed - JSON
# VEHICLE_POSITIONS_URL is the URL for the vehicle positions feed - JSON
# SERVICE_ALERTS_URL is the URL for the service alerts feed - JSON

#GTFS is the statis schedule dataset - This would be our baseline.
#this contains 4 files - routes.txt, trips.txt, stop_times.txt, stops.txt
#routes.txt - Transit routes
#stops.txt - Transit stops
#trips.txt - A trip is one specific run of a route.


#stop_times.txt - This is one of the most important tables.
# It tells you, for each trip:
# which stops it visits
# in what order
# scheduled arrival/departure times


#--------------------------------#
# The other 3 files are used to build a real-time feed.
#--------------------------------#

# trip-updates.json - Live updates to planned trips.
# vehicle-positions.json - Where the actual bus/train vehicle is currently located
# alerts.json - Disruptions, detours, service issues.



GTFS_ZIP_URL = "https://metro.kingcounty.gov/gtfs/google_transit.zip"
TRIP_UPDATES_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates_pb.json"
VEHICLE_POSITIONS_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions_pb.json"
SERVICE_ALERTS_URL = "https://s3.amazonaws.com/kcm-alerts-realtime-prod/alerts_pb.json"

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


def download_json(session: requests.Session, url: str, out_path: Path) -> dict | None:
    print(f"Fetching JSON: {url}")
    try:
        r = session.get(url, timeout=(10, 60))
        r.raise_for_status()
        data = r.json()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved -> {out_path}")
        return data
    except Exception as e:
        print(f"WARNING: failed to fetch {url}")
        print(f"Reason: {e}")
        return None



def download_file(url: str, out_path: Path) -> None:
    print(f"Downloading: {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    print(f"Saved -> {out_path}")


# def download_json(url: str, out_path: Path) -> dict:
#     print(f"Fetching JSON: {url}")
#     r = requests.get(url, timeout=30)
#     r.raise_for_status()
#     data = r.json()
#     with open(out_path, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)
#     print(f"Saved -> {out_path}")
#     return data


def inspect_gtfs_zip(zip_path: Path) -> None:
    print("\nInspecting GTFS zip...")
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        print("GTFS files found:")
        for name in names:
            print(" -", name)

        required = ["routes.txt", "trips.txt", "stop_times.txt", "stops.txt"]
        missing = [f for f in required if f not in names]
        if missing:
            raise ValueError(f"Missing expected GTFS files: {missing}")

        routes = pd.read_csv(io.BytesIO(z.read("routes.txt")))
        stops = pd.read_csv(io.BytesIO(z.read("stops.txt")))
        trips = pd.read_csv(io.BytesIO(z.read("trips.txt")))
        stop_times = pd.read_csv(io.BytesIO(z.read("stop_times.txt")))

    print("\nBasic counts:")
    print(f"routes: {len(routes):,}")
    print(f"stops: {len(stops):,}")
    print(f"trips: {len(trips):,}")
    print(f"stop_times: {len(stop_times):,}")

    print("\nSample routes:")
    print(routes.head(10).to_string(index=False))

    print("\nSample stops:")
    print(stops.head(10).to_string(index=False))

    routes.head(200).to_csv(DATA_DIR / "routes_sample.csv", index=False)
    stops.head(200).to_csv(DATA_DIR / "stops_sample.csv", index=False)


def inspect_realtime_payload(name: str, payload: dict) -> None:
    print(f"\nInspecting {name} payload...")
    if isinstance(payload, dict):
        print("Top-level keys:", list(payload.keys())[:20])

        # Many GTFS-RT JSON feeds expose an entity array
        entity = payload.get("entity", [])
        print(f"entity count: {len(entity)}")

        if entity:
            first = entity[0]
            print("First entity keys:", list(first.keys()))
            print("First entity preview:")
            print(json.dumps(first, indent=2)[:2000])


def main() -> None:
    session = build_session()

    gtfs_zip_path = DATA_DIR / "google_transit.zip"
    trip_updates_path = DATA_DIR / "realtime_trip_updates.json"
    vehicle_positions_path = DATA_DIR / "realtime_vehicle_positions.json"
    alerts_path = DATA_DIR / "realtime_alerts.json"

    download_file(GTFS_ZIP_URL, gtfs_zip_path)
    inspect_gtfs_zip(gtfs_zip_path)

    trip_updates = download_json(session, TRIP_UPDATES_URL, trip_updates_path)
    vehicle_positions = download_json(session, VEHICLE_POSITIONS_URL, vehicle_positions_path)
    alerts = download_json(session, SERVICE_ALERTS_URL, alerts_path)

    if trip_updates is not None:
        inspect_realtime_payload("trip_updates", trip_updates)

    if vehicle_positions is not None:
        inspect_realtime_payload("vehicle_positions", vehicle_positions)

    if alerts is not None:
        inspect_realtime_payload("service_alerts", alerts)

    print("\nDone.")


if __name__ == "__main__":
    main()