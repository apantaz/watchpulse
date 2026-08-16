import json
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from ingestion.core.lake import RawRecord, raw_partition_dir, write_raw_batch


def test_write_raw_batch_writes_partitioned_parquet(tmp_path: Path) -> None:
    records = [
        RawRecord(request_params={"page": 1}, payload={"results": [{"id": 1}]}),
        RawRecord(request_params={"page": 2}, payload={"results": [{"id": 2}]}),
    ]

    written = write_raw_batch(
        records,
        lake_root=tmp_path,
        source="tmdb",
        endpoint="discover_netflix",
        entity_type="movie",
        country="GR",
        run_id="testrun",
        run_date=date(2026, 8, 16),
    )

    assert written is not None
    assert written.exists()

    expected_dir = raw_partition_dir(
        lake_root=tmp_path,
        source="tmdb",
        endpoint="discover_netflix",
        entity_type="movie",
        country="GR",
        run_date=date(2026, 8, 16),
    )
    assert written.parent == expected_dir

    table = pq.read_table(written)
    assert table.num_rows == 2
    payloads = [json.loads(p) for p in table.column("payload").to_pylist()]
    assert payloads[0]["results"][0]["id"] == 1
    assert payloads[1]["results"][0]["id"] == 2


def test_write_raw_batch_skips_empty_records(tmp_path: Path) -> None:
    result = write_raw_batch(
        [],
        lake_root=tmp_path,
        source="tmdb",
        endpoint="discover_netflix",
        entity_type="movie",
        country="GR",
        run_id="testrun",
    )
    assert result is None


def test_write_raw_batch_never_collides_across_calls(tmp_path: Path) -> None:
    record = [RawRecord(request_params={}, payload={"ok": True})]
    first = write_raw_batch(
        record,
        lake_root=tmp_path,
        source="tmdb",
        endpoint="discover_netflix",
        entity_type="movie",
        country="GR",
        run_id="samerun",
        run_date=date(2026, 8, 16),
    )
    second = write_raw_batch(
        record,
        lake_root=tmp_path,
        source="tmdb",
        endpoint="discover_netflix",
        entity_type="movie",
        country="GR",
        run_id="samerun",
        run_date=date(2026, 8, 16),
    )
    assert first != second
    assert first.exists() and second.exists()
