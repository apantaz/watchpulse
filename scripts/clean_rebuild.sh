#!/usr/bin/env bash
# Clean rebuild: back up the current local catalog state, then run a full
# TMDB backfill from an empty lake. See docs/catalog-refresh-runbook.md
# ("Clean rebuild from scratch") for the flow this wraps.
#
# This never deletes data outright — it moves data/lake, data/warehouse.duckdb,
# and data/warehouse_serving.duckdb aside into a timestamped backup directory
# first, so a bad rebuild is always recoverable.
#
# IMPORTANT: data/warehouse.duckdb holds the persisted monthly Streaming
# Availability request counter (see watchpulse/pipeline_runs.py). Moving it
# aside resets that counter to zero locally, even though your REAL usage
# against the provider's monthly cap this calendar month is unchanged. Do not
# run this more than once in the same month without accounting for that by
# hand, or you risk exceeding the real external quota while this script's
# own tracking says budget remains.
#
# Usage:
#   scripts/clean_rebuild.sh [COUNTRY]
#   scripts/clean_rebuild.sh --yes [COUNTRY]   # skip the interactive prompt

set -euo pipefail

cd "$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"

CONFIRM=0
if [[ "${1:-}" == "--yes" ]]; then
  CONFIRM=1
  shift
fi

COUNTRY="${1:-GR}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="data/backup-${TIMESTAMP}"

echo "This will:"
echo "  1. Move data/lake, data/warehouse.duckdb, data/warehouse_serving.duckdb"
echo "     into ${BACKUP_DIR}/ (nothing is deleted)."
echo "  2. Run a full TMDB backfill for country ${COUNTRY} from an empty lake"
echo "     (~13,000 one-time TMDB title requests at today's catalog size,"
echo "     likely tens of minutes to a few hours)."
echo "  3. Reset the locally tracked monthly Streaming Availability request"
echo "     counter to zero, even though your real usage against the"
echo "     provider's cap this month is unchanged."
echo

if [[ "${CONFIRM}" -ne 1 ]]; then
  read -r -p "Type 'rebuild' to continue: " reply
  if [[ "${reply}" != "rebuild" ]]; then
    echo "Aborted; nothing was changed." >&2
    exit 1
  fi
fi

mkdir -p "${BACKUP_DIR}"
for path in data/lake data/warehouse.duckdb data/warehouse_serving.duckdb; do
  if [[ -e "${path}" ]]; then
    mv "${path}" "${BACKUP_DIR}/"
  fi
done
echo "Backed up previous state to ${BACKUP_DIR}/"

echo "Starting backfill for ${COUNTRY}..."
python -m ingestion.full_refresh \
  --country "${COUNTRY}" \
  --enrichment-mode backfill \
  --enrichment-max-titles 20000 \
  --summary-output data/full-rebuild-summary.json

echo
echo "Rebuild complete. Verify with:"
echo "  python -m ingestion.inspect --country ${COUNTRY} --limit 20"
echo "  make test"
echo
echo "Once verified, delete the backup manually:"
echo "  rm -rf ${BACKUP_DIR}"
