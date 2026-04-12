"""
Local loop runner for the snapshot collector.
Calls collect_snapshot.main() on a fixed interval until stopped with Ctrl+C.

Usage:
    python scripts/run_collector.py               # every 5 minutes (default)
    python scripts/run_collector.py --interval 2  # every 2 minutes
"""

from __future__ import annotations

import argparse
import sys
import time

import collect_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the snapshot collector in a loop.")
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        metavar="MINUTES",
        help="Minutes between collections (default: 5)",
    )
    args = parser.parse_args()
    interval_seconds = args.interval * 60

    print(f"Starting collector — fetching every {args.interval} min. Press Ctrl+C to stop.")
    print()

    try:
        while True:
            collect_snapshot.main()
            print(f"  Next fetch in {args.interval} min...\n")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
