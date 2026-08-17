# WatchPulse

WatchPulse is a streaming discovery product that helps users decide what to
watch based on their region, streaming services, and preferences. External APIs
populate a local catalog; browsing and filter changes will query WatchPulse's
own data rather than calling upstream APIs.

The MVP will provide region- and provider-aware discovery across four shared,
filterable sections:

- Top 10
- New Releases
- Recently Added
- Upcoming

See [AGENTS.md](AGENTS.md) for the current product requirements and
[docs/architecture.md](docs/architecture.md) for the active architecture and
implementation decisions. `AGENTS.md` remains the authoritative product brief.

Documentation is split by responsibility:

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Architecture decisions](docs/decisions.md)
- [Version roadmap](docs/roadmap.md)

## Project status

Version `v0.2` is complete pending merge. The repository currently includes:

- configurable TMDB discovery by region and provider;
- full movie and TV metadata ingestion;
- TMDB watch-provider ingestion;
- region/provider-scoped streaming lifecycle ingestion;
- append-only lifecycle history and idempotent DuckDB availability state;
- bounded manual ingestion workflow;
- append-only raw Parquet storage;
- retrying and rate-limited HTTP access;
- source-independent content and provider models;
- unit tests that do not make live API calls.

Version `v0.2` adds Movie of the Night's Streaming Availability API v4 and
persistent streaming lifecycle events. Add `STREAMING_AVAILABILITY_API_KEY` only
when running live ingestion; offline tests do not require it. See the
[v0.2 release notes](docs/releases/v0.2.md).

## Requirements

- Python 3.12 recommended (Python 3.10 or newer is required)
- A TMDB v3 API key
- `pyenv` and `pyenv-virtualenv` are optional

