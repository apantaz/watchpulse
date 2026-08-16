# WatchPulse

Curated, country- and provider-aware discovery of new streaming releases. See [docs/architecture.md](docs/architecture.md) for the full design (problem statement, domain model, data flow, and phased implementation plan).

Current status: **Phase 1** — TMDB ingestion for Greece into the raw Parquet lake. Phases 2+ (dbt marts, ranking, API, Streamlit frontend, orchestration) are not built yet; see `docs/architecture.md#25` for the plan.

## Setup

```bash
python -m venv .venv
./.venv/Scripts/activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env       # fill in TMDB_API_KEY
```

Get a TMDB v3 API key at https://www.themoviedb.org/settings/api.

## Running ingestion

```bash
# Quick smoke test: one discover page per provider/entity_type, so it
# finishes in seconds instead of pulling the full GR catalog.
python -m ingestion.run --max-pages 1

# Full run for the configured launch countries/providers (see
# ingestion/sources/tmdb/config.py).
python -m ingestion.run
```

Output lands under `data/lake/raw/...` (gitignored — this is a local stand-in for the object storage described in the architecture doc). Every run is append-only and safe to re-run.

Before a real backfill, double check the provider-id mapping in `ingestion/sources/tmdb/config.py` is still current:

```bash
python -m ingestion.sources.tmdb.list_providers
```

## Tests

```bash
pytest ingestion/tests -q
```
