"""Append-only Parquet persistence for normalized streaming lifecycle events."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq

from watchpulse.models import ContentType, MonetizationType, StreamingEvent, StreamingEventType


def write_streaming_events(
    events: list[StreamingEvent],
    *,
    lake_root: Path,
    source: str,
    region: str,
    run_id: str,
    run_date: date | None = None,
) -> Path | None:
    if not events:
        return None

    observed_date = run_date or datetime.now(timezone.utc).date()
    partition = (
        lake_root
        / "events"
        / f"source={source}"
        / f"region={region.upper()}"
        / f"date={observed_date.isoformat()}"
    )
    partition.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[Any]] = {
        "event_id": [],
        "tmdb_id": [],
        "content_type": [],
        "region": [],
        "provider_key": [],
        "monetization_type": [],
        "event_type": [],
        "event_date": [],
        "available_from": [],
        "expires_on": [],
        "source": [],
        "source_event_id": [],
        "ingested_at": [],
    }
    for event in events:
        for field in rows:
            rows[field].append(getattr(event, field))

    path = partition / f"part-{run_id}-{uuid.uuid4().hex[:8]}.parquet"
    pq.write_table(pa.table(rows), path)
    return path


def read_streaming_events(*, lake_root: Path, source: str, region: str) -> list[StreamingEvent]:
    pattern = f"events/source={source}/region={region.upper()}/date=*/*.parquet"
    events = []
    for path in sorted(lake_root.glob(pattern)):
        for row in pq.read_table(path).to_pylist():
            events.append(
                StreamingEvent(
                    event_id=str(row["event_id"]),
                    tmdb_id=int(row["tmdb_id"]),
                    content_type=cast(ContentType, row["content_type"]),
                    region=str(row["region"]),
                    provider_key=str(row["provider_key"]),
                    monetization_type=cast(MonetizationType, row["monetization_type"]),
                    event_type=cast(StreamingEventType, row["event_type"]),
                    event_date=row["event_date"],
                    available_from=row["available_from"],
                    expires_on=row["expires_on"],
                    source=str(row["source"]),
                    source_event_id=row["source_event_id"],
                    ingested_at=row["ingested_at"],
                )
            )
    return events
