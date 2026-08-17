from datetime import date
from pathlib import Path

from ingestion.core.lake import RawRecord, write_raw_batch
from ingestion.inspect import read_catalog_sample


def test_read_catalog_sample_filters_country_and_sorts(tmp_path: Path) -> None:
    for country, popularity in (("GR", 10.0), ("US", 100.0)):
        write_raw_batch(
            [
                RawRecord(
                    request_params={"page": 1},
                    payload={
                        "results": [
                            {
                                "id": 597,
                                "title": "Titanic",
                                "release_date": "1997-12-19",
                                "popularity": popularity,
                            }
                        ]
                    },
                )
            ],
            lake_root=tmp_path,
            source="tmdb",
            endpoint="discover_netflix",
            entity_type="movie",
            country=country,
            run_id=f"test-{country}",
            run_date=date(2026, 8, 17),
        )

    results = read_catalog_sample(lake_root=tmp_path, country="GR", limit=10)

    assert len(results) == 1
    assert results[0].provider == "netflix"
    assert results[0].title == "Titanic"
    assert results[0].popularity == 10.0
