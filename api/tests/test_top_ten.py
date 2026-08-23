from __future__ import annotations

import asyncio
from datetime import date, datetime

import httpx
from fastapi import FastAPI

from watchpulse.api import create_app
from watchpulse.api.query import AvailabilityState, DiscoveryRequest, DiscoverySort
from watchpulse.api.repository import CatalogAvailability, CatalogItem, CatalogRepository


class FakeRepository(CatalogRepository):
    def __init__(self, items: tuple[CatalogItem, ...] = ()) -> None:
        self.items = items
        self.request: DiscoveryRequest | None = None

    def discover(self, request: DiscoveryRequest) -> tuple[CatalogItem, ...]:
        self.request = request
        return self.items


def _get(
    app: FastAPI,
    path: str,
    params: list[tuple[str, str]] | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params=params)

    return asyncio.run(request())


def _item(tmdb_id: int, title: str, popularity: float) -> CatalogItem:
    return CatalogItem(
        tmdb_id=tmdb_id,
        content_type="movie",
        title=title,
        original_title=title,
        overview="Overview",
        release_date=date(2024, 1, 1),
        release_year=2024,
        runtime_minutes=100,
        original_language="en",
        genre_ids=(35,),
        tmdb_rating=7.5,
        vote_count=100,
        popularity_score=popularity,
        poster_path="/poster.jpg",
        backdrop_path="/backdrop.jpg",
        metadata_source="tmdb",
        last_updated_at=datetime(2026, 8, 23, 12, 0),
        availabilities=(
            CatalogAvailability(
                provider_key="netflix",
                provider_name="Netflix",
                monetization_type="subscription",
                available_since=datetime(2026, 8, 1),
                available_from=None,
                expires_on=None,
                is_available=True,
                is_upcoming=False,
                source="tmdb",
            ),
        ),
    )


def test_top_ten_returns_ranked_catalog_items() -> None:
    repository = FakeRepository((_item(1, "First", 20), _item(2, "Second", 10)))
    app = create_app(repository=repository)

    response = _get(
        app,
        "/api/v1/discovery/top-10",
        [("region", "gr"), ("providers", "Netflix")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["section"] == "top_10"
    assert payload["filters"]["region"] == "GR"
    assert payload["filters"]["providers"] == ["netflix"]
    assert payload["count"] == 2
    assert [(item["rank"], item["title"]) for item in payload["items"]] == [
        (1, "First"),
        (2, "Second"),
    ]
    assert payload["items"][0]["availabilities"][0]["provider_key"] == "netflix"


def test_top_ten_uses_fixed_current_popularity_request() -> None:
    repository = FakeRepository()
    app = create_app(repository=repository)

    response = _get(
        app,
        "/api/v1/discovery/top-10",
        [
            ("region", "GR"),
            ("providers", "netflix"),
            ("content_type", "movie"),
            ("genre_ids", "35"),
            ("runtime_max", "100"),
            ("release_year_from", "2020"),
            ("rating_min", "7"),
            ("language", "en"),
        ],
    )

    assert response.status_code == 200
    assert repository.request is not None
    assert repository.request.availability is AvailabilityState.CURRENT
    assert repository.request.sort is DiscoverySort.POPULARITY
    assert repository.request.limit == 10
    assert repository.request.offset == 0
    assert repository.request.filters.genre_ids == (35,)
    assert repository.request.filters.runtime_max == 100


def test_top_ten_requires_region_and_provider() -> None:
    app = create_app(repository=FakeRepository())

    response = _get(app, "/api/v1/discovery/top-10")

    assert response.status_code == 422


def test_top_ten_filter_contract_is_visible_in_openapi() -> None:
    app = create_app(repository=FakeRepository())

    schema = _get(app, "/openapi.json").json()
    operation = schema["paths"]["/api/v1/discovery/top-10"]["get"]
    parameters = {parameter["name"] for parameter in operation["parameters"]}

    assert parameters == {
        "region",
        "providers",
        "content_type",
        "genre_ids",
        "runtime_max",
        "release_year_from",
        "release_year_to",
        "rating_min",
        "language",
    }
