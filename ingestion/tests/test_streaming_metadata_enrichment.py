from pathlib import Path

from ingestion.core.lake import RawRecord, write_raw_batch
from ingestion.enrich_streaming_metadata import pending_title_refs, run


def _streaming_event(lake_root: Path) -> None:
    write_raw_batch(
        [
            RawRecord(
                request_params={"country": "GR"},
                payload={
                    "shows": {
                        "one": {"tmdbId": "movie/101", "title": "One"},
                        "two": {"tmdbId": "tv/202", "title": "Two"},
                    }
                },
            )
        ],
        lake_root=lake_root,
        source="streaming_availability",
        endpoint="changes_upcoming",
        entity_type="show",
        country="GR",
        run_id="events",
    )


def test_pending_title_refs_excludes_retained_tmdb_metadata(tmp_path: Path) -> None:
    _streaming_event(tmp_path)
    write_raw_batch(
        [
            RawRecord(
                request_params={"entity_type": "movie", "tmdb_id": 101},
                payload={"id": 101, "title": "One"},
            )
        ],
        lake_root=tmp_path,
        source="tmdb",
        endpoint="metadata",
        entity_type="movie",
        country="ALL",
        run_id="metadata",
    )

    assert pending_title_refs(tmp_path, country="GR") == (("tv", 202),)


def test_run_fetches_only_pending_lifecycle_metadata(tmp_path: Path, monkeypatch) -> None:
    _streaming_event(tmp_path)

    class FakeTMDBSource:
        request_count = 0

        def __init__(self, api_key: str, **options: str) -> None:
            assert api_key == ""

        def __enter__(self):
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def fetch_metadata(self, *, entity_type: str, source_title_id: int) -> RawRecord:
            self.request_count += 1
            return RawRecord(
                request_params={"entity_type": entity_type, "tmdb_id": source_title_id},
                payload={"id": source_title_id, "title": str(source_title_id)},
            )

        def fetch_availability(self, *, entity_type: str, source_title_id: int) -> RawRecord:
            self.request_count += 1
            return RawRecord(
                request_params={"entity_type": entity_type, "tmdb_id": source_title_id},
                payload={"id": source_title_id, "results": {}},
            )

    monkeypatch.setattr(
        "ingestion.enrich_streaming_metadata.TMDBSource",
        FakeTMDBSource,
    )

    summary = run(
        lake_root=tmp_path,
        api_key="",
        country="GR",
        max_titles=1,
        include_watch_providers=True,
    )

    assert summary["metadata_titles_requested"] == 1
    assert summary["availability_titles_requested"] == 1
    assert summary["metadata_records_written"] == 1
    assert summary["availability_records_written"] == 1
    assert summary["api_request_count"] == 2
    assert (
        len(
            list(
                tmp_path.glob(
                    "raw/source=tmdb/endpoint=metadata/entity_type=mixed/country=ALL/date=*/*.parquet"
                )
            )
        )
        == 1
    )
    assert (
        len(
            list(
                tmp_path.glob(
                    "raw/source=tmdb/endpoint=watch_providers/entity_type=mixed/country=ALL/date=*/*.parquet"
                )
            )
        )
        == 1
    )
