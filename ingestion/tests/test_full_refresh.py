from pathlib import Path
from types import SimpleNamespace

from ingestion.full_refresh import run_full_refresh


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        tmdb_api_key="tmdb-key",  # pragma: allowlist secret
        tmdb_base_url="https://tmdb.test",
        streaming_availability_api_key="streaming-key",  # pragma: allowlist secret
        streaming_availability_base_url="https://streaming.test",
        streaming_availability_monthly_cap=1000,
        lake_root=tmp_path / "lake",
        database_path=tmp_path / "ops.duckdb",
        serving_database_path=tmp_path / "serving.duckdb",
        tmdb_enrichment_upcoming_refresh_days=7,
        tmdb_enrichment_recent_refresh_days=30,
        tmdb_enrichment_series_refresh_days=90,
        tmdb_enrichment_movie_refresh_days=180,
        tmdb_enrichment_provider_refresh_days=60,
    )


def test_full_refresh_runs_mandatory_discovery_and_two_atomic_publications(
    tmp_path: Path, monkeypatch
) -> None:
    publications = []
    monkeypatch.setattr(
        "ingestion.full_refresh.run_tmdb_discovery",
        lambda **kwargs: {
            "run_id": "discovery",
            "discovery_complete": True,
            "api_request_count": 2,
            "discover_pages_written": 2,
        },
    )
    monkeypatch.setattr(
        "ingestion.full_refresh.publish_warehouse",
        lambda project, output: publications.append((project, output)),
    )

    summary = run_full_refresh(
        settings=_settings(tmp_path),
        country="gr",
        provider_keys=("netflix",),
        streaming_max_requests=100,
        enrichment_max_titles=10,
        include_watch_providers=False,
        enrichment_mode="incremental",
        run_streaming=False,
        run_enrichment=False,
    )

    assert summary["country"] == "GR"
    assert summary["stages"]["tmdb_discovery"]["run_id"] == "discovery"
    assert len(publications) == 2


def test_incomplete_discovery_is_never_published(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "ingestion.full_refresh.run_tmdb_discovery",
        lambda **kwargs: {"run_id": "partial", "discovery_complete": False},
    )
    monkeypatch.setattr(
        "ingestion.full_refresh.publish_warehouse",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not publish")),
    )

    try:
        run_full_refresh(
            settings=_settings(tmp_path),
            country="GR",
            provider_keys=("netflix",),
            streaming_max_requests=100,
            enrichment_max_titles=10,
            include_watch_providers=False,
            enrichment_mode="incremental",
            run_streaming=False,
            run_enrichment=False,
        )
    except RuntimeError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("incomplete discovery should fail")
