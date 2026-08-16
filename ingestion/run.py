"""Phase 1 entrypoint: TMDB ingestion for Greece -> raw Parquet lake.

Two-pass strategy (see ingestion/sources/tmdb/client.py for why):

1. Discover: for each (country, entity_type, provider), page through
   `discover/{type}` filtered to that provider/country to find candidate
   title ids. Each page is written to the raw lake as-is.
2. Enrich: for each unique title id found across all providers, fetch the
   authoritative `watch/providers` payload (subscription vs rent vs buy,
   per country) and write that to the raw lake too.

Every write is append-only and idempotent (see ingestion/core/lake.py) --
re-running this script for the same day is always safe.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from ingestion.core.lake import write_raw_batch
from ingestion.sources.tmdb.client import TMDBSource
from ingestion.sources.tmdb.config import DEFAULT_COUNTRIES, ENTITY_TYPES, PROVIDERS

logger = logging.getLogger("ingestion.run")

AVAILABILITY_BATCH_SIZE = 50


def run(
    *,
    lake_root: Path,
    api_key: str,
    countries: tuple[str, ...] = DEFAULT_COUNTRIES,
    providers: dict[str, int] = PROVIDERS,
    entity_types: tuple[str, ...] = ENTITY_TYPES,
    max_pages: int | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    started_at = time.monotonic()
    discovered_ids: dict[str, set[int]] = {et: set() for et in entity_types}
    discover_pages_written = 0

    with TMDBSource(api_key) as source:
        for country in countries:
            for entity_type in entity_types:
                for provider_slug, provider_id in providers.items():
                    records = []
                    for page_num, record in enumerate(
                        source.fetch_titles(
                            entity_type=entity_type, country=country, provider_id=provider_id
                        ),
                        start=1,
                    ):
                        records.append(record)
                        for result in record.payload.get("results", []):
                            discovered_ids[entity_type].add(result["id"])
                        if max_pages is not None and page_num >= max_pages:
                            break
                    written = write_raw_batch(
                        records,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint=f"discover_{provider_slug}",
                        entity_type=entity_type,
                        country=country,
                        run_id=run_id,
                    )
                    if written:
                        discover_pages_written += len(records)
                    logger.info(
                        "discover country=%s entity_type=%s provider=%s pages=%d",
                        country,
                        entity_type,
                        provider_slug,
                        len(records),
                    )

        availability_written = 0
        for entity_type, ids in discovered_ids.items():
            batch = []
            for tmdb_id in sorted(ids):
                batch.append(source.fetch_availability(entity_type=entity_type, source_title_id=tmdb_id))
                if len(batch) >= AVAILABILITY_BATCH_SIZE:
                    write_raw_batch(
                        batch,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint="watch_providers",
                        entity_type=entity_type,
                        country="ALL",
                        run_id=run_id,
                    )
                    availability_written += len(batch)
                    batch = []
            if batch:
                write_raw_batch(
                    batch,
                    lake_root=lake_root,
                    source="tmdb",
                    endpoint="watch_providers",
                    entity_type=entity_type,
                    country="ALL",
                    run_id=run_id,
                )
                availability_written += len(batch)

    summary = {
        "run_id": run_id,
        "duration_seconds": round(time.monotonic() - started_at, 1),
        "discover_pages_written": discover_pages_written,
        "discovered_title_counts": {et: len(ids) for et, ids in discovered_ids.items()},
        "availability_records_written": availability_written,
    }
    logger.info("run complete: %s", summary)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", action="append", dest="countries", help="ISO2 country code; repeatable. Defaults to configured launch countries.")
    parser.add_argument("--lake-root", default=os.environ.get("LAKE_ROOT", "data/lake"))
    parser.add_argument("--max-pages", type=int, default=None, help="Cap discover pagination per provider (useful for a quick smoke test).")
    args = parser.parse_args()

    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        raise SystemExit("TMDB_API_KEY is not set. Copy .env.example to .env and fill it in.")

    countries = tuple(args.countries) if args.countries else DEFAULT_COUNTRIES

    run(
        lake_root=Path(args.lake_root),
        api_key=api_key,
        countries=countries,
        max_pages=args.max_pages,
    )


if __name__ == "__main__":
    main()
