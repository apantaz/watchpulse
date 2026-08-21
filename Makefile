PYTHON ?= python

.PHONY: install install-hooks dbt-deps dbt-parse precommit pre-commit prepush pre-push syntax test ci

install:
	$(PYTHON) -m pip install -e ".[dev,warehouse]"

install-hooks:
	$(PYTHON) -m pre_commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

dbt-deps:
	cd warehouse && dbt deps

dbt-parse:
	cd warehouse && dbt parse

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

ci: dbt-deps precommit syntax dbt-parse test
