"""Stable API response contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
