import json
from pathlib import Path

import duckdb

from ingestion.core.lake import RawRecord
from ingestion.run import run


class FakeTMDBSource:
    instances = []
    total_pages = 2

    def __init__(self, api_key: str, **options) -> None:
        self.request_count = 0
        self.metadata_ids = []
        self.availability_ids = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        pass

    def fetch_titles(self, **kwargs):
        for page, tmdb_id in ((1, 101), (2, 202)):
            self.request_count += 1
            yield RawRecord(
                request_params={"page": page},
                payload={
                    "page": page,
                    "total_pages": self.total_pages,
                    "total_results": 2,
                    "results": [{"id": tmdb_id}],
                },
            )

    def fetch_metadata(self, *, source_title_id: int, **kwargs):
        self.request_count += 1
        self.metadata_ids.append(source_title_id)
        return RawRecord(request_params={}, payload={"id": source_title_id})

    def fetch_availability(self, *, source_title_id: int, **kwargs):
        self.request_count += 1
        self.availability_ids.append(source_title_id)
        return RawRecord(request_params={}, payload={"id": source_title_id})


def test_discovery_only_is_default_and_reports_complete_query(tmp_path: Path, monkeypatch) -> None:
    FakeTMDBSource.instances.clear()
    FakeTMDBSource.total_pages = 2
    monkeypatch.setattr("ingestion.run.TMDBSource", FakeTMDBSource)

    summary = run(
        lake_root=tmp_path / "lake",
        database_path=tmp_path / "warehouse.duckdb",
        api_key="test-key",  # pragma: allowlist secret
        countries=("GR",),
        providers={"netflix": 8},
        entity_types=("movie",),
    )

    source = FakeTMDBSource.instances[-1]
    assert summary["api_request_count"] == 2
    assert summary["discovery_complete"] is True
    assert summary["enrichment_enabled"] is False
    assert summary["metadata_records_written"] == 0
    assert summary["availability_records_written"] == 0
    assert source.metadata_ids == []
    assert source.availability_ids == []
    assert summary["discovery_queries"] == [
        {
            "country": "GR",
            "provider_key": "netflix",
            "content_type": "movie",
            "upstream_total_pages": 2,
            "expected_pages": 2,
            "pages_fetched": 2,
            "total_results": 2,
            "complete": True,
            "truncated_by_source_limit": False,
        }
    ]
    manifests = list(
        (tmp_path / "lake").glob("raw/source=tmdb/endpoint=discovery_manifest/**/*.parquet")
    )
    assert len(manifests) == 1
    payload = json.loads(
        duckdb.connect()
        .execute("select cast(payload as json) from read_parquet(?)", [[str(manifests[0])]])
        .fetchone()[0]
    )
    assert payload["run_id"] == summary["run_id"]
    assert payload["discovery_complete"] is True


def test_bounded_discovery_is_partial_and_enrichment_is_opt_in(tmp_path: Path, monkeypatch) -> None:
    FakeTMDBSource.instances.clear()
    FakeTMDBSource.total_pages = 2
    monkeypatch.setattr("ingestion.run.TMDBSource", FakeTMDBSource)

    summary = run(
        lake_root=tmp_path / "lake",
        api_key="test-key",  # pragma: allowlist secret
        countries=("GR",),
        providers={"netflix": 8},
        entity_types=("movie",),
        max_pages=1,
        enrich=True,
    )

    source = FakeTMDBSource.instances[-1]
    assert summary["discovery_complete"] is False
    assert summary["discovery_queries"][0]["pages_fetched"] == 1
    assert summary["enrichment_enabled"] is True
    assert source.metadata_ids == [101]
    assert source.availability_ids == [101]
    assert summary["api_request_count"] == 3


def test_catalog_over_source_page_limit_is_never_complete(tmp_path: Path, monkeypatch) -> None:
    FakeTMDBSource.instances.clear()
    FakeTMDBSource.total_pages = 501
    monkeypatch.setattr("ingestion.run.TMDBSource", FakeTMDBSource)

    summary = run(
        lake_root=tmp_path / "lake",
        api_key="test-key",  # pragma: allowlist secret
        countries=("GR",),
        providers={"netflix": 8},
        entity_types=("movie",),
        max_pages=1,
    )

    query = summary["discovery_queries"][0]
    assert query["expected_pages"] == 500
    assert query["truncated_by_source_limit"] is True
    assert query["complete"] is False
