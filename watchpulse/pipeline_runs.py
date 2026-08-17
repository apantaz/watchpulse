"""Durable operational metadata for scheduled pipeline executions."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

_REDACTIONS = (
    (re.compile(r"(?i)(api[_-]?key=)[^&\s]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"), r"\1[REDACTED]"),
)


def sanitize_error(error: BaseException, *, secrets: Iterable[str] = ()) -> str:
    """Return a bounded error summary suitable for persistent logs."""
    message = f"{type(error).__name__}: {error}"
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    for pattern, replacement in _REDACTIONS:
        message = pattern.sub(replacement, message)
    return message[:2000]


class PipelineRunRepository:
    """Owns the small DuckDB table used for ingestion observability."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self._database_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id VARCHAR PRIMARY KEY,
                    job_name VARCHAR NOT NULL,
                    source VARCHAR NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    finished_at TIMESTAMPTZ,
                    status VARCHAR NOT NULL,
                    api_request_count INTEGER NOT NULL DEFAULT 0,
                    rows_fetched BIGINT NOT NULL DEFAULT 0,
                    rows_inserted BIGINT NOT NULL DEFAULT 0,
                    rows_updated BIGINT NOT NULL DEFAULT 0,
                    rows_failed BIGINT NOT NULL DEFAULT 0,
                    error_message VARCHAR,
                    details_json JSON
                )
                """
            )

    def start(self, *, run_id: str, job_name: str, source: str) -> None:
        self.initialize()
        with duckdb.connect(str(self._database_path)) as connection:
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, job_name, source, started_at, status
                ) VALUES (?, ?, ?, ?, 'running')
                """,
                [run_id, job_name, source, datetime.now(timezone.utc)],
            )

    def succeed(
        self,
        *,
        run_id: str,
        api_request_count: int,
        rows_fetched: int,
        rows_inserted: int,
        details: dict[str, Any],
    ) -> None:
        self._finish(
            run_id=run_id,
            status="success",
            api_request_count=api_request_count,
            rows_fetched=rows_fetched,
            rows_inserted=rows_inserted,
            rows_failed=0,
            error_message=None,
            details=details,
        )

    def fail(
        self,
        *,
        run_id: str,
        api_request_count: int,
        error_message: str,
    ) -> None:
        self._finish(
            run_id=run_id,
            status="failed",
            api_request_count=api_request_count,
            rows_fetched=0,
            rows_inserted=0,
            rows_failed=1,
            error_message=error_message,
            details={},
        )

    def _finish(
        self,
        *,
        run_id: str,
        status: str,
        api_request_count: int,
        rows_fetched: int,
        rows_inserted: int,
        rows_failed: int,
        error_message: str | None,
        details: dict[str, Any],
    ) -> None:
        with duckdb.connect(str(self._database_path)) as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = ?,
                    status = ?,
                    api_request_count = ?,
                    rows_fetched = ?,
                    rows_inserted = ?,
                    rows_failed = ?,
                    error_message = ?,
                    details_json = ?
                WHERE run_id = ?
                """,
                [
                    datetime.now(timezone.utc),
                    status,
                    api_request_count,
                    rows_fetched,
                    rows_inserted,
                    rows_failed,
                    error_message,
                    json.dumps(details, sort_keys=True),
                    run_id,
                ],
            )
