PYTHON ?= python

.PHONY: install install-hooks dbt-deps dbt-debug dbt-parse dbt-validate lint precommit pre-commit prepush pre-push syntax test coverage ci

install:
	$(PYTHON) -m pip install -e ".[dev,warehouse]"

install-hooks:
	$(PYTHON) -m pre_commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

dbt-deps:
	cd warehouse && dbt deps

dbt-debug:
	cd warehouse && dbt debug

dbt-parse:
	cd warehouse && dbt parse

dbt-validate: dbt-deps dbt-debug dbt-parse

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
