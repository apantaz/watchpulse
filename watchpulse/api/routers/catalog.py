"""Catalog reference-data routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from watchpulse.api.filters import CatalogScopeQuery
from watchpulse.api.models import (
    FilterOptionsResponse,
    GenreOption,
    GenresResponse,
    IntegerRange,
    NumberRange,
    ProviderOption,
    ProvidersResponse,
    RegionOption,
    RegionsResponse,
)
from watchpulse.api.repository import CatalogRepository

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


def _repository(request: Request) -> CatalogRepository:
    return request.app.state.catalog_repository


@router.get("/regions", response_model=RegionsResponse)
async def regions(request: Request) -> RegionsResponse:
    values = _repository(request).list_regions()
    return RegionsResponse(regions=tuple(RegionOption(code=value) for value in values))


@router.get("/providers", response_model=ProvidersResponse)
async def providers(
    request: Request,
    region: str = Query(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"),
) -> ProvidersResponse:
    normalized_region = region.upper()
    values = _repository(request).list_providers(normalized_region)
    return ProvidersResponse(
        region=normalized_region,
        providers=tuple(ProviderOption(key=value.key, name=value.name) for value in values),
    )


@router.get("/genres", response_model=GenresResponse)
async def genres(request: Request, scope: CatalogScopeQuery) -> GenresResponse:
    values = _repository(request).list_genres(scope)
    return GenresResponse(
        genres=tuple(
            GenreOption(content_type=value.content_type, id=value.id, name=value.name)
            for value in values
        )
    )


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def filter_options(request: Request, scope: CatalogScopeQuery) -> FilterOptionsResponse:
    values = _repository(request).get_filter_options(scope)
    return FilterOptionsResponse(
        content_types=values.content_types,
        languages=values.languages,
        runtime_minutes=IntegerRange(minimum=values.runtime_min, maximum=values.runtime_max),
        release_year=IntegerRange(
            minimum=values.release_year_min,
            maximum=values.release_year_max,
        ),
        rating=NumberRange(minimum=values.rating_min, maximum=values.rating_max),
    )
