"""Ingest bounded streaming lifecycle changes into the local Parquet lake."""

from __future__ import annotations

import argparse
import logging
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from ingestion.core.events import write_streaming_events
from ingestion.core.lake import write_raw_batch
from ingestion.sources.streaming_availability.adapter import events_from_changes
from ingestion.sources.streaming_availability.client import StreamingAvailabilitySource
from ingestion.sources.streaming_availability.config import (
    DEFAULT_CHANGE_TYPES,
    SUPPORTED_CHANGE_TYPES,
    subscription_catalogs,
)
from watchpulse.availability_state import AvailabilityStateRepository
from watchpulse.config import Settings
from watchpulse.pipeline_runs import PipelineRunRepository, sanitize_error

logger = logging.getLogger("ingestion.run_streaming_availability")
SOURCE = "streaming_availability"


def run(
    *,
    lake_root: Path,
    database_path: Path,
    api_key: str,
    base_url: str,
    countries: tuple[str, ...],
    provider_keys: tuple[str, ...],
    max_requests_per_run: int,
    monthly_cap: int,
    change_types: tuple[str, ...] = DEFAULT_CHANGE_TYPES,
    max_pages_per_type: int | None = None,
) -> dict:
    runs = PipelineRunRepository(database_path)
    availability_state = AvailabilityStateRepository(database_path)
    monthly_used = runs.request_count_for_current_month(source=SOURCE)
    monthly_remaining = monthly_cap - monthly_used
    request_budget = min(max_requests_per_run, monthly_remaining)
    if request_budget <= 0:
        raise RuntimeError(
            f"Monthly Streaming Availability request cap exhausted: {monthly_used}/{monthly_cap}"
        )

    run_id = uuid.uuid4().hex[:12]
    started_at = time.monotonic()
    raw_pages_written = 0
    events_written = 0
    state_events_applied = 0
    catalogs = subscription_catalogs(provider_keys)
    source = StreamingAvailabilitySource(
        api_key,
        base_url=base_url,
        max_requests=request_budget,
    )
    runs.start(run_id=run_id, job_name="streaming_lifecycle_ingestion", source=SOURCE)

    try:
        with source:
            for country in countries:
                for change_type in change_types:
                    for record in source.fetch_changes(
                        country=country,
                        catalogs=catalogs,
                        change_type=change_type,
                        max_pages=max_pages_per_type,
                    ):
                        write_raw_batch(
                            [record],
                            lake_root=lake_root,
                            source=SOURCE,
                            endpoint=f"changes_{change_type}",
                            entity_type="show",
                            country=country.upper(),
                            run_id=run_id,
                        )
                        raw_pages_written += 1
                        events = events_from_changes(record.payload, region=country)
                        write_streaming_events(
                            events,
                            lake_root=lake_root,
                            source=SOURCE,
                            region=country,
                            run_id=run_id,
                        )
                        events_written += len(events)
                        state_events_applied += availability_state.apply(events)

        summary = {
            "run_id": run_id,
            "duration_seconds": round(time.monotonic() - started_at, 1),
            "api_request_count": source.request_count,
            "monthly_requests_before_run": monthly_used,
            "monthly_cap": monthly_cap,
            "request_budget": request_budget,
            "raw_pages_written": raw_pages_written,
            "events_written": events_written,
            "state_events_applied": state_events_applied,
            "countries": list(countries),
            "provider_keys": list(provider_keys),
            "catalogs": list(catalogs),
            "change_types": list(change_types),
            "max_pages_per_type": max_pages_per_type,
        }
        runs.succeed(
            run_id=run_id,
            api_request_count=source.request_count,
            rows_fetched=events_written,
            rows_inserted=events_written,
            details=summary,
        )
        logger.info("run complete: %s", summary)
        return summary
    except Exception as exc:
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
    parser.add_argument("--country", action="append", dest="countries")
    parser.add_argument(
        "--change-type",
        action="append",
        dest="change_types",
        choices=SUPPORTED_CHANGE_TYPES,
    )
    parser.add_argument("--max-requests", type=int)
    pagination = parser.add_mutually_exclusive_group()
    pagination.add_argument(
        "--max-pages-per-type",
        type=int,
        default=1,
        help="Pages per lifecycle type (default: 1).",
    )
    pagination.add_argument(
        "--all-pages",
        action="store_true",
        help="Follow cursors until hasMore=false, subject to request limits.",
    )
    args = parser.parse_args()

    if not settings.streaming_availability_api_key:
        raise SystemExit("STREAMING_AVAILABILITY_API_KEY is not set in .env")

    max_requests = (
        args.max_requests
        if args.max_requests is not None
        else settings.streaming_availability_max_requests_per_run
    )
    if max_requests <= 0:
        raise SystemExit("--max-requests must be greater than zero")
    if args.max_pages_per_type is not None and args.max_pages_per_type <= 0:
        raise SystemExit("--max-pages-per-type must be greater than zero")

    max_pages_per_type = None if args.all_pages else args.max_pages_per_type

    run(
        lake_root=settings.lake_root,
        database_path=settings.database_path,
        api_key=settings.streaming_availability_api_key,
        base_url=settings.streaming_availability_base_url,
        countries=tuple(args.countries) if args.countries else settings.supported_regions,
        provider_keys=settings.supported_providers,
        max_requests_per_run=max_requests,
        monthly_cap=settings.streaming_availability_monthly_cap,
        change_types=tuple(args.change_types) if args.change_types else DEFAULT_CHANGE_TYPES,
        max_pages_per_type=max_pages_per_type,
    )


if __name__ == "__main__":
    main()
