PYTHON ?= python

.PHONY: install install-hooks api-dev catalog-refresh dbt-deps dbt-debug dbt-parse dbt-validate dbt-publish frontend-install frontend-dev frontend-lint frontend-test frontend-build frontend-ci lint precommit pre-commit prepush pre-push syntax test coverage ci

install:
	$(PYTHON) -m pip install -e ".[dev,warehouse]"

install-hooks:
	$(PYTHON) -m pre_commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

api-dev:
	uvicorn watchpulse.api:create_app --factory --reload

catalog-refresh:
	$(PYTHON) -m ingestion.full_refresh --country GR --summary-output data/full-refresh-summary.json

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

frontend-ci: frontend-lint frontend-test frontend-build

dbt-deps:
	cd warehouse && dbt deps

dbt-debug:
	cd warehouse && dbt debug

dbt-parse:
	cd warehouse && dbt parse

dbt-validate: dbt-deps dbt-debug dbt-parse

dbt-publish:
	$(PYTHON) -m watchpulse.warehouse_publish

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

precommit:
	$(PYTHON) -m pre_commit run --all-files --hook-stage pre-commit

pre-commit: precommit

prepush:
	$(PYTHON) -m pre_commit run --all-files --hook-stage pre-push

pre-push: prepush

syntax:
	$(PYTHON) -m compileall -q watchpulse ingestion

test:
	$(PYTHON) -m pytest -q

coverage:
	$(PYTHON) -m pytest -q --cov=watchpulse --cov=ingestion --cov-report=term-missing --cov-report=xml --cov-fail-under=65

ci: lint syntax coverage dbt-validate
