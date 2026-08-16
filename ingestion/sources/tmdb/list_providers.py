"""One-off helper: print TMDB's current watch-provider ids for GR so the
mapping in config.py can be verified/updated before a real backfill.

Usage: python -m ingestion.sources.tmdb.list_providers
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from ingestion.core.http import RateLimitedClient
from ingestion.sources.tmdb.config import TMDB_BASE_URL


def main() -> None:
    load_dotenv()
    api_key = os.environ["TMDB_API_KEY"]

    with RateLimitedClient(base_url=TMDB_BASE_URL) as client:
        for entity_type in ("movie", "tv"):
            payload = client.get_json(
                f"/watch/providers/{entity_type}",
                params={"api_key": api_key, "watch_region": "GR"},
            )
            print(f"\n{entity_type} providers available in GR:")
            for provider in sorted(payload.get("results", []), key=lambda p: p["provider_name"]):
                print(f"  {provider['provider_id']:>5}  {provider['provider_name']}")


if __name__ == "__main__":
    main()
