from __future__ import annotations

import asyncio
import socket
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import httpx
import pytest
from fastapi import FastAPI

from watchpulse.api import create_app
from watchpulse.api.repository import CatalogRepository


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


def _catalog_row(
    *,
    tmdb_id: int,
    region: str,
    provider_key: str,
    provider_name: str,
    is_available: bool = True,
    is_upcoming: bool = False,
    release_date: date | None,
    runtime: int | None = 90,
    language: str | None = "en",
    genre_ids: str | None = "[35]",
    rating: float | None = 8.0,
    popularity: float | None = 10.0,
    available_since: datetime | None = None,
    available_from: datetime | None = None,
    expires_on: datetime | None = None,
) -> tuple[object, ...]:
    return (
        tmdb_id,
        "movie",
        f"Title {tmdb_id}",
        f"Title {tmdb_id}",
        f"Overview {tmdb_id}",
        release_date,
        release_date.year if release_date else None,
        runtime,
        language,
        genre_ids,
        rating,
        100,
        popularity,
        region,
        provider_key,
        provider_name,
        "subscription",
        available_since,
        available_from,
        expires_on,
        is_available,
        is_upcoming,
        f"/{tmdb_id}.jpg",
        f"/{tmdb_id}-bg.jpg",
        "tmdb" if is_available else "streaming_availability",
        "tmdb_discovery" if is_available else "streaming_availability",
        datetime.now(UTC),
        "https://www.netflix.com/title/example" if provider_key == "netflix" else None,
        None,
        None,
    )


def _create_catalog(path: Path) -> None:
    now = datetime.now(UTC)
    today = now.date()
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute(
            """
            create table main_marts.catalog_availability (
                tmdb_id bigint, content_type varchar, title varchar,
                original_title varchar, overview varchar, release_date date,
                release_year integer, runtime_minutes integer,
                original_language varchar, genre_ids json, tmdb_rating double,
                vote_count bigint, popularity_score double, region varchar,
                provider_key varchar, provider_name varchar,
                monetization_type varchar, available_since timestamptz,
                available_from timestamptz, expires_on timestamptz,
                is_available boolean, is_upcoming boolean, poster_path varchar,
                backdrop_path varchar, metadata_source varchar,
                availability_source varchar, last_updated_at timestamptz,
                watch_url varchar, episode_count integer, season_count integer
            )
            """
        )
        rows = [
            _catalog_row(
                tmdb_id=1,
                region="GR",
                provider_key="netflix",
                provider_name="Netflix",
                release_date=today - timedelta(days=10),
                available_since=now - timedelta(days=2),
                expires_on=now + timedelta(days=5),
            ),
            _catalog_row(
                tmdb_id=2,
                region="GR",
                provider_key="netflix",
                provider_name="Netflix",
                release_date=today - timedelta(days=500),
                runtime=150,
                language="fr",
                genre_ids="[28]",
                rating=5.0,
                popularity=20.0,
                available_since=now - timedelta(days=100),
            ),
            _catalog_row(
                tmdb_id=3,
                region="GR",
                provider_key="netflix",
                provider_name="Netflix",
                is_available=False,
                is_upcoming=True,
                release_date=today,
                available_from=now + timedelta(days=3),
            ),
            _catalog_row(
                tmdb_id=4,
                region="US",
                provider_key="netflix",
                provider_name="Netflix",
                release_date=today - timedelta(days=10),
                available_since=now - timedelta(days=2),
                expires_on=now + timedelta(days=5),
            ),
            _catalog_row(
                tmdb_id=5,
                region="GR",
                provider_key="disney_plus",
                provider_name="Disney+",
                release_date=today - timedelta(days=10),
                available_since=now - timedelta(days=2),
                expires_on=now + timedelta(days=5),
            ),
        ]
        placeholders = ", ".join("?" for _ in rows[0])
        connection.executemany(
            f"insert into main_marts.catalog_availability values ({placeholders})",
            rows,
        )
        connection.execute(
            """
            create table main_marts.content_genres (
                tmdb_id bigint,
                content_type varchar,
                genre_id integer,
                genre_name varchar
            )
            """
        )
        connection.executemany(
            "insert into main_marts.content_genres values (?, 'movie', ?, ?)",
            [
                (1, 35, "Comedy"),
                (2, 28, "Action"),
                (3, 35, "Comedy"),
                (4, 35, "Comedy"),
                (5, 35, "Comedy"),
            ],
        )
        connection.execute(
            """
            create table main_marts.catalog_freshness as
            select
                'catalog_availability'::varchar as catalog_name,
                current_timestamp as warehouse_built_at,
                current_timestamp as latest_source_updated_at,
                count(*)::bigint as catalog_row_count,
                count_if(is_available)::bigint as current_row_count,
                count_if(is_upcoming)::bigint as upcoming_row_count
            from main_marts.catalog_availability
            """
        )


