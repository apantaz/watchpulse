from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from watchpulse.warehouse_publish import publish_warehouse, validate_candidate


def _create_candidate(path: Path, catalog_rows: int = 2) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema main_marts")
        connection.execute("create table main_marts.catalog_availability (is_available boolean)")
        connection.executemany(
            "insert into main_marts.catalog_availability values (?)",
            [(True,)] * catalog_rows,
        )
        connection.execute(
            """
            create table main_marts.catalog_freshness as
            select
                'catalog_availability'::varchar as catalog_name,
                current_timestamp as warehouse_built_at,
                current_timestamp as latest_source_updated_at,
                ?::bigint as catalog_row_count,
                ?::bigint as current_row_count,
                0::bigint as upcoming_row_count
            """,
            [catalog_rows, catalog_rows],
        )
        connection.execute("create schema main_intermediate")
        connection.execute(
            """
            create view main_intermediate.int_content as
            select * from main_marts.catalog_availability
            """
        )


def test_publish_replaces_output_only_after_validation(tmp_path: Path) -> None:
    project_dir = tmp_path / "warehouse"
    project_dir.mkdir()
    output_path = tmp_path / "serving.duckdb"
    output_path.write_bytes(b"previous database")

    def runner(command: tuple[str, ...], cwd: Path, environment: dict[str, str]) -> None:
        assert command == ("dbt", "build")
        assert cwd == project_dir
        candidate_path = Path(environment["WATCHPULSE_DBT_PATH"])
        assert candidate_path.name == output_path.name
        assert candidate_path.parent != output_path.parent
        _create_candidate(candidate_path)

    published = publish_warehouse(project_dir, output_path, runner=runner)

    assert published == output_path
    validate_candidate(output_path)
    with duckdb.connect(str(output_path), read_only=True) as connection:
        assert connection.execute(
            "select count(*) from main_intermediate.int_content"
        ).fetchone() == (2,)


def test_failed_build_preserves_previous_output(tmp_path: Path) -> None:
    project_dir = tmp_path / "warehouse"
    project_dir.mkdir()
    output_path = tmp_path / "serving.duckdb"
    original = b"last known good database"
    output_path.write_bytes(original)

    def failing_runner(command: tuple[str, ...], cwd: Path, environment: dict[str, str]) -> None:
        raise RuntimeError("dbt failed")

    with pytest.raises(RuntimeError, match="dbt failed"):
        publish_warehouse(project_dir, output_path, runner=failing_runner)

    assert output_path.read_bytes() == original
    assert not list(tmp_path.glob(".warehouse_candidate_*"))


def test_failed_validation_preserves_previous_output(tmp_path: Path) -> None:
    project_dir = tmp_path / "warehouse"
    project_dir.mkdir()
    output_path = tmp_path / "serving.duckdb"
    original = b"last known good database"
    output_path.write_bytes(original)

    def runner(command: tuple[str, ...], cwd: Path, environment: dict[str, str]) -> None:
        Path(environment["WATCHPULSE_DBT_PATH"]).write_bytes(b"invalid candidate")

    with pytest.raises(duckdb.Error):
        publish_warehouse(project_dir, output_path, runner=runner)

    assert output_path.read_bytes() == original
    assert not list(tmp_path.glob(".warehouse_candidate_*"))
