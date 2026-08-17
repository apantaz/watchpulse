"""Print recent normalized streaming lifecycle events from the local lake."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pyarrow.parquet as pq
from dotenv import load_dotenv

from ingestion.sources.streaming_availability.adapter import parse_tmdb_id


def _titles(lake_root: Path, country: str) -> dict[tuple[int, str], str]:
    result = {}
    pattern = (
        "raw/source=streaming_availability/endpoint=changes_*/entity_type=show/"
        f"country={country}/date=*/*.parquet"
    )
    for path in lake_root.glob(pattern):
        for raw_payload in pq.read_table(path, columns=["payload"])["payload"].to_pylist():
            payload = json.loads(raw_payload)
            for show in payload.get("shows", {}).values():
                show_type = str(show.get("showType") or "")
                tmdb_value = show.get("tmdbId")
                if not tmdb_value or show_type not in {"movie", "series"}:
                    continue
                content_type = "movie" if show_type == "movie" else "tv"
                result[(parse_tmdb_id(str(tmdb_value), show_type=show_type), content_type)] = str(
                    show.get("title") or show.get("originalTitle") or "Unknown title"
                )
    return result


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default="GR")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--lake-root", default=os.environ.get("LAKE_ROOT", "data/lake"))
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")

    country = args.country.upper()
    lake_root = Path(args.lake_root)
    paths = list(
        lake_root.glob(f"events/source=streaming_availability/region={country}/date=*/*.parquet")
    )
    if not paths:
        raise SystemExit(f"No local streaming events found for {country}")

    titles = _titles(lake_root, country)
    events = []
    for path in paths:
        events.extend(pq.read_table(path).to_pylist())
    events.sort(key=lambda event: event["ingested_at"], reverse=True)

    print(f"Recent streaming lifecycle events for {country}\n")
    for event in events[: args.limit]:
        title = titles.get((event["tmdb_id"], event["content_type"]), f"TMDB {event['tmdb_id']}")
        when = event["event_date"] or "unknown date"
        print(
            f"{title} | {event['provider_key']} | {event['content_type']} | "
            f"{event['event_type']} | {when}"
        )


if __name__ == "__main__":
    main()
