#!/usr/bin/env bash

set -euo pipefail

LOG_FILE="$(mktemp -t pveem-deploy-version-check.XXXXXX)"

read_version_tag() {
  local version_tag

  version_tag="$(
    grep '^version = "' pyproject.toml |
      head -n 1 |
      sed 's/version = "\(.*\)"/\1/'
  )"

  if [[ -z "${version_tag}" ]]; then
    echo "[deploy] Could not read version from pyproject.toml."
    exit 1
  fi

  printf '%s\n' "${version_tag}"
}

tag_current_commit() {
  local version_tag="$1"
  local release_tag="pv-eem/${version_tag}"
  local head_sha
  local tagged_sha

  head_sha="$(git rev-parse HEAD)"

  if git rev-parse --verify --quiet "refs/tags/${release_tag}" >/dev/null; then
    tagged_sha="$(git rev-parse "${release_tag}^{commit}")"
    if [[ "${tagged_sha}" == "${head_sha}" ]]; then
      echo "[deploy] Tag ${release_tag} already points to HEAD."
      return
    fi

    echo "[deploy] Tag ${release_tag} already exists on ${tagged_sha}."
    echo "[deploy] Refusing to move an existing release tag."
    exit 1
  fi

  git tag "${release_tag}"
  echo "[deploy] Created git tag ${release_tag}"
}

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

version_tag="$(read_version_tag)"

mise run pveem:types
mise run pveem:ruff
mise run pveem:pytest
mise run pveem:push-image
mise run pveem:cdk-deploy -- -c runtimeEnvironment=PROD
tag_current_commit "${version_tag}"
