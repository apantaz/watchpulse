from pathlib import Path

import duckdb
import pytest

from ingestion.run import run
from watchpulse.pipeline_runs import PipelineRunRepository, sanitize_error


def _row(database_path: Path, run_id: str) -> tuple:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT status, api_request_count, rows_fetched, rows_inserted,
                   rows_failed, error_message, details_json
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            [run_id],
        ).fetchone()


def test_successful_pipeline_run_is_persisted(tmp_path: Path) -> None:
    database_path = tmp_path / "warehouse.duckdb"
    runs = PipelineRunRepository(database_path)

    runs.start(run_id="run-1", job_name="test", source="tmdb")
    runs.succeed(
        run_id="run-1",
        api_request_count=4,
        rows_fetched=3,
        rows_inserted=3,
        details={"country": "GR"},
    )

    row = _row(database_path, "run-1")
    assert row[:5] == ("success", 4, 3, 3, 0)
    assert row[5] is None
    assert '"country": "GR"' in str(row[6])


def test_failed_pipeline_run_redacts_secrets(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "warehouse.duckdb"
    runs = PipelineRunRepository(database_path)
    secret = "super-secret"  # pragma: allowlist secret

    runs.start(run_id="run-2", job_name="test", source="tmdb")
    error_message = sanitize_error(
        RuntimeError(f"request failed?api_key={secret}"), secrets=(secret,)
    )
    runs.fail(run_id="run-2", api_request_count=2, error_message=error_message)

    row = _row(database_path, "run-2")
    assert row[:5] == ("failed", 2, 0, 0, 1)
    assert secret not in row[5]
    assert "[REDACTED]" in row[5]


def test_ingestion_failure_updates_pipeline_run(tmp_path: Path, monkeypatch) -> None:
    secret = "integration-secret"  # pragma: allowlist secret
    database_path = tmp_path / "warehouse.duckdb"

    class FailingSource:
        request_count = 1

        def __init__(self, api_key: str, **options) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info) -> None:
            pass

        def fetch_titles(self, **kwargs):
            raise RuntimeError(f"upstream rejected api_key={secret}")

    monkeypatch.setattr("ingestion.run.TMDBSource", FailingSource)

    with pytest.raises(RuntimeError, match="upstream rejected"):
        run(
            lake_root=tmp_path / "lake",
            database_path=database_path,
            api_key=secret,
            countries=("GR",),
            providers={"netflix": 8},
            entity_types=("movie",),
        )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT status, api_request_count, error_message FROM pipeline_runs"
        ).fetchone()
    assert row[0:2] == ("failed", 1)
    assert secret not in row[2]
    assert "[REDACTED]" in row[2]
