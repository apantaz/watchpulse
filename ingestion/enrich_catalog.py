"""Plan and execute bounded TMDB enrichment for the local serving catalog.

Modes:

* ``backfill`` selects catalog titles that have never retained the requested
  enrichment payloads. It is intended for the initial broad enrichment.
* ``incremental`` selects only new or stale titles, ordered by product value.

Planning is entirely local. External requests happen only after the plan has
been built and only when ``--dry-run`` is not supplied.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import duckdb
from dotenv import load_dotenv

from ingestion.core.lake import RawRecord, write_raw_batch
from ingestion.sources.tmdb.client import TMDBSource
from watchpulse.config import Settings
from watchpulse.pipeline_runs import PipelineRunRepository, sanitize_error

logger = logging.getLogger("ingestion.enrich_catalog")
EnrichmentMode = Literal["backfill", "incremental"]
BATCH_SIZE = 25


@dataclass(frozen=True)
class EnrichmentCandidate:
    content_type: str
    tmdb_id: int
    title: str
    priority: float
    reasons: tuple[str, ...]
    metadata_due: bool
    providers_due: bool


def _latest_observations(lake_root: Path, endpoint: str) -> dict[tuple[str, int], datetime]:
    files = sorted(
        lake_root.glob(
            f"raw/source=tmdb/endpoint={endpoint}/entity_type=*/country=ALL/date=*/*.parquet"
        )
    )
    if not files:
        return {}
    with duckdb.connect() as connection:
        rows = connection.execute(
            """
            select
                json_extract_string(cast(request_params as json), '$.entity_type'),
                try_cast(json_extract_string(cast(request_params as json), '$.tmdb_id') as bigint),
                max(cast(fetched_at as timestamptz))
            from read_parquet(?, union_by_name = true)
            group by 1, 2
            """,
            [[str(path) for path in files]],
        ).fetchall()
    return {
        (str(content_type), int(tmdb_id)): fetched_at
        for content_type, tmdb_id, fetched_at in rows
        if content_type in {"movie", "tv"} and tmdb_id is not None
    }


def _catalog_rows(database_path: Path) -> list[tuple]:
    if not database_path.is_file():
        raise FileNotFoundError(f"Serving catalog does not exist: {database_path}")
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            with ranked as (
                select
                    *,
                    row_number() over (
                        partition by region, provider_key, content_type
                        order by popularity_score desc nulls last, tmdb_id
                    ) as provider_rank
                from main_marts.catalog_availability
                where is_available or is_upcoming
            )
            select
                content_type,
                tmdb_id,
                max(title) as title,
                max(release_date) as release_date,
                max(popularity_score) as popularity_score,
                bool_or(is_upcoming) as is_upcoming,
                bool_or(is_available and provider_rank <= 10) as is_top_ten,
                max(available_since) as available_since,
                bool_or(poster_path is null or overview is null or release_date is null)
                    as missing_core_metadata,
                bool_or(runtime_minutes is null) as missing_runtime,
                bool_or(
                    content_type = 'tv'
                    and (season_count is null or episode_count is null)
                ) as missing_series_totals
            from ranked
            group by content_type, tmdb_id
            """
        ).fetchall()


def _is_due(last_seen: datetime | None, *, as_of: datetime, days: int) -> bool:
    if last_seen is None:
        return True
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return last_seen <= as_of - timedelta(days=days)


