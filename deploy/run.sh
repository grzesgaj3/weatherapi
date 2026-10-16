#!/usr/bin/env bash
# Ręczne uruchomienie API na małym VPS (bez systemd).
# Użycie:  bash deploy/run.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# Oszczędność pamięci glibc + brak plików .pyc
export MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Ustawienia limitu równoczesnych połączeń (ochrona małego VPS).
LIMIT_CONCURRENCY="${LIMIT_CONCURRENCY:-50}"

exec .venv/bin/uvicorn app.main:app \
    --host "${HOST:-127.0.0.1}" \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --no-access-log \
    --no-server-header \
    --limit-concurrency "${LIMIT_CONCURRENCY}" \
    --timeout-keep-alive 15 \
    --backlog 64
