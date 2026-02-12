#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
API_URL="${API_URL:-http://127.0.0.1:8000}"
WEB_URL="${WEB_URL:-http://127.0.0.1:5173}"
WAIT_SECONDS="${WAIT_SECONDS:-120}"
POLL_SECONDS=2
LOG_DIR="${REPO_ROOT}/output/playwright"
LOG_FILE="${LOG_DIR}/dev-pr-screenshot-dev.log"

url_ready() {
  local url="$1"
  curl -sS --max-time 2 -o /dev/null "${url}"
}

is_ready() {
  url_ready "${API_URL}" && url_ready "${WEB_URL}"
}

if is_ready; then
  echo "API and web-app already running:"
  echo "  API: ${API_URL}"
  echo "  WEB: ${WEB_URL}"
  exit 0
fi

mkdir -p "${LOG_DIR}"

echo "Starting API and web-app with: mise run dev"
nohup mise run dev >"${LOG_FILE}" 2>&1 &
dev_pid=$!

echo "Waiting for services to be ready..."
deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  if is_ready; then
    echo "Services ready:"
    echo "  API: ${API_URL}"
    echo "  WEB: ${WEB_URL}"
    echo "Dev logs: ${LOG_FILE}"
    exit 0
  fi

  if ! kill -0 "${dev_pid}" >/dev/null 2>&1; then
    echo "Error: 'mise run dev' exited before services became ready." >&2
    echo "Last 40 log lines from ${LOG_FILE}:" >&2
    tail -n 40 "${LOG_FILE}" >&2 || true
    exit 1
  fi

  sleep "${POLL_SECONDS}"
done

echo "Error: timed out waiting for services after ${WAIT_SECONDS}s." >&2
echo "Last 40 log lines from ${LOG_FILE}:" >&2
tail -n 40 "${LOG_FILE}" >&2 || true
exit 1
