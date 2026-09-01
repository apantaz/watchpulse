"""Run a guarded, end-to-end WatchPulse catalog refresh.

The workflow keeps external ingestion out of the serving path and publishes
only validated DuckDB candidates. TMDB discovery is mandatory; lifecycle and
enrichment stages are independently configurable and bounded.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from ingestion.enrich_catalog import EnrichmentMode, execute_enrichment, plan_enrichment
from ingestion.enrich_streaming_metadata import run as enrich_lifecycle_metadata
from ingestion.run import run as run_tmdb_discovery
from ingestion.run_streaming_availability import run as run_streaming_lifecycle
from ingestion.sources.streaming_availability.config import DEFAULT_CHANGE_TYPES
from ingestion.sources.tmdb.config import PROVIDERS
from watchpulse.config import Settings
from watchpulse.warehouse_publish import publish_warehouse

logger = logging.getLogger("ingestion.full_refresh")


def run_full_refresh(
    *,
    settings: Settings,
    country: str,
    provider_keys: tuple[str, ...],
    streaming_max_requests: int,
    enrichment_max_titles: int,
    include_watch_providers: bool,
    enrichment_mode: EnrichmentMode = "incremental",
    run_streaming: bool = True,
    run_enrichment: bool = True,
    project_dir: Path = Path("warehouse"),
) -> dict[str, object]:
    """Refresh raw sources and atomically publish validated serving data."""
    if not settings.tmdb_api_key:
        raise ValueError("TMDB_API_KEY is required")
    unknown = set(provider_keys) - PROVIDERS.keys()
    if unknown:
        raise ValueError(f"Unknown provider keys: {sorted(unknown)}")
    country = country.upper()
    summary: dict[str, object] = {
        "country": country,
        "provider_keys": list(provider_keys),
        "stages": {},
    }
    stages = summary["stages"]
    assert isinstance(stages, dict)

    logger.info(
        "full refresh started country=%s providers=%s streaming=%s enrichment=%s",
        country,
        ",".join(provider_keys),
        run_streaming,
        run_enrichment,
    )
    logger.info("stage started: tmdb_discovery")
    discovery = run_tmdb_discovery(
        lake_root=settings.lake_root,
        database_path=settings.database_path,
        api_key=settings.tmdb_api_key,
        countries=(country,),
        providers={key: PROVIDERS[key] for key in provider_keys},
        enrich=False,
        tmdb_base_url=settings.tmdb_base_url,
    )
    stages["tmdb_discovery"] = discovery
    if not discovery["discovery_complete"]:
        raise RuntimeError("TMDB discovery was incomplete; serving database was not published")
    logger.info(
        "stage completed: tmdb_discovery requests=%s pages=%s",
        discovery["api_request_count"],
        discovery["discover_pages_written"],
    )

    logger.info("stage started: catalog_publication")
    publish_warehouse(project_dir, settings.serving_database_path)
    stages["catalog_publication"] = {"status": "success"}
    logger.info("stage completed: catalog_publication")

    if run_streaming:
        if not settings.streaming_availability_api_key:
            raise ValueError("STREAMING_AVAILABILITY_API_KEY is required")
        logger.info("stage started: streaming_lifecycle")
        stages["streaming_lifecycle"] = run_streaming_lifecycle(
            lake_root=settings.lake_root,
            database_path=settings.database_path,
            api_key=settings.streaming_availability_api_key,
            base_url=settings.streaming_availability_base_url,
            countries=(country,),
            provider_keys=provider_keys,
            max_requests_per_run=streaming_max_requests,
            monthly_cap=settings.streaming_availability_monthly_cap,
            change_types=DEFAULT_CHANGE_TYPES,
            max_pages_per_type=None,
        )
        logger.info(
            "stage completed: streaming_lifecycle requests=%s events=%s",
            stages["streaming_lifecycle"]["api_request_count"],
            stages["streaming_lifecycle"]["events_written"],
        )

    if run_enrichment:
        logger.info("stage started: tmdb_enrichment_planning")
        plan = plan_enrichment(
            database_path=settings.serving_database_path,
            lake_root=settings.lake_root,
            mode=enrichment_mode,
            max_titles=enrichment_max_titles,
            include_providers=include_watch_providers,
            upcoming_refresh_days=settings.tmdb_enrichment_upcoming_refresh_days,
            recent_refresh_days=settings.tmdb_enrichment_recent_refresh_days,
            series_refresh_days=settings.tmdb_enrichment_series_refresh_days,
            movie_refresh_days=settings.tmdb_enrichment_movie_refresh_days,
            provider_refresh_days=settings.tmdb_enrichment_provider_refresh_days,
        )
        stages["tmdb_enrichment_plan"] = {
            "titles": len(plan),
            "metadata_requests": sum(item.metadata_due for item in plan),
            "provider_requests": sum(item.providers_due for item in plan),
            "sample": [asdict(item) for item in plan[:10]],
        }
        logger.info(
            "stage completed: tmdb_enrichment_planning titles=%d requests=%d",
            len(plan),
            sum(item.metadata_due + item.providers_due for item in plan),
        )
        logger.info("stage started: tmdb_enrichment")
        stages["tmdb_enrichment"] = execute_enrichment(
            plan,
            lake_root=settings.lake_root,
            api_key=settings.tmdb_api_key,
            mode=enrichment_mode,
            tmdb_base_url=settings.tmdb_base_url,
            database_path=settings.database_path,
        )
        logger.info(
            "stage completed: tmdb_enrichment requests=%s",
            stages["tmdb_enrichment"]["api_request_count"],
        )

    if run_streaming:
        logger.info("stage started: lifecycle_metadata")
        lifecycle_enrichment = {}
        for event_type in DEFAULT_CHANGE_TYPES:
            lifecycle_enrichment[event_type] = enrich_lifecycle_metadata(
                lake_root=settings.lake_root,
                api_key=settings.tmdb_api_key,
                event_type=event_type,
                country=country,
                include_watch_providers=False,
                tmdb_base_url=settings.tmdb_base_url,
            )
        stages["lifecycle_metadata"] = lifecycle_enrichment
        logger.info("stage completed: lifecycle_metadata")

    logger.info("stage started: final_publication")
    publish_warehouse(project_dir, settings.serving_database_path)
    stages["final_publication"] = {"status": "success"}
    logger.info("stage completed: final_publication")
    logger.info("full refresh completed country=%s", country)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default="GR")
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--streaming-max-requests", type=int, default=100)
    parser.add_argument("--enrichment-max-titles", type=int, default=20_000)
    parser.add_argument(
        "--enrichment-mode", choices=("backfill", "incremental"), default="incremental"
    )
    parser.add_argument("--include-watch-providers", action="store_true")
    parser.add_argument("--skip-streaming", action="store_true")
    parser.add_argument("--skip-enrichment", action="store_true")
    parser.add_argument("--summary-output", type=Path)
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv()
    settings = Settings.from_env()
    args = build_parser().parse_args()
    providers = tuple(args.providers) if args.providers else settings.supported_providers
    summary = run_full_refresh(
        settings=settings,
        country=args.country,
        provider_keys=providers,
        streaming_max_requests=args.streaming_max_requests,
        enrichment_max_titles=args.enrichment_max_titles,
        include_watch_providers=args.include_watch_providers,
        enrichment_mode=args.enrichment_mode,
        run_streaming=not args.skip_streaming,
        run_enrichment=not args.skip_enrichment,
    )
    rendered = json.dumps(summary, indent=2, default=str)
    if args.summary_output:
        args.summary_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
