"""Read-only access to the published DuckDB serving database."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

from watchpulse.api.filters import CatalogScope
from watchpulse.api.query import DiscoveryQueryBuilder, DiscoveryRequest


class CatalogUnavailableError(RuntimeError):
    """Raised when the published catalog cannot safely serve a request."""


@dataclass(frozen=True)
class CatalogFreshness:
    catalog_name: str
    warehouse_built_at: datetime
    latest_source_updated_at: datetime
    catalog_row_count: int
    current_row_count: int
    upcoming_row_count: int


@dataclass(frozen=True)
class ProviderReference:
    key: str
    name: str


@dataclass(frozen=True)
class GenreReference:
    content_type: str
    id: int
    name: str


@dataclass(frozen=True)
class FilterOptions:
    content_types: tuple[str, ...]
    languages: tuple[str, ...]
    runtime_min: int | None
    runtime_max: int | None
    release_year_min: int | None
    release_year_max: int | None
    rating_min: float | None
    rating_max: float | None


@dataclass(frozen=True)
class CatalogAvailability:
    provider_key: str
    provider_name: str
    monetization_type: str
    available_since: datetime | None
    available_from: datetime | None
    expires_on: datetime | None
    is_available: bool
    is_upcoming: bool
    source: str
    watch_url: str | None = None


@dataclass(frozen=True)
class CatalogItem:
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
    genre_names: tuple[str, ...]
    tmdb_rating: float | None
    vote_count: int | None
    popularity_score: float | None
    poster_path: str | None
    backdrop_path: str | None
    metadata_source: str
    last_updated_at: datetime
    availabilities: tuple[CatalogAvailability, ...]


class CatalogRepository:
    """Repository boundary for local, read-only catalog queries."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def get_freshness(self) -> CatalogFreshness:
        with self._connect() as connection:
            try:
                row = connection.execute(
                    """
                    select
                        catalog_name,
                        warehouse_built_at,
                        latest_source_updated_at,
                        catalog_row_count,
                        current_row_count,
                        upcoming_row_count
                    from main_marts.catalog_freshness
                    """
                ).fetchone()
            except duckdb.Error as error:
                raise CatalogUnavailableError("The serving catalog could not be read") from error

        if row is None:
            raise CatalogUnavailableError("Catalog freshness metadata is missing")

        return CatalogFreshness(*row)

    def list_regions(self) -> tuple[str, ...]:
        rows = self._fetchall(
            "select distinct region from main_marts.catalog_availability order by region"
        )
        return tuple(row[0] for row in rows)

    def list_providers(self, region: str) -> tuple[ProviderReference, ...]:
        rows = self._fetchall(
            """
            select provider_key, provider_name
            from main_marts.catalog_availability
            where region = ?
            group by provider_key, provider_name
            order by provider_name, provider_key
            """,
            [region],
        )
        return tuple(ProviderReference(*row) for row in rows)

    def list_genres(self, scope: CatalogScope) -> tuple[GenreReference, ...]:
        predicates, parameters = self._scope_predicates(scope, alias="catalog")
        rows = self._fetchall(
            f"""
            select genres.content_type, genres.genre_id, genres.genre_name
            from main_marts.catalog_availability as catalog
            inner join main_marts.content_genres as genres
                on catalog.tmdb_id = genres.tmdb_id
                and catalog.content_type = genres.content_type
            where {" and ".join(predicates)}
            group by genres.content_type, genres.genre_id, genres.genre_name
            order by genres.content_type, genres.genre_name, genres.genre_id
            """,  # noqa: S608 -- predicates contain fixed SQL and generated placeholders only.
            parameters,
        )
        return tuple(GenreReference(*row) for row in rows)

    def get_filter_options(self, scope: CatalogScope) -> FilterOptions:
        predicates, parameters = self._scope_predicates(scope)
        where_clause = " and ".join(predicates)
        content_types = self._fetchall(
            f"""
            select distinct content_type
            from main_marts.catalog_availability
            where {where_clause}
            order by content_type
            """,  # noqa: S608 -- predicates contain fixed SQL and generated placeholders only.
            parameters,
        )
        languages = self._fetchall(
            f"""
            select distinct original_language
            from main_marts.catalog_availability
            where {where_clause} and original_language is not null
            order by original_language
            """,  # noqa: S608 -- predicates contain fixed SQL and generated placeholders only.
            parameters,
        )
        ranges = self._fetchone(
            f"""
            select
                min(runtime_minutes), max(runtime_minutes),
                min(release_year), max(release_year),
                min(tmdb_rating), max(tmdb_rating)
            from main_marts.catalog_availability
            where {where_clause}
            """,  # noqa: S608 -- predicates contain fixed SQL and generated placeholders only.
            parameters,
        )
        return FilterOptions(
            content_types=tuple(row[0] for row in content_types),
            languages=tuple(row[0] for row in languages),
            runtime_min=ranges[0],
            runtime_max=ranges[1],
            release_year_min=ranges[2],
            release_year_max=ranges[3],
            rating_min=ranges[4],
            rating_max=ranges[5],
        )

    def discover(self, request: DiscoveryRequest) -> tuple[CatalogItem, ...]:
        query = DiscoveryQueryBuilder().build(request)
        rows = self._fetchall(query.sql, list(query.parameters))
        return tuple(self._catalog_item(row) for row in rows)

    @staticmethod
    def _catalog_item(row: tuple[Any, ...]) -> CatalogItem:
        raw_genres = json.loads(row[9]) if row[9] is not None else []
        availabilities = tuple(CatalogAvailability(**availability) for availability in row[18])
        return CatalogItem(
            tmdb_id=row[0],
            content_type=row[1],
            title=row[2],
            original_title=row[3],
            overview=row[4],
            release_date=row[5],
            release_year=row[6],
            runtime_minutes=row[7],
            original_language=row[8],
            genre_ids=tuple(int(genre_id) for genre_id in raw_genres),
            genre_names=tuple(row[10]),
            tmdb_rating=row[11],
            vote_count=row[12],
            popularity_score=row[13],
            poster_path=row[14],
            backdrop_path=row[15],
            metadata_source=row[16],
            last_updated_at=row[17],
            availabilities=availabilities,
        )

    @staticmethod
    def _scope_predicates(
        scope: CatalogScope, alias: str | None = None
    ) -> tuple[list[str], list[Any]]:
        prefix = f"{alias}." if alias else ""
        predicates = [f"{prefix}region = ?"]
        parameters: list[Any] = [scope.region]
        if scope.providers:
            placeholders = ", ".join("?" for _ in scope.providers)
            predicates.append(f"{prefix}provider_key in ({placeholders})")
            parameters.extend(scope.providers)
        if scope.content_type is not None:
            predicates.append(f"{prefix}content_type = ?")
            parameters.append(scope.content_type.value)
        return predicates, parameters

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if not self.database_path.is_file():
            raise CatalogUnavailableError("The serving catalog is not available")
        try:
            return duckdb.connect(str(self.database_path), read_only=True)
        except duckdb.Error as error:
            raise CatalogUnavailableError("The serving catalog could not be read") from error

    def _fetchall(self, query: str, parameters: list[Any] | None = None) -> list[tuple[Any, ...]]:
        with self._connect() as connection:
            try:
                return connection.execute(query, parameters or []).fetchall()
            except duckdb.Error as error:
                raise CatalogUnavailableError("The serving catalog could not be read") from error

    def _fetchone(self, query: str, parameters: list[Any]) -> tuple[Any, ...]:
        with self._connect() as connection:
            try:
                row = connection.execute(query, parameters).fetchone()
            except duckdb.Error as error:
                raise CatalogUnavailableError("The serving catalog could not be read") from error
        if row is None:
            raise CatalogUnavailableError("The serving catalog returned no result")
        return row
