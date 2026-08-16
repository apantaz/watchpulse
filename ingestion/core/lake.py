"""Writes to the raw Parquet lake.

Per docs/architecture.md #10/#11: the raw layer stores API responses close
to verbatim (one immutable file per ingestion batch, partitioned by
source/endpoint/entity_type/country/date) so schema drift in the upstream
API never breaks ingestion, and every day can be safely replayed.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pyarrow as pa
import pyarrow.parquet as pq


@dataclass(frozen=True)
class RawRecord:
    """One API response, kept close to verbatim."""

    request_params: dict[str, Any]
    payload: dict[str, Any]
    fetched_at: datetime | None = None

    def fetched_at_iso(self) -> str:
        return (self.fetched_at or datetime.now(timezone.utc)).isoformat()


def raw_partition_dir(
    *, lake_root: Path, source: str, endpoint: str, entity_type: str, country: str, run_date: date
) -> Path:
    return (
        lake_root
        / "raw"
        / f"source={source}"
        / f"endpoint={endpoint}"
        / f"entity_type={entity_type}"
        / f"country={country}"
        / f"date={run_date.isoformat()}"
    )


def write_raw_batch(
    records: Sequence[RawRecord],
    *,
    lake_root: Path,
    source: str,
    endpoint: str,
    entity_type: str,
    country: str,
    run_id: str,
    run_date: date | None = None,
) -> Path | None:
    """Appends one immutable Parquet file to the raw lake. Never overwrites
    an existing file — safe to call repeatedly across retried/replayed runs.
    """
    if not records:
        return None

    run_date = run_date or datetime.now(timezone.utc).date()
    partition_dir = raw_partition_dir(
        lake_root=lake_root,
        source=source,
        endpoint=endpoint,
        entity_type=entity_type,
        country=country,
        run_date=run_date,
    )
    partition_dir.mkdir(parents=True, exist_ok=True)

    table = pa.table(
        {
            "fetched_at": [r.fetched_at_iso() for r in records],
            "request_params": [json.dumps(r.request_params, sort_keys=True) for r in records],
            "payload": [json.dumps(r.payload) for r in records],
        }
    )

    file_path = partition_dir / f"part-{run_id}-{uuid.uuid4().hex[:8]}.parquet"
    pq.write_table(table, file_path)
    return file_path
