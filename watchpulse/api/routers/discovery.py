"""Public deterministic discovery routes."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Request

from watchpulse.api.filters import DiscoveryFiltersQuery
from watchpulse.api.models import (
    CatalogItemResponse,
    NewReleasesResponse,
    RankedCatalogItemResponse,
    TopTenResponse,
)
from watchpulse.api.query import AvailabilityState, DiscoveryRequest, DiscoverySort
from watchpulse.api.repository import CatalogRepository

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


def _repository(request: Request) -> CatalogRepository:
    return request.app.state.catalog_repository


@router.get("/top-10", response_model=TopTenResponse)
async def top_ten(request: Request, filters: DiscoveryFiltersQuery) -> TopTenResponse:
    query = DiscoveryRequest(
        filters=filters,
        availability=AvailabilityState.CURRENT,
        sort=DiscoverySort.POPULARITY,
        limit=10,
    )
    items = _repository(request).discover(query)
    ranked_items = tuple(
        RankedCatalogItemResponse(
            rank=rank,
            **CatalogItemResponse.model_validate(item).model_dump(),
        )
        for rank, item in enumerate(items, start=1)
    )
    return TopTenResponse(
        section="top_10",
        filters=filters,
        count=len(ranked_items),
        items=ranked_items,
    )


@router.get("/new-releases", response_model=NewReleasesResponse)
async def new_releases(request: Request, filters: DiscoveryFiltersQuery) -> NewReleasesResponse:
    as_of = date.today()
    window_days = request.app.state.settings.new_release_days
    query = DiscoveryRequest(
        filters=filters,
        availability=AvailabilityState.CURRENT,
        sort=DiscoverySort.RELEASE_DATE,
        limit=20,
        release_date_from=as_of - timedelta(days=window_days),
        release_date_to=as_of,
    )
    items = _repository(request).discover(query)
    return NewReleasesResponse(
        section="new_releases",
        filters=filters,
        as_of=as_of,
        window_days=window_days,
        count=len(items),
        items=tuple(CatalogItemResponse.model_validate(item) for item in items),
    )
