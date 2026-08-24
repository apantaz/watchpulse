from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb

from ingestion.core.lake import RawRecord, write_raw_batch
from ingestion.enrich_catalog import execute_enrichment, plan_enrichment


def _catalog(path: Path, now: datetime) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute(
            """
            create table main_marts.catalog_availability (
                tmdb_id bigint, content_type varchar, title varchar,
                release_date date, popularity_score double, region varchar,
                provider_key varchar, is_available boolean, is_upcoming boolean,
                available_since timestamptz, poster_path varchar, overview varchar,
                runtime_minutes integer, season_count integer, episode_count integer
            )
            """
        )
        connection.executemany(
            """
            insert into main_marts.catalog_availability
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "tv",
                    "Upcoming",
                    now.date(),
                    10.0,
                    "GR",
                    "netflix",
                    False,
                    True,
                    None,
                    "/1.jpg",
                    "One",
                    None,
                    None,
                    None,
                ),
                (
                    2,
                    "movie",
                    "Popular",
                    date(2000, 1, 1),
                    100.0,
                    "GR",
                    "netflix",
                    True,
                    False,
                    None,
                    "/2.jpg",
                    "Two",
                    None,
                    None,
                    None,
                ),
                (
                    3,
                    "movie",
                    "Retained",
                    date(2000, 1, 1),
                    1.0,
                    "GR",
                    "netflix",
                    True,
                    False,
                    None,
                    "/3.jpg",
                    "Three",
                    90,
                    None,
                    None,
                ),
            ],
        )


def _retain(lake_root: Path, endpoint: str, tmdb_id: int, fetched_at: datetime) -> None:
    write_raw_batch(
        [
            RawRecord(
                request_params={"entity_type": "movie", "tmdb_id": tmdb_id},
                payload={"id": tmdb_id},
                fetched_at=fetched_at,
            )
        ],
        lake_root=lake_root,
        source="tmdb",
        endpoint=endpoint,
        entity_type="mixed",
        country="ALL",
        run_id=f"{endpoint}-{tmdb_id}",
        run_date=fetched_at.date(),
    )


def test_backfill_selects_only_titles_without_retained_payloads(tmp_path: Path) -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    database = tmp_path / "serving.duckdb"
    _catalog(database, now)
    _retain(tmp_path, "metadata", 3, now)
    _retain(tmp_path, "watch_providers", 3, now)

    plan = plan_enrichment(
        database_path=database,
        lake_root=tmp_path,
        mode="backfill",
        max_titles=10,
        as_of=now,
    )

    assert [candidate.tmdb_id for candidate in plan] == [1, 2]
    assert plan[0].reasons[0] == "upcoming"
    assert all(candidate.metadata_due and candidate.providers_due for candidate in plan)


def test_incremental_prioritizes_product_value_and_respects_freshness(tmp_path: Path) -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    database = tmp_path / "serving.duckdb"
    _catalog(database, now)
    _retain(tmp_path, "metadata", 3, now - timedelta(days=10))
    _retain(tmp_path, "watch_providers", 3, now - timedelta(days=10))

    plan = plan_enrichment(
        database_path=database,
        lake_root=tmp_path,
        mode="incremental",
        max_titles=2,
        as_of=now,
    )

    assert [candidate.tmdb_id for candidate in plan] == [1, 2]
    assert plan[0].priority > plan[1].priority


def test_execute_retains_batches_and_counts_requests(tmp_path: Path, monkeypatch) -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    database = tmp_path / "serving.duckdb"
    _catalog(database, now)
    plan = plan_enrichment(
        database_path=database,
        lake_root=tmp_path,
        mode="backfill",
        max_titles=1,
        as_of=now,
    )

    class FakeTMDBSource:
        request_count = 0

        def __init__(self, api_key: str, **_options: str) -> None:
            assert api_key == ""

        def __enter__(self):
            return self

        def __exit__(self, *_exc_info: object) -> None:
            return None

        def fetch_metadata(self, *, entity_type: str, source_title_id: int) -> RawRecord:
            self.request_count += 1
            return RawRecord(
                request_params={"entity_type": entity_type, "tmdb_id": source_title_id},
                payload={"id": source_title_id},
            )

        def fetch_availability(self, *, entity_type: str, source_title_id: int) -> RawRecord:
            self.request_count += 1
            return RawRecord(
                request_params={"entity_type": entity_type, "tmdb_id": source_title_id},
                payload={"id": source_title_id, "results": {}},
            )

    monkeypatch.setattr("ingestion.enrich_catalog.TMDBSource", FakeTMDBSource)
    summary = execute_enrichment(
        plan,
        lake_root=tmp_path,
        api_key="",
        mode="backfill",
    )

    assert summary["api_request_count"] == 2
    assert summary["metadata_records_written"] == 1
    assert summary["provider_records_written"] == 1
    assert len(list(tmp_path.glob("raw/source=tmdb/endpoint=metadata/**/*.parquet"))) == 1
    assert len(list(tmp_path.glob("raw/source=tmdb/endpoint=watch_providers/**/*.parquet"))) == 1
