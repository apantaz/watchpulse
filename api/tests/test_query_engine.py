from __future__ import annotations

import socket
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from watchpulse.api.filters import DiscoveryFilters
from watchpulse.api.query import (
    AvailabilityState,
    DiscoveryQueryBuilder,
    DiscoveryRequest,
    DiscoverySort,
)
from watchpulse.api.repository import CatalogRepository


def _create_catalog(path: Path) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute(
            """
            create table main_marts.catalog_availability (
                tmdb_id bigint,
                content_type varchar,
                title varchar,
                original_title varchar,
                overview varchar,
                release_date date,
                release_year integer,
                runtime_minutes integer,
                original_language varchar,
                genre_ids json,
                tmdb_rating double,
                vote_count bigint,
                popularity_score double,
                region varchar,
                provider_key varchar,
                provider_name varchar,
                monetization_type varchar,
                available_since timestamp,
                available_from timestamp,
                expires_on timestamp,
                is_available boolean,
                is_upcoming boolean,
                poster_path varchar,
                backdrop_path varchar,
                metadata_source varchar,
                availability_source varchar,
                last_updated_at timestamp
            )
            """
        )
        rows = [
            (
                1,
                "movie",
                "Comedy",
                "Comedy",
                "Funny",
                date(2024, 1, 1),
                2024,
                100,
                "en",
                "[35, 18]",
                7.0,
                100,
                10.0,
                "GR",
                "netflix",
                "Netflix",
                "subscription",
                datetime(2026, 8, 1),
                None,
                None,
                True,
                False,
                "/1.jpg",
                "/1-bg.jpg",
                "tmdb",
                "tmdb",
                datetime(2026, 8, 20),
            ),
            (
                1,
                "movie",
                "Comedy",
                "Comedy",
                "Funny",
                date(2024, 1, 1),
                2024,
                100,
                "en",
                "[35, 18]",
                7.0,
                100,
                10.0,
                "GR",
                "disney_plus",
                "Disney+",
                "subscription",
                datetime(2026, 8, 2),
                None,
                None,
                True,
                False,
                "/1.jpg",
                "/1-bg.jpg",
                "tmdb",
                "tmdb",
                datetime(2026, 8, 21),
            ),
            (
                2,
                "movie",
                "Action",
                "Action",
                "Fast",
                date(2020, 1, 1),
                2020,
                120,
                "fr",
                "[28]",
                8.0,
                200,
                20.0,
                "GR",
                "netflix",
                "Netflix",
                "subscription",
                datetime(2026, 7, 1),
                None,
                None,
                True,
                False,
                "/2.jpg",
                None,
                "tmdb",
                "tmdb",
                datetime(2026, 8, 19),
            ),
            (
                3,
                "movie",
                "US only",
                "US only",
                None,
                date(2025, 1, 1),
                2025,
                90,
                "en",
                "[35]",
                9.0,
                300,
                30.0,
                "US",
                "netflix",
                "Netflix",
                "subscription",
                datetime(2026, 8, 1),
                None,
                None,
                True,
                False,
                None,
                None,
                "tmdb",
                "tmdb",
                datetime(2026, 8, 21),
            ),
            (
                4,
                "tv",
                "Coming soon",
                "Coming soon",
                None,
                None,
                2026,
                45,
                None,
                None,
                None,
                None,
                None,
                "GR",
                "netflix",
                "Netflix",
                "subscription",
                None,
                datetime(2026, 9, 1),
                None,
                False,
                True,
                None,
                None,
                "streaming_availability",
                "streaming_availability",
                datetime(2026, 8, 22),
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
            "insert into main_marts.content_genres values (?, ?, ?, ?)",
            [
                (1, "movie", 35, "Comedy"),
                (1, "movie", 18, "Drama"),
                (2, "movie", 28, "Action"),
                (3, "movie", 35, "Comedy"),
            ],
        )


def _repository(tmp_path: Path) -> CatalogRepository:
    path = tmp_path / "serving.duckdb"
    _create_catalog(path)
    return CatalogRepository(path)


def test_query_builder_binds_every_user_value() -> None:
    filters = DiscoveryFilters(
        region="GR",
        providers=("netflix", "disney_plus"),
        content_type="movie",
        genre_ids=(35,),
        runtime_max=100,
        release_year_from=2020,
        release_year_to=2024,
        rating_min=7,
        language="en",
    )

    query = DiscoveryQueryBuilder().build(DiscoveryRequest(filters, limit=10, offset=5))

    assert "netflix" not in query.sql
    assert "disney_plus" not in query.sql
    assert query.parameters == (
        "GR",
        "netflix",
        "disney_plus",
        "movie",
        35,
        100,
        2020,
        2024,
        7.0,
        "en",
        10,
        5,
    )


def test_applies_all_global_filters_with_inclusive_boundaries(tmp_path: Path) -> None:
    filters = DiscoveryFilters(
        region="GR",
        providers=("netflix",),
        content_type="movie",
        genre_ids=(35,),
        runtime_max=100,
        release_year_from=2024,
        release_year_to=2024,
        rating_min=7,
        language="en",
    )

    items = _repository(tmp_path).discover(DiscoveryRequest(filters))

    assert [item.tmdb_id for item in items] == [1]


def test_aggregates_selected_providers_into_one_title(tmp_path: Path) -> None:
    filters = DiscoveryFilters(region="GR", providers=("netflix", "disney_plus"))

    items = _repository(tmp_path).discover(DiscoveryRequest(filters))
    comedy = next(item for item in items if item.tmdb_id == 1)

    assert [availability.provider_key for availability in comedy.availabilities] == [
        "disney_plus",
        "netflix",
    ]
    assert comedy.last_updated_at == datetime(2026, 8, 21)


def test_region_and_availability_state_never_leak(tmp_path: Path) -> None:
    filters = DiscoveryFilters(region="GR", providers=("netflix",))
    repository = _repository(tmp_path)

    current = repository.discover(DiscoveryRequest(filters))
    upcoming = repository.discover(
        DiscoveryRequest(filters, availability=AvailabilityState.UPCOMING)
    )

    assert {item.tmdb_id for item in current} == {1, 2}
    assert [item.tmdb_id for item in upcoming] == [4]


def test_multiple_genres_match_any_selected_genre(tmp_path: Path) -> None:
    filters = DiscoveryFilters(
        region="GR",
        providers=("netflix",),
        genre_ids=(35, 28),
    )

    items = _repository(tmp_path).discover(DiscoveryRequest(filters))

    assert {item.tmdb_id for item in items} == {1, 2}


def test_controlled_sort_and_pagination(tmp_path: Path) -> None:
    filters = DiscoveryFilters(region="GR", providers=("netflix",))
    request = DiscoveryRequest(
        filters,
        sort=DiscoverySort.POPULARITY,
        limit=1,
        offset=1,
    )

    items = _repository(tmp_path).discover(request)

    assert [item.tmdb_id for item in items] == [1]


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (101, 0), (20, -1)])
def test_rejects_unsafe_pagination(limit: int, offset: int) -> None:
    filters = DiscoveryFilters(region="GR", providers=("netflix",))

    with pytest.raises(ValueError):
        DiscoveryRequest(filters, limit=limit, offset=offset)


def test_discovery_never_uses_the_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("discovery attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    filters = DiscoveryFilters(region="GR", providers=("netflix",))

    assert _repository(tmp_path).discover(DiscoveryRequest(filters))