def plan_enrichment(
    *,
    database_path: Path,
    lake_root: Path,
    mode: EnrichmentMode = "incremental",
    max_titles: int = 250,
    include_providers: bool = True,
    as_of: datetime | None = None,
    upcoming_refresh_days: int = 7,
    recent_refresh_days: int = 30,
    series_refresh_days: int = 90,
    movie_refresh_days: int = 180,
    provider_refresh_days: int = 60,
) -> tuple[EnrichmentCandidate, ...]:
    """Return a capped, deterministic enrichment plan without external calls."""
    if mode not in {"backfill", "incremental"}:
        raise ValueError("mode must be backfill or incremental")
    if max_titles <= 0:
        raise ValueError("max_titles must be greater than zero")
    now = as_of or datetime.now(UTC)
    metadata_seen = _latest_observations(lake_root, "metadata")
    providers_seen = _latest_observations(lake_root, "watch_providers")
    candidates: list[EnrichmentCandidate] = []

    for row in _catalog_rows(database_path):
        (
            content_type,
            tmdb_id,
            title,
            release_date,
            popularity,
            is_upcoming,
            is_top_ten,
            available_since,
            missing_core,
            missing_runtime,
            missing_series_totals,
        ) = row
        key = (str(content_type), int(tmdb_id))
        recent_release = release_date is not None and release_date >= now.date() - timedelta(
            days=365
        )
        recently_added = available_since is not None and available_since >= now - timedelta(days=30)
        metadata_days = (
            upcoming_refresh_days
            if is_upcoming
            else recent_refresh_days
            if recent_release
            else series_refresh_days
            if content_type == "tv"
            else movie_refresh_days
        )
        provider_days = upcoming_refresh_days if is_upcoming else provider_refresh_days
        if mode == "backfill":
            metadata_due = key not in metadata_seen
            providers_due = include_providers and key not in providers_seen
        else:
            metadata_due = _is_due(metadata_seen.get(key), as_of=now, days=metadata_days)
            providers_due = include_providers and _is_due(
                providers_seen.get(key), as_of=now, days=provider_days
            )
        if not metadata_due and not providers_due:
            continue

        reasons: list[str] = []
        priority = min(float(popularity or 0), 200.0)
        if is_upcoming:
            priority += 1000
            reasons.append("upcoming")
        if recently_added:
            priority += 900
            reasons.append("recently_added")
        if recent_release:
            priority += 800
            reasons.append("recent_release")
        if is_top_ten:
            priority += 700
            reasons.append("top_10")
        if missing_core:
            priority += 500
            reasons.append("missing_core_metadata")
        if missing_runtime or missing_series_totals:
            priority += 300
            reasons.append("missing_details")
        if not reasons:
            reasons.append("new_or_stale")
        candidates.append(
            EnrichmentCandidate(
                content_type=str(content_type),
                tmdb_id=int(tmdb_id),
                title=str(title),
                priority=round(priority, 4),
                reasons=tuple(reasons),
                metadata_due=metadata_due,
                providers_due=providers_due,
            )
        )

    candidates.sort(key=lambda item: (-item.priority, item.content_type, item.tmdb_id))
    return tuple(candidates[:max_titles])


def _write_batch(
    records: list[RawRecord],
    *,
    lake_root: Path,
    endpoint: str,
    run_id: str,
) -> int:
    if not records:
        return 0
    record_count = len(records)
    write_raw_batch(
        records,
        lake_root=lake_root,
        source="tmdb",
        endpoint=endpoint,
        entity_type="mixed",
        country="ALL",
        run_id=run_id,
    )
    records.clear()
    return record_count


