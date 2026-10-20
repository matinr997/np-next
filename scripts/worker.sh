#!/usr/bin/env bash
# Start the NursePlus content-pipeline worker.
#
#   ./scripts/worker.sh            # run in the foreground
#   ./scripts/worker.sh --daemon   # run in the background, log to deploy/worker.log
#
# The worker needs the site URL and the shared secret from api/config.php
# (worker_token) — it reads them itself, so there is nothing to configure here.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# the local server port (the worker talks to the API over it)
export NP_PORT="${NP_PORT:-8125}"

if [ ! -f api/config.php ]; then
  echo "api/config.php is missing — copy api/config.example.php and fill it in." >&2
  exit 1
fi

PY="$(command -v python3)"
# The transcript library and yt-dlp live in the system Python on macOS.
if ! "$PY" -c 'import youtube_transcript_api' >/dev/null 2>&1; then
  if [ -x /usr/bin/python3 ] && /usr/bin/python3 -c 'import youtube_transcript_api' >/dev/null 2>&1; then
    PY=/usr/bin/python3
  else
    echo "youtube_transcript_api is not installed: python3 -m pip install --user youtube-transcript-api" >&2
    exit 1
  fi
fi

if [ "${1:-}" = "--daemon" ]; then
  mkdir -p deploy
  nohup "$PY" -u scripts/pipeline_worker.py --loop --sleep 5 --no-git \
    >> deploy/worker.log 2>&1 &
  echo "worker started (pid $!), log: deploy/worker.log"
  echo "stop it with:  pkill -f pipeline_worker.py"
else
  exec "$PY" -u scripts/pipeline_worker.py --loop --sleep 5 --no-git
fi
