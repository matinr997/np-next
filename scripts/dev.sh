#!/usr/bin/env bash
# Start the whole local environment: the PHP server, the pipeline worker.
#
#   ./scripts/dev.sh          # the server in the foreground, the worker as a daemon
#   ./scripts/dev.sh --stop   # stop everything
#
# The panel is then at http://127.0.0.1:8131/admin/
# The account is in api/config.php (admin email + password).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${NP_PORT:-8125}"
SITE="http://127.0.0.1:${PORT}"

if [ "${1:-}" = "--stop" ]; then
  pkill -f "php -S 127.0.0.1:${PORT}" 2>/dev/null || true
  pkill -f "pipeline_worker.py --loop" 2>/dev/null || true
  echo "stopped"
  exit 0
fi

# the database must exist before the server can answer
if [ ! -f "$ROOT/.data/nurseplus.sqlite" ]; then
  echo "the database is missing — run: php api/setup.php"
  exit 1
fi

if ! curl -s -o /dev/null "${SITE}/api/auth.php?action=csrf"; then
  echo "starting the PHP server on ${SITE}"
  # the server goes to the background, otherwise the script never returns
  (cd "$ROOT" && php -S "127.0.0.1:${PORT}" -t . > deploy/php-server.log 2>&1 </dev/null &)
  sleep 2
fi

if ! pgrep -f "pipeline_worker.py --loop" > /dev/null; then
  echo "starting the pipeline worker"
  NP_PORT="$PORT" bash "$ROOT/scripts/worker.sh" --daemon
fi

echo
echo "the panel   : ${SITE}/admin/"
echo "the COM one : ${SITE}/com/admin/"
echo "the site   : ${SITE}/index.html"
echo "the log    : deploy/worker.log"
