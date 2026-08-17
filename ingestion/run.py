"""Phase 1 entrypoint: TMDB ingestion for Greece -> raw Parquet lake.

Two-pass strategy (see ingestion/sources/tmdb/client.py for why):

1. Discover: for each (country, entity_type, provider), page through
   `discover/{type}` filtered to that provider/country to find candidate
   title ids. Each page is written to the raw lake as-is.
2. Enrich: for each unique title id found across all providers, fetch its
   metadata and authoritative `watch/providers` payload and write both to
   the raw lake.

Every write is append-only and idempotent (see ingestion/core/lake.py) --
re-running this script for the same day is always safe.
"""

from __future__ import annotations

import argparse
import logging
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from ingestion.core.lake import write_raw_batch
from ingestion.sources.tmdb.client import TMDBSource
from ingestion.sources.tmdb.config import DEFAULT_COUNTRIES, ENTITY_TYPES, PROVIDERS
from watchpulse.config import Settings
from watchpulse.pipeline_runs import PipelineRunRepository, sanitize_error

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
    tmdb_base_url: str | None = None,
    database_path: Path | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    started_at = time.monotonic()
    discovered_ids: dict[str, set[int]] = {et: set() for et in entity_types}
    discover_pages_written = 0

    source_options = {"base_url": tmdb_base_url} if tmdb_base_url else {}
    source = TMDBSource(api_key, **source_options)
    runs = PipelineRunRepository(database_path) if database_path else None
    if runs:
        runs.start(run_id=run_id, job_name="tmdb_catalog_ingestion", source="tmdb")

    try:
        with source:
            for country in countries:
                for entity_type in entity_types:
                    for provider_slug, provider_id in providers.items():
                        records = []
                        for page_num, record in enumerate(
                            source.fetch_titles(
                                entity_type=entity_type,
                                country=country,
                                provider_id=provider_id,
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

            metadata_written = 0
            availability_written = 0
            for entity_type, ids in discovered_ids.items():
                metadata_batch = []
                availability_batch = []
                for tmdb_id in sorted(ids):
                    metadata_batch.append(
                        source.fetch_metadata(entity_type=entity_type, source_title_id=tmdb_id)
                    )
                    availability_batch.append(
                        source.fetch_availability(entity_type=entity_type, source_title_id=tmdb_id)
                    )
                    if len(metadata_batch) < AVAILABILITY_BATCH_SIZE:
                        continue
                    write_raw_batch(
                        metadata_batch,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint="metadata",
                        entity_type=entity_type,
                        country="ALL",
                        run_id=run_id,
                    )
                    write_raw_batch(
                        availability_batch,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint="watch_providers",
                        entity_type=entity_type,
                        country="ALL",
                        run_id=run_id,
                    )
                    metadata_written += len(metadata_batch)
                    availability_written += len(availability_batch)
                    metadata_batch = []
                    availability_batch = []
                if metadata_batch:
                    write_raw_batch(
                        metadata_batch,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint="metadata",
                        entity_type=entity_type,
                        country="ALL",
                        run_id=run_id,
                    )
                    write_raw_batch(
                        availability_batch,
                        lake_root=lake_root,
                        source="tmdb",
                        endpoint="watch_providers",
                        entity_type=entity_type,
                        country="ALL",
                        run_id=run_id,
                    )
                    metadata_written += len(metadata_batch)
                    availability_written += len(availability_batch)

        raw_records_written = discover_pages_written + metadata_written + availability_written
        summary = {
            "run_id": run_id,
            "duration_seconds": round(time.monotonic() - started_at, 1),
            "api_request_count": source.request_count,
            "discover_pages_written": discover_pages_written,
            "discovered_title_counts": {
                entity_type: len(ids) for entity_type, ids in discovered_ids.items()
            },
            "metadata_records_written": metadata_written,
            "availability_records_written": availability_written,
        }
        if runs:
            runs.succeed(
                run_id=run_id,
                api_request_count=source.request_count,
                rows_fetched=raw_records_written,
                rows_inserted=raw_records_written,
                details=summary,
            )
        logger.info("run complete: %s", summary)
        return summary
    except Exception as exc:
        if runs:
            runs.fail(
                run_id=run_id,
                api_request_count=source.request_count,
                error_message=sanitize_error(exc, secrets=(api_key,)),
            )
        logger.exception("run failed run_id=%s", run_id)
        raise


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    settings = Settings.from_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--country",
        action="append",
        dest="countries",
        help="ISO2 country code; repeatable. Defaults to configured launch countries.",
    )
    parser.add_argument("--lake-root", default=str(settings.lake_root))
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Cap discover pagination per provider (useful for a quick smoke test).",
    )
    args = parser.parse_args()

    api_key = settings.tmdb_api_key
    if not api_key:
        raise SystemExit("TMDB_API_KEY is not set. Copy .env.example to .env and fill it in.")

    countries = tuple(args.countries) if args.countries else settings.supported_regions
    unknown_providers = set(settings.supported_providers) - PROVIDERS.keys()
    if unknown_providers:
        raise SystemExit(
            "SUPPORTED_PROVIDERS contains unknown provider keys: "
            + ", ".join(sorted(unknown_providers))
        )
    providers = {key: PROVIDERS[key] for key in settings.supported_providers}

    run(
        lake_root=Path(args.lake_root),
        api_key=api_key,
        countries=countries,
        providers=providers,
        max_pages=args.max_pages,
        tmdb_base_url=settings.tmdb_base_url,
        database_path=settings.database_path,
    )


if __name__ == "__main__":
    main()