def execute_enrichment(
    plan: tuple[EnrichmentCandidate, ...],
    *,
    lake_root: Path,
    api_key: str,
    mode: EnrichmentMode,
    tmdb_base_url: str | None = None,
    database_path: Path | None = None,
) -> dict[str, object]:
    """Execute a previously built plan and retain completed batches for resumption."""
    run_id = uuid.uuid4().hex[:12]
    started_at = time.monotonic()
    options = {"base_url": tmdb_base_url} if tmdb_base_url else {}
    source = TMDBSource(api_key, **options)
    runs = PipelineRunRepository(database_path) if database_path else None
    metadata_records: list[RawRecord] = []
    provider_records: list[RawRecord] = []
    metadata_written = 0
    providers_written = 0
    if runs:
        runs.start(run_id=run_id, job_name="tmdb_catalog_enrichment", source="tmdb")
    try:
        with source:
            for candidate in plan:
                if candidate.metadata_due:
                    metadata_records.append(
                        source.fetch_metadata(
                            entity_type=candidate.content_type,
                            source_title_id=candidate.tmdb_id,
                        )
                    )
                    if len(metadata_records) >= BATCH_SIZE:
                        metadata_written += _write_batch(
                            metadata_records,
                            lake_root=lake_root,
                            endpoint="metadata",
                            run_id=run_id,
                        )
                if candidate.providers_due:
                    provider_records.append(
                        source.fetch_availability(
                            entity_type=candidate.content_type,
                            source_title_id=candidate.tmdb_id,
                        )
                    )
                    if len(provider_records) >= BATCH_SIZE:
                        providers_written += _write_batch(
                            provider_records,
                            lake_root=lake_root,
                            endpoint="watch_providers",
                            run_id=run_id,
                        )
            metadata_written += _write_batch(
                metadata_records, lake_root=lake_root, endpoint="metadata", run_id=run_id
            )
            providers_written += _write_batch(
                provider_records,
                lake_root=lake_root,
                endpoint="watch_providers",
                run_id=run_id,
            )
        summary: dict[str, object] = {
            "run_id": run_id,
            "mode": mode,
            "titles_planned": len(plan),
            "metadata_records_written": metadata_written,
            "provider_records_written": providers_written,
            "api_request_count": source.request_count,
            "duration_seconds": round(time.monotonic() - started_at, 1),
        }
        if runs:
            runs.succeed(
                run_id=run_id,
                api_request_count=source.request_count,
                rows_fetched=metadata_written + providers_written,
                rows_inserted=metadata_written + providers_written,
                details=summary,
            )
        return summary
    except Exception as error:
        if runs:
            runs.fail(
                run_id=run_id,
                api_request_count=source.request_count,
                error_message=sanitize_error(error, secrets=(api_key,)),
            )
        raise


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    load_dotenv()
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("backfill", "incremental"), default="incremental")
    parser.add_argument(
        "--max-titles", type=int, default=settings.tmdb_enrichment_max_titles_per_run
    )
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    parser.add_argument("--lake-root", type=Path, default=settings.lake_root)
    parser.add_argument("--serving-db", type=Path, default=settings.serving_database_path)
    args = parser.parse_args()
    plan = plan_enrichment(
        database_path=args.serving_db,
        lake_root=args.lake_root,
        mode=args.mode,
        max_titles=args.max_titles,
        include_providers=not args.metadata_only,
        upcoming_refresh_days=settings.tmdb_enrichment_upcoming_refresh_days,
        recent_refresh_days=settings.tmdb_enrichment_recent_refresh_days,
        series_refresh_days=settings.tmdb_enrichment_series_refresh_days,
        movie_refresh_days=settings.tmdb_enrichment_movie_refresh_days,
        provider_refresh_days=settings.tmdb_enrichment_provider_refresh_days,
    )
    plan_payload = [asdict(candidate) for candidate in plan]
    if args.plan_output:
        args.plan_output.write_text(json.dumps(plan_payload, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "planned titles=%d metadata_requests=%d provider_requests=%d mode=%s",
        len(plan),
        sum(item.metadata_due for item in plan),
        sum(item.providers_due for item in plan),
        args.mode,
    )
    if args.dry_run:
        for candidate in plan[:20]:
            logger.info("candidate: %s", asdict(candidate))
        return
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY is not set")
    summary = execute_enrichment(
        plan,
        lake_root=args.lake_root,
        api_key=settings.tmdb_api_key,
        mode=args.mode,
        tmdb_base_url=settings.tmdb_base_url,
        database_path=settings.database_path,
    )
    logger.info("enrichment complete: %s", summary)


if __name__ == "__main__":
    main()
