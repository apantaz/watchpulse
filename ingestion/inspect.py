"""Print a human-readable sample from the locally ingested TMDB catalog."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
from dotenv import load_dotenv


@dataclass(frozen=True)
class CatalogTitle:
    provider: str
    content_type: str
    tmdb_id: int
    title: str
    release_date: str | None
    popularity: float


def read_catalog_sample(*, lake_root: Path, country: str, limit: int = 20) -> list[CatalogTitle]:
    """Read and deduplicate discover results already stored in the raw lake."""
    country = country.upper()
    pattern = (
        f"raw/source=tmdb/endpoint=discover_*/entity_type=*/country={country}/date=*/*.parquet"
    )
    titles: dict[tuple[str, str, int], CatalogTitle] = {}

    for path in sorted(lake_root.glob(pattern)):
        partitions = _partitions(path)
        provider = partitions["endpoint"].removeprefix("discover_")
        content_type = partitions["entity_type"]
        table = pq.read_table(path, columns=["payload"])
        for raw_payload in table.column("payload").to_pylist():
            payload = json.loads(raw_payload)
            for result in payload.get("results", []):
                tmdb_id = int(result["id"])
                title = result.get("title") or result.get("name") or f"TMDB {tmdb_id}"
                release_date = result.get("release_date") or result.get("first_air_date")
                item = CatalogTitle(
                    provider=provider,
                    content_type=content_type,
                    tmdb_id=tmdb_id,
                    title=title,
                    release_date=release_date or None,
                    popularity=float(result.get("popularity") or 0),
                )
                key = (provider, content_type, tmdb_id)
                existing = titles.get(key)
                if existing is None or item.popularity > existing.popularity:
                    titles[key] = item

    return sorted(titles.values(), key=lambda item: item.popularity, reverse=True)[:limit]


def _partitions(path: Path) -> dict[str, str]:
    return {
        key: value
        for part in path.parts
        if "=" in part
        for key, value in [part.split("=", maxsplit=1)]
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default="GR", help="ISO alpha-2 region")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--lake-root", default=os.environ.get("LAKE_ROOT", "data/lake"))
    args = parser.parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")

    titles = read_catalog_sample(
        lake_root=Path(args.lake_root), country=args.country, limit=args.limit
    )
    if not titles:
        raise SystemExit(
            f"No local TMDB discover data found for {args.country.upper()}. Run ingestion first."
        )

    print(f"Current subscription catalog sample for {args.country.upper()} (TMDB seed)\n")
    for position, item in enumerate(titles, start=1):
        release = item.release_date or "unknown date"
        print(
            f"{position:>2}. {item.title} | {item.provider} | "
            f"{item.content_type} | {release} | popularity {item.popularity:g}"
        )


if __name__ == "__main__":
    main()