Get a TMDB API key from the
[TMDB API settings page](https://www.themoviedb.org/settings/api).

## Development setup

### Option A: pyenv (optional)

Create a local pyenv environment named `watchpulse` if it does not already
exist. `pyenv local` creates an ignored `.python-version` file for your machine:

```bash
pyenv install 3.12.13                 # skip if already installed
pyenv virtualenv 3.12.13 watchpulse   # skip if already created
pyenv local watchpulse
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If you prefer a different Python 3.12 patch release, create the `watchpulse`
environment from that version instead.

### Option B: standard virtual environment

Pyenv is not required. Any supported Python installation can be used:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Configuration

Create a local environment file and add your TMDB key:

```bash
cp .env.example .env
```

```dotenv
TMDB_API_KEY=your_key_here
```

The remaining values in `.env.example` have development defaults. Important
settings include:

- `SUPPORTED_REGIONS`: comma-separated ISO country codes, such as `GR,GB`;
- `SUPPORTED_PROVIDERS`: stable WatchPulse provider keys;
- `LAKE_ROOT`: location of the append-only Parquet lake;
- `DATABASE_PATH`: future DuckDB serving database path;
- discovery windows for new, recently added, and leaving-soon content.

Never commit `.env`; it is ignored by Git.

## Dependency management

`pyproject.toml` is the canonical project configuration. It contains package
metadata, supported Python versions, runtime dependencies, development extras,
and pytest/Ruff settings.

For development, install the editable project and its development tools:

```bash
python -m pip install -e ".[dev]"
```

`requirements.txt` remains as a small compatibility entry point for deployment
services that require that filename. Installing it resolves the project and its
runtime dependencies from `pyproject.toml`, avoiding two manually synchronized
dependency lists:

```bash
python -m pip install -r requirements.txt
```

### Git hooks

After installing the development dependencies, install both repository hooks:

```bash
python -m pre_commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
```

The hooks are intentionally split by cost:

- before commit: direct commits to `main`/`master` are blocked, Ruff checks
  staged Python, and `detect-secrets` scans staged text files;
- before push: the complete offline pytest suite runs.
- commit message: Commitizen enforces Conventional Commits.

Secret detection uses the committed `.secrets.baseline`. If a legitimate test
fixture is detected, audit the finding instead of bypassing the hook:

```bash
detect-secrets audit .secrets.baseline
```

Never add a real credential to the baseline. Rotate it immediately if it was
ever staged or committed.

Run either stage manually when needed:

```bash
python -m pre_commit run --all-files --hook-stage pre-commit
python -m pre_commit run --all-files --hook-stage pre-push
```

Hooks use the active project environment, so run
`python -m pip install -e ".[dev]"` after dependency changes.

Create a guided conventional commit with:

```bash
cz commit
```

Examples of accepted messages are `feat: add provider mapping`,
`fix(ingestion): handle an empty page`, and `docs: update roadmap`. Commitizen
uses the PEP 621 version in `pyproject.toml`; when a version is ready, preview
and apply the semantic bump with:

```bash
cz bump --dry-run
cz bump
```

The bump updates the project version and changelog and creates a `vX.Y.Z` tag.

## Running ingestion

Start with a smoke test. It fetches one discovery page for every configured
region, provider, and entity type, then enriches the discovered titles with
metadata and watch-provider payloads:

```bash
python -m ingestion.run --max-pages 1
```

Run the complete configured catalog ingestion with:

```bash
python -m ingestion.run
```

To override the configured regions for one run, repeat `--country`:

```bash
python -m ingestion.run --country GR --country GB --max-pages 1
```

Raw responses are written beneath:

```text
data/lake/raw/source=tmdb/endpoint=.../entity_type=.../country=.../date=...
```

Each batch creates an immutable Parquet file. Re-running ingestion preserves
the previous raw responses; downstream transformations will deduplicate records
at their documented business grain.

Inspect a readable sample from the locally stored catalog without making new
API calls:

```bash
python -m ingestion.inspect --country GR --limit 20
```

This is a Phase 1 diagnostic over the TMDB subscription-catalog seed. It is not
yet the final lifecycle-aware WatchPulse serving query from `v0.2`/`v0.3`.

Before a full backfill, verify that the configured TMDB provider IDs are still
valid for the selected region:

```bash
python -m ingestion.sources.tmdb.list_providers
```

This command and ingestion require network access and a valid `TMDB_API_KEY`.
The normal test suite does not.

### Streaming lifecycle ingestion (v0.2)

After adding a direct Movie of the Night API key to `.env`, run a one-request
Greece smoke test:

```bash
python -m ingestion.run_streaming_availability \
  --country GR \
  --change-type new \
  --max-requests 1 \
  --max-pages-per-type 1
```

A normal bounded MVP run requests one page each for `new` and `upcoming`:

```bash
python -m ingestion.run_streaming_availability --country GR
```

This costs at most two requests with the default configuration. The client and
event model still support `removed`, `updated`, and `expiring`, but those types
and the Leaving Soon section are deferred beyond the first public release.

Full pagination is opt-in and remains protected by the request ceiling:

```bash
python -m ingestion.run_streaming_availability \
  --country GR \
  --change-type new \
  --all-pages \
  --max-requests 500
```

The manual GitHub workflow uses that full-pagination mode for the four combined
subscription catalogs (`netflix`, `disney_plus`, `prime_video`, and
`apple_tv_plus`). It has no cron trigger, follows both selected cursor chains to
completion, and stops before request attempt 501. Ordinary local runs remain
limited to one page per type unless `--all-pages` is supplied.

The configured monthly cap relies on the DuckDB usage ledger and therefore
applies across runs only where that database persists. Until durable workflow
storage is introduced, each manual GitHub invocation must be treated as having
its own 500-request ceiling.

The runner combines all configured subscription providers per request, writes
raw pages under `data/lake/raw`, writes normalized append-only events under
`data/lake/events`, and records usage in DuckDB. It enforces both the per-run and
calendar-month request limits from `.env`, including retry attempts.

Inspect or replay locally persisted events:

```bash
python -m ingestion.inspect_events --country GR --limit 20
python -m ingestion.replay_events --country GR
```

## Tests

Run all tests from the repository root:

```bash
python -m pytest -q
```

Current tests cover raw-lake writes, HTTP retry behavior, configuration
validation, and translation from TMDB payloads into internal content models.

## Automation

GitHub Actions currently provides:

- `CI`: installs Python 3.12 dependencies, checks syntax, and runs all tests on
  pull requests and pushes to `master`;
- `Manual TMDB ingestion`: runs a bounded, manually triggered ingestion and
  uploads its raw Parquet lake as a seven-day workflow artifact.

To use manual ingestion, add `TMDB_API_KEY` under the repository's Actions
secrets, then choose **Actions → Manual TMDB ingestion → Run workflow**. The
workflow intentionally requires a page limit so an accidental manual run cannot
start an unbounded catalog backfill.

Scheduled ingestion will be enabled in `v0.2`, once incremental lifecycle
ingestion exists. Production continuous deployment will be added in `v0.6`
after the hosting and frontend decisions are recorded; adding a pretend deploy
job before a target exists would not produce a working deployment.

## Repository layout

```text
watchpulse/              Shared configuration and domain models
ingestion/core/          Source contracts, HTTP behavior, and raw-lake writes
ingestion/sources/tmdb/  TMDB client, adapter, and provider configuration
ingestion/tests/         Offline unit tests and fixtures
warehouse/               Planned dbt-duckdb transformation project
api/                     Planned read-only discovery backend
frontend/                Planned guest-first discovery UI
scripts/                 Planned safe operational commands
tests/                   Cross-component and end-to-end tests
.github/workflows/       CI, ingestion automation, and future deployment
docs/                    Architecture documentation
data/                    Local generated data (gitignored)
```

Planned boundaries are `warehouse/` for dbt and DuckDB models, `api/` for the
local query layer, and `frontend/` for discovery UI. The frontend will only call
the WatchPulse API; it will never call TMDB or a streaming availability source.

## Implementation sequence

1. Finish foundation configuration, DuckDB setup, models, and ingestion run
   observability.
2. Add Streaming Availability API ingestion and historical lifecycle events.
3. Build dbt staging, normalized models, and the serving catalog.
4. Add safe parameterized discovery queries and API endpoints.
5. Build the filterable frontend and content details.
6. Add CI, scheduled ingestion, monitoring, and deployment.
7. Add bounded natural-language discovery after deterministic discovery works.

Authentication and personalization are intentionally deferred. Core discovery
will work without an account.
