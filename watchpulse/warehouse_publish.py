"""Build, validate, and atomically publish the dbt serving warehouse."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

import duckdb

CommandRunner = Callable[[Sequence[str], Path, dict[str, str]], None]
CandidateValidator = Callable[[Path], None]


def run_command(command: Sequence[str], cwd: Path, environment: dict[str, str]) -> None:
    """Run one required publication command."""
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def validate_candidate(candidate_path: Path) -> None:
    """Reject a candidate without a consistent, non-empty serving catalog."""
    with duckdb.connect(str(candidate_path), read_only=True) as connection:
        actual_row_count = connection.execute(
            "select count(*) from main_marts.catalog_availability"
        ).fetchone()[0]
        freshness_rows = connection.execute(
            """
            select
                catalog_row_count,
                current_row_count,
                upcoming_row_count,
                warehouse_built_at,
                latest_source_updated_at
            from main_marts.catalog_freshness
            where catalog_name = 'catalog_availability'
            """
        ).fetchall()

    if len(freshness_rows) != 1:
        raise ValueError("Candidate must contain exactly one catalog freshness row")

    catalog_count, current_count, upcoming_count, built_at, source_updated_at = freshness_rows[0]
    if actual_row_count <= 0 or catalog_count != actual_row_count:
        raise ValueError("Candidate catalog is empty or its recorded count is invalid")
    if current_count + upcoming_count != catalog_count:
        raise ValueError("Candidate availability-state counts are inconsistent")
    if built_at is None or source_updated_at is None:
        raise ValueError("Candidate freshness timestamps must not be null")


def publish_warehouse(
    project_dir: Path,
    output_path: Path,
    *,
    install_dependencies: bool = False,
    runner: CommandRunner = run_command,
    validator: CandidateValidator = validate_candidate,
) -> Path:
    """Build a candidate and atomically replace the serving file on success."""
    project_dir = project_dir.resolve(strict=True)
    output_path = output_path.resolve()
    if output_path.suffix != ".duckdb":
        raise ValueError("Published warehouse path must end with .duckdb")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, candidate_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f"{output_path.stem}_candidate_",
        suffix=".duckdb",
    )
    os.close(descriptor)
    candidate_path = Path(candidate_name)
    candidate_path.unlink()

    environment = os.environ.copy()
    environment["WATCHPULSE_DBT_PATH"] = str(candidate_path)

    try:
        if install_dependencies:
            runner(("dbt", "deps"), project_dir, environment)
        runner(("dbt", "build"), project_dir, environment)
        validator(candidate_path)
        os.replace(candidate_path, output_path)
        return output_path
    finally:
        candidate_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("warehouse"),
        help="dbt project directory (default: warehouse)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.getenv("WATCHPULSE_SERVING_DB_PATH", "data/warehouse_serving.duckdb")),
        help="published serving database path (or WATCHPULSE_SERVING_DB_PATH)",
    )
    parser.add_argument(
        "--deps",
        action="store_true",
        help="run dbt deps before building the candidate",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    published_path = publish_warehouse(
        arguments.project_dir,
        arguments.output,
        install_dependencies=arguments.deps,
    )
    print(f"Published serving warehouse: {published_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
