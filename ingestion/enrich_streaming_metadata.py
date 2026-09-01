"""Incrementally enrich lifecycle titles with canonical TMDB metadata."""

from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from ingestion.core.lake import write_raw_batch
from ingestion.sources.tmdb.client import TMDBSource
from watchpulse.config import Settings

logger = logging.getLogger("ingestion.enrich_streaming_metadata")
BATCH_SIZE = 10


def lifecycle_title_refs(
    lake_root: Path,
    *,
    event_type: str = "upcoming",
    country: str | None = None,
) -> tuple[tuple[str, int], ...]:
    country_pattern = country.upper() if country else "*"
    event_files = sorted(
        lake_root.glob(
            "raw/source=streaming_availability/"
            f"endpoint=changes_{event_type}/entity_type=show/country={country_pattern}/"
            "date=*/*.parquet"
        )
    )
    if not event_files:
        return ()

    with duckdb.connect() as connection:
        lifecycle_rows = connection.execute(
            """
            with raw as (
                select cast(payload as json) as payload
                from read_parquet(?, union_by_name = true)
            )
            select distinct
                split_part(json_extract_string(show_row.value, '$.tmdbId'), '/', 1) as content_type,
                try_cast(
                    split_part(json_extract_string(show_row.value, '$.tmdbId'), '/', 2)
                    as bigint
                ) as tmdb_id
            from raw, json_each(payload, '$.shows') as show_row
            """,
            [[str(path) for path in event_files]],
        ).fetchall()
    return tuple(
        sorted(
            (str(content_type), int(tmdb_id))
            for content_type, tmdb_id in lifecycle_rows
            if content_type in {"movie", "tv"} and tmdb_id is not None
        )
    )


def _retained_refs(lake_root: Path, endpoint: str) -> set[tuple[str, int]]:
    files = sorted(
        lake_root.glob(
            f"raw/source=tmdb/endpoint={endpoint}/entity_type=*/country=ALL/date=*/*.parquet"
        )
    )
    if not files:
        return set()
    with duckdb.connect() as connection:
        existing_rows = connection.execute(
            """
            select distinct
                json_extract_string(cast(request_params as json), '$.entity_type'),
                cast(json_extract_string(cast(request_params as json), '$.tmdb_id') as bigint)
            from read_parquet(?, union_by_name = true)
            """,
            [[str(path) for path in files]],
        ).fetchall()
    return {(str(content_type), int(tmdb_id)) for content_type, tmdb_id in existing_rows}


def pending_title_refs(
    lake_root: Path,
    *,
    event_type: str = "upcoming",
    country: str | None = None,
    endpoint: str = "metadata",
) -> tuple[tuple[str, int], ...]:
    refs = set(lifecycle_title_refs(lake_root, event_type=event_type, country=country))
    return tuple(sorted(refs - _retained_refs(lake_root, endpoint)))


def run(
    *,
    lake_root: Path,
    api_key: str,
    event_type: str = "upcoming",
    country: str | None = None,
    max_titles: int | None = None,
    include_watch_providers: bool = False,
    tmdb_base_url: str | None = None,
) -> dict[str, object]:
    metadata_refs = pending_title_refs(
        lake_root, event_type=event_type, country=country, endpoint="metadata"
    )
    availability_refs = (
        pending_title_refs(
            lake_root, event_type=event_type, country=country, endpoint="watch_providers"
        )
        if include_watch_providers
        else ()
    )
    if max_titles is not None:
        allowed = set(
            lifecycle_title_refs(lake_root, event_type=event_type, country=country)[:max_titles]
        )
        metadata_refs = tuple(ref for ref in metadata_refs if ref in allowed)
        availability_refs = tuple(ref for ref in availability_refs if ref in allowed)
    source_options = {"base_url": tmdb_base_url} if tmdb_base_url else {}
    source = TMDBSource(api_key, **source_options)
    run_id = uuid.uuid4().hex[:12]
    metadata_records = []
    availability_records = []
    metadata_written = 0
    availability_written = 0
    with source:
        for content_type, tmdb_id in metadata_refs:
            metadata_records.append(
                source.fetch_metadata(entity_type=content_type, source_title_id=tmdb_id)
            )
        for content_type, tmdb_id in availability_refs:
            availability_records.append(
                source.fetch_availability(entity_type=content_type, source_title_id=tmdb_id)
            )
        for start in range(0, len(metadata_records), BATCH_SIZE):
            batch = metadata_records[start : start + BATCH_SIZE]
            write_raw_batch(
                batch,
                lake_root=lake_root,
                source="tmdb",
                endpoint="metadata",
                entity_type="mixed",
                country="ALL",
                run_id=run_id,
            )
            metadata_written += len(batch)
        for start in range(0, len(availability_records), BATCH_SIZE):
            batch = availability_records[start : start + BATCH_SIZE]
            write_raw_batch(
                batch,
                lake_root=lake_root,
                source="tmdb",
                endpoint="watch_providers",
                entity_type="mixed",
                country="ALL",
                run_id=run_id,
            )
            availability_written += len(batch)
    return {
        "run_id": run_id,
        "event_type": event_type,
        "country": country.upper() if country else None,
        "metadata_titles_requested": len(metadata_refs),
        "availability_titles_requested": len(availability_refs),
        "metadata_records_written": metadata_written,
        "availability_records_written": availability_written,
        "api_request_count": source.request_count,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    load_dotenv()
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-type", choices=("new", "upcoming"), default="upcoming")
    parser.add_argument("--country")
    parser.add_argument("--max-titles", type=int)
    parser.add_argument("--include-watch-providers", action="store_true")
    parser.add_argument("--lake-root", default=str(settings.lake_root))
    args = parser.parse_args()
    if args.max_titles is not None and args.max_titles <= 0:
        raise SystemExit("--max-titles must be greater than zero")
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY is not set")
    summary = run(
        lake_root=Path(args.lake_root),
        api_key=settings.tmdb_api_key,
        event_type=args.event_type,
        country=args.country,
        max_titles=args.max_titles,
        include_watch_providers=args.include_watch_providers,
        tmdb_base_url=settings.tmdb_base_url,
    )
    logger.info("enrichment complete: %s", summary)


if __name__ == "__main__":
    main()
