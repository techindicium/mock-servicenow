#!/bin/sh
# Seeds the database, then starts uvicorn.
#
# app/seed.py's main() exits 2 specifically for SEED_STATE_INCONSISTENT, which only happens
# when a previous seed run was interrupted before it finished (e.g. this container got killed
# mid-seed) -- never from a genuine data problem, that's exit 1. Since every row the seed
# command writes comes from a committed fixture, an exit-2 database holds nothing worth
# preserving: it is safe to wipe the file and reseed from scratch, exactly once. Exit 1 is not
# retried, since the same fixtures would just produce the same failure again.
set -eu

DB_PATH="${DATABASE_PATH:-servicenow.db}"

set +e
python3 -m app.seed
status=$?
set -e

if [ "$status" -eq 2 ]; then
  echo "seed: $DB_PATH was left in a partial state by an interrupted prior run -- wiping and reseeding" >&2
  rm -f "$DB_PATH"
  python3 -m app.seed
elif [ "$status" -ne 0 ]; then
  exit "$status"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
