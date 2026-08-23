"""Public deterministic discovery routes."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Request

from watchpulse.api.filters import DiscoveryFiltersQuery
from watchpulse.api.models import (
    CatalogItemResponse,
    LeavingSoonResponse,
    NewReleasesResponse,
    RankedCatalogItemResponse,
    RecentlyAddedResponse,
    TopTenResponse,
    UpcomingResponse,
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


@router.get("/recently-added", response_model=RecentlyAddedResponse)
async def recently_added(request: Request, filters: DiscoveryFiltersQuery) -> RecentlyAddedResponse:
    as_of = datetime.now(UTC)
    window_days = request.app.state.settings.recently_added_days
    query = DiscoveryRequest(
        filters=filters,
        availability=AvailabilityState.CURRENT,
        sort=DiscoverySort.RECENTLY_ADDED,
        limit=20,
        available_since_from=as_of - timedelta(days=window_days),
        available_since_to=as_of,
    )
    items = _repository(request).discover(query)
    return RecentlyAddedResponse(
        section="recently_added",
        filters=filters,
        as_of=as_of,
        window_days=window_days,
        count=len(items),
        items=tuple(CatalogItemResponse.model_validate(item) for item in items),
    )


@router.get("/upcoming", response_model=UpcomingResponse)
async def upcoming(request: Request, filters: DiscoveryFiltersQuery) -> UpcomingResponse:
    as_of = datetime.now(UTC)
    query = DiscoveryRequest(
        filters=filters,
        availability=AvailabilityState.UPCOMING,
        sort=DiscoverySort.AVAILABLE_FROM,
        limit=20,
        available_from_after=as_of,
    )
    items = _repository(request).discover(query)
    return UpcomingResponse(
        section="upcoming",
        filters=filters,
        as_of=as_of,
        count=len(items),
        items=tuple(CatalogItemResponse.model_validate(item) for item in items),
    )


@router.get("/leaving-soon", response_model=LeavingSoonResponse)
async def leaving_soon(request: Request, filters: DiscoveryFiltersQuery) -> LeavingSoonResponse:
    as_of = datetime.now(UTC)
    window_days = request.app.state.settings.leaving_soon_days
    query = DiscoveryRequest(
        filters=filters,
        availability=AvailabilityState.CURRENT,
        sort=DiscoverySort.EXPIRATION,
        limit=20,
        expires_from=as_of,
        expires_to=as_of + timedelta(days=window_days),
    )
    items = _repository(request).discover(query)
    return LeavingSoonResponse(
        section="leaving_soon",
        filters=filters,
        as_of=as_of,
        window_days=window_days,
        count=len(items),
        items=tuple(CatalogItemResponse.model_validate(item) for item in items),
    )
