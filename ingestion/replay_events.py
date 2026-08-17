"""Rebuild current availability state from the append-only local event lake."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from ingestion.core.events import read_streaming_events
from watchpulse.availability_state import AvailabilityStateRepository
from watchpulse.config import Settings


def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default=settings.default_region)
    args = parser.parse_args()

    events = read_streaming_events(
        lake_root=settings.lake_root,
        source="streaming_availability",
        region=args.country,
    )
    applied = AvailabilityStateRepository(settings.database_path).apply(events)
    print(f"Read {len(events)} events; applied {applied} previously unseen events.")


if __name__ == "__main__":
    main()
