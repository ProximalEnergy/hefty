#!/usr/bin/env bash

set -euo pipefail

LOG_FILE="$(mktemp -t pveem-deploy-version-check.XXXXXX)"

cleanup() {
  rm -f "${LOG_FILE}"
}
trap cleanup EXIT

if mise run pveem:version-check >"${LOG_FILE}" 2>&1; then
  cat "${LOG_FILE}"
else
  cat "${LOG_FILE}"

  if grep -q "No semver-like deployed image tags found for Lambda" "${LOG_FILE}"; then
    echo "[deploy] Current Lambda image only has non-semver tags."
    echo "[deploy] Continuing to publish and deploy pyproject.toml version."
  else
    exit 1
  fi
fi

mise run pveem:types
mise run pveem:ruff
mise run pveem:pytest
mise run pveem:push-image
mise run pveem:cdk-deploy -- -c runtimeEnvironment=PROD
