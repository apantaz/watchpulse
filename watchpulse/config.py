"""Environment-backed application configuration.

Operational values live here so ingestion, transformation, and serving code can
share one contract without hardcoding deployment-specific paths or regions.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _regions(value: str) -> tuple[str, ...]:
    regions = tuple(region.upper() for region in _csv(value))
    invalid = [region for region in regions if len(region) != 2 or not region.isalpha()]
    if invalid:
        raise ValueError(f"Invalid ISO 3166-1 alpha-2 region codes: {invalid}")
    if not regions:
        raise ValueError("SUPPORTED_REGIONS must contain at least one region")
    return regions


@dataclass(frozen=True)
class Settings:
    tmdb_api_key: str | None
    tmdb_base_url: str
    streaming_availability_api_key: str | None
    streaming_availability_base_url: str
    streaming_availability_max_requests_per_run: int
    streaming_availability_monthly_cap: int
    lake_root: Path
    database_path: Path
    serving_database_path: Path
    frontend_origins: tuple[str, ...]
    default_region: str
    supported_regions: tuple[str, ...]
    supported_providers: tuple[str, ...]
    new_release_days: int
    recently_added_days: int
    leaving_soon_days: int
    tmdb_enrichment_max_titles_per_run: int
    tmdb_enrichment_upcoming_refresh_days: int
    tmdb_enrichment_recent_refresh_days: int
    tmdb_enrichment_series_refresh_days: int
    tmdb_enrichment_movie_refresh_days: int
    tmdb_enrichment_provider_refresh_days: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        supported_regions = _regions(values.get("SUPPORTED_REGIONS", "GR"))
        default_region = values.get("DEFAULT_REGION", supported_regions[0]).upper()
        if default_region not in supported_regions:
            raise ValueError("DEFAULT_REGION must be included in SUPPORTED_REGIONS")

        return cls(
            tmdb_api_key=values.get("TMDB_API_KEY") or None,
            tmdb_base_url=values.get("TMDB_BASE_URL", "https://api.themoviedb.org/3"),
            streaming_availability_api_key=(values.get("STREAMING_AVAILABILITY_API_KEY") or None),
            streaming_availability_base_url=values.get(
                "STREAMING_AVAILABILITY_BASE_URL",
                "https://api.movieofthenight.com/v4",
            ),
            streaming_availability_max_requests_per_run=_positive_int(
                values, "STREAMING_AVAILABILITY_MAX_REQUESTS_PER_RUN", 80
            ),
            streaming_availability_monthly_cap=_positive_int(
                values, "STREAMING_AVAILABILITY_MONTHLY_CAP", 900
            ),
            lake_root=Path(values.get("LAKE_ROOT", "data/lake")),
            database_path=Path(values.get("DATABASE_PATH", "data/warehouse.duckdb")),
            serving_database_path=Path(
                values.get("WATCHPULSE_SERVING_DB_PATH", "data/warehouse_serving.duckdb")
            ),
            frontend_origins=_csv(
                values.get(
                    "WATCHPULSE_FRONTEND_ORIGINS",
                    "http://127.0.0.1:5173,http://localhost:5173",
                )
            ),
            default_region=default_region,
            supported_regions=supported_regions,
            supported_providers=_csv(
                values.get(
                    "SUPPORTED_PROVIDERS",
                    "netflix,disney_plus,prime_video,apple_tv_plus",
                )
            ),
            new_release_days=_positive_int(values, "NEW_RELEASE_DAYS", 90),
            recently_added_days=_positive_int(values, "RECENTLY_ADDED_DAYS", 30),
            leaving_soon_days=_positive_int(values, "LEAVING_SOON_DAYS", 30),
            tmdb_enrichment_max_titles_per_run=_positive_int(
                values, "TMDB_ENRICHMENT_MAX_TITLES_PER_RUN", 250
            ),
            tmdb_enrichment_upcoming_refresh_days=_positive_int(
                values, "TMDB_ENRICHMENT_UPCOMING_REFRESH_DAYS", 7
            ),
            tmdb_enrichment_recent_refresh_days=_positive_int(
                values, "TMDB_ENRICHMENT_RECENT_REFRESH_DAYS", 30
            ),
            tmdb_enrichment_series_refresh_days=_positive_int(
                values, "TMDB_ENRICHMENT_SERIES_REFRESH_DAYS", 90
            ),
            tmdb_enrichment_movie_refresh_days=_positive_int(
                values, "TMDB_ENRICHMENT_MOVIE_REFRESH_DAYS", 180
            ),
            tmdb_enrichment_provider_refresh_days=_positive_int(
                values, "TMDB_ENRICHMENT_PROVIDER_REFRESH_DAYS", 60
            ),
        )


def _positive_int(values: Mapping[str, str], name: str, default: int) -> int:
    value = int(values.get(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value
