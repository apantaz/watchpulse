from __future__ import annotations

import asyncio
from pathlib import Path

import duckdb
import httpx
from fastapi import FastAPI

from watchpulse.api import create_app
from watchpulse.api.repository import CatalogRepository


def _get(app: FastAPI, path: str, params: list[tuple[str, str]] | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params=params)

    return asyncio.run(request())


def _create_catalog(path: Path) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute(
            """
            create table main_marts.catalog_availability (
                tmdb_id bigint,
                content_type varchar,
                region varchar,
                provider_key varchar,
                provider_name varchar,
                runtime_minutes integer,
                release_year integer,
                tmdb_rating double,
                original_language varchar
            )
            """
        )
        connection.executemany(
            "insert into main_marts.catalog_availability values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "movie", "GR", "netflix", "Netflix", 90, 2024, 7.5, "en"),
                (2, "tv", "GR", "disney_plus", "Disney+", 45, 2022, 8.0, "el"),
                (3, "movie", "US", "netflix", "Netflix", 110, 2020, 6.0, "fr"),
            ],
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
            "insert into main_marts.content_genres values (?, ?, ?, ?)",
            [
                (1, "movie", 35, "Comedy"),
                (2, "tv", 18, "Drama"),
                (3, "movie", 28, "Action"),
            ],
        )


def _app(tmp_path: Path) -> FastAPI:
    database_path = tmp_path / "serving.duckdb"
    _create_catalog(database_path)
    return create_app(repository=CatalogRepository(database_path))


def test_lists_catalog_regions(tmp_path: Path) -> None:
    response = _get(_app(tmp_path), "/api/v1/catalog/regions")

    assert response.status_code == 200
    assert response.json() == {"regions": [{"code": "GR"}, {"code": "US"}]}


def test_lists_only_providers_available_in_the_region(tmp_path: Path) -> None:
    app = _app(tmp_path)

    greek = _get(app, "/api/v1/catalog/providers", [("region", "gr")])
    american = _get(app, "/api/v1/catalog/providers", [("region", "US")])

    assert greek.json() == {
        "region": "GR",
        "providers": [
            {"key": "disney_plus", "name": "Disney+"},
            {"key": "netflix", "name": "Netflix"},
        ],
    }
    assert american.json() == {
        "region": "US",
        "providers": [{"key": "netflix", "name": "Netflix"}],
    }


def test_genres_respect_region_provider_and_content_type(tmp_path: Path) -> None:
    response = _get(
        _app(tmp_path),
        "/api/v1/catalog/genres",
        [
            ("region", "GR"),
            ("providers", "disney_plus"),
            ("content_type", "tv"),
        ],
    )

    assert response.status_code == 200
    assert response.json() == {"genres": [{"content_type": "tv", "id": 18, "name": "Drama"}]}


def test_filter_options_are_scoped_to_the_selected_catalog(tmp_path: Path) -> None:
    response = _get(
        _app(tmp_path),
        "/api/v1/catalog/filter-options",
        [("region", "GR")],
    )

    assert response.status_code == 200
    assert response.json() == {
        "content_types": ["movie", "tv"],
        "languages": ["el", "en"],
        "runtime_minutes": {"minimum": 45, "maximum": 90},
        "release_year": {"minimum": 2022, "maximum": 2024},
        "rating": {"minimum": 7.5, "maximum": 8.0},
    }


def test_empty_scope_returns_empty_options_and_null_ranges(tmp_path: Path) -> None:
    response = _get(
        _app(tmp_path),
        "/api/v1/catalog/filter-options",
        [("region", "DE")],
    )

    assert response.status_code == 200
    assert response.json() == {
        "content_types": [],
        "languages": [],
        "runtime_minutes": {"minimum": None, "maximum": None},
        "release_year": {"minimum": None, "maximum": None},
        "rating": {"minimum": None, "maximum": None},
    }


def test_reference_filters_reject_unknown_fields_and_sql_input(tmp_path: Path) -> None:
    app = _app(tmp_path)

    unknown = _get(
        app,
        "/api/v1/catalog/genres",
        [("region", "GR"), ("raw_sql", "true")],
    )
    injection = _get(
        app,
        "/api/v1/catalog/genres",
        [("region", "GR"), ("providers", "netflix') or true --")],
    )

    assert unknown.status_code == 422
    assert injection.status_code == 422


def test_reference_endpoint_returns_503_without_catalog(tmp_path: Path) -> None:
    app = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))

    response = _get(app, "/api/v1/catalog/regions")

    assert response.status_code == 503
    assert response.json() == {"detail": "The serving catalog is not available"}
