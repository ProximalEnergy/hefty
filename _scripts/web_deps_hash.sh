#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="${ROOT_DIR}/web-app"
STAMP_FILE="${WEB_DIR}/node_modules/.mono-deps.hash"

hash_file_if_present() {
  local path="$1"

  if [ -f "${path}" ]; then
    shasum < "${path}"
  fi
}

write_hash_inputs() {
  printf 'pnpm=%s\n' "$(mise current pnpm)"
  hash_file_if_present "${ROOT_DIR}/.npmrc"
  hash_file_if_present "${ROOT_DIR}/pnpm-workspace.yaml"
  hash_file_if_present "${WEB_DIR}/.npmrc"
  hash_file_if_present "${WEB_DIR}/package.json"
  hash_file_if_present "${WEB_DIR}/pnpm-lock.yaml"
}

current_hash() {
  write_hash_inputs | shasum | awk '{ print $1 }'
}

check_web_deps_installed() {
  if [ ! -f "${WEB_DIR}/node_modules/.modules.yaml" ]; then
    echo "Stale pnpm environment: web-app node_modules is missing"
    return 1
  fi

  if [ ! -d "${WEB_DIR}/node_modules/.pnpm" ]; then
    echo "Stale pnpm environment: web-app virtual store is missing"
    return 1
  fi
}

check_web_deps_hash() {
  local expected_hash
  local stored_hash

  check_web_deps_installed || return 1

  expected_hash="$(current_hash)"
  if [ ! -f "${STAMP_FILE}" ]; then
    echo "Stale pnpm environment: web-app dependency stamp is missing"
    return 1
  fi

  stored_hash="$(cat "${STAMP_FILE}")"
  if [ "${stored_hash}" != "${expected_hash}" ]; then
    echo "Stale pnpm environment: web-app dependency inputs changed"
    return 1
  fi
}

write_web_deps_hash() {
  mkdir -p "$(dirname "${STAMP_FILE}")"
  current_hash > "${STAMP_FILE}"
}

case "${1:-check}" in
  check)
    check_web_deps_hash
    ;;
  print)
    current_hash
    ;;
  write)
    write_web_deps_hash
    ;;
  *)
    echo "Usage: $0 [check|print|write]" >&2
    exit 2
    ;;
esac