@pytest.fixture
def catalog_app(tmp_path: Path) -> FastAPI:
    database_path = tmp_path / "serving.duckdb"
    _create_catalog(database_path)
    return create_app(repository=CatalogRepository(database_path))


def _shared_filters() -> list[tuple[str, str]]:
    current_year = date.today().year
    return [
        ("region", "GR"),
        ("providers", "netflix"),
        ("content_type", "movie"),
        ("genre_ids", "35"),
        ("runtime_max", "100"),
        ("release_year_from", str(current_year)),
        ("release_year_to", str(current_year)),
        ("rating_min", "7"),
        ("language", "en"),
    ]


def test_all_sections_apply_the_same_global_filters(catalog_app: FastAPI) -> None:
    expected_ids = {
        "/api/v1/discovery/top-10": [1],
        "/api/v1/discovery/new-releases": [1],
        "/api/v1/discovery/recently-added": [1],
        "/api/v1/discovery/leaving-soon": [1],
        "/api/v1/discovery/upcoming": [3],
    }

    for path, expected in expected_ids.items():
        response = _get(catalog_app, path, _shared_filters())
        assert response.status_code == 200, path
        assert [item["tmdb_id"] for item in response.json()["items"]] == expected, path


def test_region_and_provider_never_leak_across_http_routes(catalog_app: FastAPI) -> None:
    greek_netflix = _get(
        catalog_app,
        "/api/v1/discovery/top-10",
        [("region", "GR"), ("providers", "netflix")],
    )
    american_netflix = _get(
        catalog_app,
        "/api/v1/discovery/top-10",
        [("region", "US"), ("providers", "netflix")],
    )
    greek_disney = _get(
        catalog_app,
        "/api/v1/discovery/top-10",
        [("region", "GR"), ("providers", "disney_plus")],
    )

    assert {item["tmdb_id"] for item in greek_netflix.json()["items"]} == {1, 2}
    assert [item["tmdb_id"] for item in american_netflix.json()["items"]] == [4]
    assert [item["tmdb_id"] for item in greek_disney.json()["items"]] == [5]


def test_api_exposes_verified_watch_urls_with_scoped_availability(
    catalog_app: FastAPI,
) -> None:
    response = _get(
        catalog_app,
        "/api/v1/discovery/top-10",
        [("region", "GR"), ("providers", "netflix")],
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["availabilities"][0]["watch_url"] == (
        "https://www.netflix.com/title/example"
    )


def test_frontend_like_requests_make_zero_network_connections(
    catalog_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a local API request attempted an external connection")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    assert _get(catalog_app, "/api/v1/catalog/regions").status_code == 200
    assert (
        _get(
            catalog_app,
            "/api/v1/discovery/top-10",
            [("region", "GR"), ("providers", "netflix")],
        ).status_code
        == 200
    )
    assert (
        _get(
            catalog_app,
            "/api/v1/discovery/titles/movie/1",
            [("region", "GR"), ("providers", "netflix")],
        ).status_code
        == 200
    )


def test_discovery_errors_are_validated_and_sanitized(tmp_path: Path) -> None:
    invalid = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))
    missing = _get(
        invalid,
        "/api/v1/discovery/top-10",
        [("region", "GR"), ("providers", "netflix")],
    )
    injection = _get(
        invalid,
        "/api/v1/discovery/top-10",
        [("region", "GR"), ("providers", "netflix') union select 1 --")],
    )

    assert missing.status_code == 503
    assert missing.json() == {"detail": "The serving catalog is not available"}
    assert str(tmp_path) not in missing.text
    assert injection.status_code == 422


def test_openapi_contains_the_complete_v04_contract(catalog_app: FastAPI) -> None:
    schema = _get(catalog_app, "/openapi.json").json()
    required_paths = {
        "/health",
        "/api/v1/catalog/freshness",
        "/api/v1/catalog/regions",
        "/api/v1/catalog/providers",
        "/api/v1/catalog/genres",
        "/api/v1/catalog/filter-options",
        "/api/v1/discovery/top-10",
        "/api/v1/discovery/new-releases",
        "/api/v1/discovery/recently-added",
        "/api/v1/discovery/upcoming",
        "/api/v1/discovery/leaving-soon",
        "/api/v1/discovery/titles/{content_type}/{tmdb_id}",
    }

    assert required_paths <= set(schema["paths"])
    assert schema["info"]["version"] == "0.4.0"
