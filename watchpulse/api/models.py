"""Stable API response contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from watchpulse.api.filters import DiscoveryFilters


class HealthResponse(BaseModel):
    """Process liveness response that does not depend on the catalog."""

    status: str


class CatalogFreshnessResponse(BaseModel):
    """Freshness and validated row counts for the published catalog."""

    model_config = ConfigDict(from_attributes=True)

    catalog_name: str
    warehouse_built_at: datetime
    latest_source_updated_at: datetime
    catalog_row_count: int
    current_row_count: int
    upcoming_row_count: int


class RegionOption(BaseModel):
    code: str


class RegionsResponse(BaseModel):
    regions: tuple[RegionOption, ...]


class ProviderOption(BaseModel):
    key: str
    name: str


class ProvidersResponse(BaseModel):
    region: str
    providers: tuple[ProviderOption, ...]


class GenreOption(BaseModel):
    content_type: str
    id: int
    name: str


class GenresResponse(BaseModel):
    genres: tuple[GenreOption, ...]


class IntegerRange(BaseModel):
    minimum: int | None
    maximum: int | None


class NumberRange(BaseModel):
    minimum: float | None
    maximum: float | None


class FilterOptionsResponse(BaseModel):
    content_types: tuple[str, ...]
    languages: tuple[str, ...]
    runtime_minutes: IntegerRange
    release_year: IntegerRange
    rating: NumberRange


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider_key: str
    provider_name: str
    monetization_type: str
    available_since: datetime | None
    available_from: datetime | None
    expires_on: datetime | None
    is_available: bool
    is_upcoming: bool
    source: str


class CatalogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tmdb_id: int
    content_type: str
    title: str
    original_title: str | None
    overview: str | None
    release_date: date | None
    release_year: int | None
    runtime_minutes: int | None
    original_language: str | None
    genre_ids: tuple[int, ...]
    tmdb_rating: float | None
    vote_count: int | None
    popularity_score: float | None
    poster_path: str | None
    backdrop_path: str | None
    metadata_source: str
    last_updated_at: datetime
    availabilities: tuple[AvailabilityResponse, ...]


class RankedCatalogItemResponse(CatalogItemResponse):
    rank: int


class TopTenResponse(BaseModel):
    section: Literal["top_10"]
    filters: DiscoveryFilters
    count: int
    items: tuple[RankedCatalogItemResponse, ...]


class NewReleasesResponse(BaseModel):
    section: Literal["new_releases"]
    filters: DiscoveryFilters
    as_of: date
    window_days: int
    count: int
    items: tuple[CatalogItemResponse, ...]


class RecentlyAddedResponse(BaseModel):
    section: Literal["recently_added"]
    filters: DiscoveryFilters
    as_of: datetime
    window_days: int
    count: int
    items: tuple[CatalogItemResponse, ...]


class UpcomingResponse(BaseModel):
    section: Literal["upcoming"]
    filters: DiscoveryFilters
    as_of: datetime
    count: int
    items: tuple[CatalogItemResponse, ...]


class LeavingSoonResponse(BaseModel):
    section: Literal["leaving_soon"]
    filters: DiscoveryFilters
    as_of: datetime
    window_days: int
    count: int
    items: tuple[CatalogItemResponse, ...]
