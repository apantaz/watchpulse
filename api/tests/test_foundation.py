from __future__ import annotations

import asyncio
from pathlib import Path

import duckdb
import httpx
import pytest
from fastapi import FastAPI

from watchpulse.api import create_app
from watchpulse.api.repository import CatalogRepository
from watchpulse.config import Settings


def _get(app: FastAPI, path: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(request())


def _options(app: FastAPI, path: str, origin: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        }
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.options(path, headers=headers)

    return asyncio.run(request())


def _create_catalog(path: Path) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute(
            """
            create table main_marts.catalog_freshness as
            select
                'catalog_availability'::varchar as catalog_name,
                timestamp '2026-08-21 12:00:00' as warehouse_built_at,
                timestamp '2026-08-21 11:30:00' as latest_source_updated_at,
                190::bigint as catalog_row_count,
                160::bigint as current_row_count,
                30::bigint as upcoming_row_count
            """
        )


def test_health_does_not_require_a_catalog(tmp_path: Path) -> None:
    app = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))

    response = _get(app, "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_freshness_reads_the_published_catalog(tmp_path: Path) -> None:
    database_path = tmp_path / "serving.duckdb"
    _create_catalog(database_path)
    app = create_app(repository=CatalogRepository(database_path))

    response = _get(app, "/api/v1/catalog/freshness")

    assert response.status_code == 200
    assert response.json() == {
        "catalog_name": "catalog_availability",
        "warehouse_built_at": "2026-08-21T12:00:00",
        "latest_source_updated_at": "2026-08-21T11:30:00",
        "catalog_row_count": 190,
        "current_row_count": 160,
        "upcoming_row_count": 30,
    }


def test_repository_opens_duckdb_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "serving.duckdb"
    _create_catalog(database_path)
    connect = duckdb.connect

    def checked_connect(database: str, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        assert read_only is True
        return connect(database, read_only=read_only)

    monkeypatch.setattr(duckdb, "connect", checked_connect)

    assert CatalogRepository(database_path).get_freshness().catalog_row_count == 190


def test_freshness_returns_503_without_a_catalog(tmp_path: Path) -> None:
    app = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))

    response = _get(app, "/api/v1/catalog/freshness")

    assert response.status_code == 503
    assert response.json() == {"detail": "The serving catalog is not available"}


def test_settings_configure_the_serving_database_path() -> None:
    settings = Settings.from_env(
        {
            "SUPPORTED_REGIONS": "GR",
            "WATCHPULSE_SERVING_DB_PATH": "/tmp/watchpulse-api.duckdb",
        }
    )

    assert settings.serving_database_path == Path("/tmp/watchpulse-api.duckdb")


def test_local_frontend_origin_can_read_the_api(tmp_path: Path) -> None:
    app = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))

    response = _options(app, "/health", "http://127.0.0.1:5173")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_openapi_documents_the_foundation_endpoints(tmp_path: Path) -> None:
    app = create_app(repository=CatalogRepository(tmp_path / "missing.duckdb"))

    schema = _get(app, "/openapi.json").json()

    assert "/health" in schema["paths"]
    assert "/api/v1/catalog/freshness" in schema["paths"]
