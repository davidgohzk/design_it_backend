#!/usr/bin/env bash
# Starts the API. Render sets PORT; locally it defaults to 8000 and loads .env if present.
set -euo pipefail

args=(app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*")

if [ -f .env ]; then
  args+=(--env-file .env)
fi

exec uvicorn "${args[@]}"
