from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from watchpulse.api.filters import ContentType, DiscoveryFilters, DiscoveryFiltersQuery


def _filter_app() -> FastAPI:
    app = FastAPI()

    @app.get("/discover")
    async def discover(filters: DiscoveryFiltersQuery) -> DiscoveryFilters:
        return filters

    return app


def _get(params: list[tuple[str, str]]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=_filter_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/discover", params=params)

    return asyncio.run(request())


def test_normalizes_and_deduplicates_global_filters() -> None:
    filters = DiscoveryFilters(
        region=" gr ",
        providers=("Netflix", "netflix", "Disney_Plus"),
        content_type="movie",
        genre_ids=(35, 35, 18),
        language=" EL ",
    )

    assert filters.region == "GR"
    assert filters.providers == ("netflix", "disney_plus")
    assert filters.content_type is ContentType.MOVIE
    assert filters.genre_ids == (35, 18)
    assert filters.language == "el"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("region", "GRC"),
        ("providers", ()),
        ("providers", ("disney-plus",)),
        ("content_type", "series"),
        ("genre_ids", (0,)),
        ("runtime_max", 0),
        ("rating_min", 10.1),
        ("language", "greek"),
    ],
)
def test_rejects_invalid_filter_values(field: str, value: object) -> None:
    values: dict[str, object] = {"region": "GR", "providers": ("netflix",)}
    values[field] = value

    with pytest.raises(ValidationError):
        DiscoveryFilters.model_validate(values)


def test_rejects_reversed_release_year_range() -> None:
    with pytest.raises(ValidationError, match="release_year_from"):
        DiscoveryFilters(
            region="GR",
            providers=("netflix",),
            release_year_from=2025,
            release_year_to=2020,
        )


def test_fastapi_binds_repeated_query_parameters() -> None:
    response = _get(
        [
            ("region", "gr"),
            ("providers", "netflix"),
            ("providers", "disney_plus"),
            ("content_type", "tv"),
            ("genre_ids", "18"),
            ("genre_ids", "35"),
            ("runtime_max", "120"),
            ("release_year_from", "2020"),
            ("release_year_to", "2026"),
            ("rating_min", "7.5"),
            ("language", "EL"),
        ]
    )

    assert response.status_code == 200
    assert response.json() == {
        "region": "GR",
        "providers": ["netflix", "disney_plus"],
        "content_type": "tv",
        "genre_ids": [18, 35],
        "runtime_max": 120,
        "release_year_from": 2020,
        "release_year_to": 2026,
        "rating_min": 7.5,
        "language": "el",
    }


def test_fastapi_returns_422_for_invalid_or_unknown_filters() -> None:
    invalid = _get([("region", "GR"), ("providers", "netflix"), ("rating_min", "11")])
    unknown = _get([("region", "GR"), ("providers", "netflix"), ("raw_sql", "true")])

    assert invalid.status_code == 422
    assert unknown.status_code == 422
