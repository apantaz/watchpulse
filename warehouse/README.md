# Warehouse

Active `dbt-duckdb` project introduced in `v0.3`.

Ownership:

- read immutable source data from `data/lake`;
- build staging, intermediate, and mart models;
- enforce the contracts in `docs/data-model.md`;
- build a candidate DuckDB file and publish it only after tests pass.

This component must not call external APIs.

## Project layout

```text
warehouse/
├── analyses/       Read-only compiled analytical queries
├── docs/
│   ├── staging/    models.md and columns.md
│   ├── intermediate/ models.md and columns.md
│   └── marts/      models.md and columns.md
├── macros/         Reusable Jinja/dbt logic
├── models/
│   ├── staging/    Typed source-facing tables
│   ├── intermediate/ Reusable business transformations
│   └── marts/      Serving tables
├── seeds/          Small version-controlled reference data
├── snapshots/      Future slowly changing source history
├── tests/          Singular cross-row/business tests
├── dbt_project.yml Project paths and materialization defaults
├── packages.yml    Pinned reusable dbt packages
├── profiles.yml    Local DuckDB target
└── selectors.yml   Named build selections
```

All dbt configuration and resources live in this directory.

Every database object must have a model description, documented grain, owner,
source, and descriptions/data types for every exposed column. Supported
adapters persist those descriptions into relations and columns.

Each model layer has a matching folder under `warehouse/docs`: `models.md`
contains relation-level dbt doc blocks and `columns.md` contains reusable
column-level doc blocks. The `docs-paths` setting points to that dedicated root.

## Setup

Install the warehouse dependency group:

```bash
python -m pip install -e ".[dev,warehouse]"
```

## Build

Enter the warehouse directory before running dbt:

```bash
cd warehouse
```

Then validate the installation and connection without additional flags:

```bash
dbt debug
```

Parse and build the project with:

```bash
dbt parse
dbt build
```

Remove generated targets, downloaded packages, and dbt logs with:

```bash
dbt clean
```

Install or refresh the pinned dbt packages before the first build and whenever
`packages.yml` changes:

```bash
dbt deps
```

Reusable data-quality assertions live beside their models in schema YAML. The
project uses `dbt-utils` for structural tests and `dbt-expectations` for value
expectations. Reserve `warehouse/tests` for business rules that cannot be
expressed clearly as generic tests.

The repository's pre-commit configuration uses dbt-checkpoint to compile dbt
changes and generate the documentation catalog before every commit. Both hooks
explicitly use this directory for the dbt project and profile. They select the
`pre_commit` profile target because Git invokes hooks from the repository root;
that target writes its disposable DuckDB file under `warehouse`, whose parent
exists on fresh CI runners. Normal commands run inside `warehouse` continue to
use `dev`. Install the Git hooks with:

```bash
make install-hooks
```

Run the configured stages from the repository root with `make precommit` and
`make prepush`.

Build only the staging layer through its named selector:

```bash
dbt build --selector staging
```

## Documentation catalog

Generate dbt's searchable lineage and database-object catalog after a build:

```bash
dbt docs generate
dbt docs serve
```

The generated site includes model and column definitions, tests, lineage,
declared data types, ownership metadata, and the physical DuckDB catalog. Files
under `warehouse/target` are generated locally and are not committed.

The default development target is the ignored repository file
`data/warehouse_dev.duckdb`. From `warehouse`, override it when needed:

```bash
WATCHPULSE_DBT_PATH=../data/candidate.duckdb \
dbt build
```

The `lake_root` dbt variable resolves to the repository's `data/lake` directory
by default (`../data/lake` from `warehouse`) and can point at a fixture lake or
another local artifact:

```bash
dbt build \
  --vars '{lake_root: /absolute/path/to/lake}'
```

## Atomic publication

From the repository root, build and publish the serving warehouse with:

```bash
make dbt-publish
```

The command builds and tests dbt against a uniquely named candidate DuckDB file
in the destination directory. It then validates `catalog_availability` and
`catalog_freshness` before atomically replacing the published file. A failed
build or validation leaves the previous serving database untouched and removes
the candidate.

The default destination is `data/warehouse_serving.duckdb`. Override it with:

```bash
WATCHPULSE_SERVING_DB_PATH=/absolute/path/watchpulse.duckdb make dbt-publish
```

Pass `--deps` when invoking the module directly if dbt packages have not yet
been installed:

```bash
python -m watchpulse.warehouse_publish --deps
```
