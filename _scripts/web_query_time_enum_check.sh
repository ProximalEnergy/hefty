#!/bin/bash

# Run query-time enum semgrep on changed files or all web-app TS files.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUN_ALL_FILES=false

for arg in "$@"; do
    case "${arg}" in
        --all-files)
            RUN_ALL_FILES=true
            ;;
    esac
done

cd "${REPO_ROOT}"

target_web_files=""
declare -a baseline_args=()

if [ "${RUN_ALL_FILES}" = "true" ]; then
    target_web_files=$(
        rg --files web-app | grep -E '\.(ts|tsx)$' || true
    )
else
    base_ref="dev"

    if ! git rev-parse --verify --quiet "dev^{commit}" >/dev/null; then
        if git rev-parse --verify --quiet "origin/dev^{commit}" >/dev/null; then
            base_ref="origin/dev"
        fi
    fi

    if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
        echo "No dev base available for query-time enum check; skipping."
        exit 0
    fi

    if ! diff_files="$("${SCRIPT_DIR}/diff_files_vs_dev.sh" "${base_ref}")"; then
        echo "Unable to detect changed files vs ${base_ref}; skipping."
        exit 0
    fi

    target_web_files=$(
        printf '%s\n' "${diff_files}" \
            | grep -E '^web-app/.*\.(ts|tsx)$' || true
    )

    baseline_commit="$(git rev-parse "${base_ref}")"
    baseline_args=(--baseline-commit "${baseline_commit}")
fi

if [ -z "${target_web_files}" ]; then
    if [ "${RUN_ALL_FILES}" = "true" ]; then
        echo "No TS/TSX files for query-time enum check; skipping."
    else
        echo "No changed TS/TSX files vs ${base_ref}; skipping."
    fi
    exit 0
fi

declare -a targets=()
while IFS= read -r file; do
    if [ -n "${file}" ] && [ -f "${file}" ]; then
        targets+=("${file}")
    fi
done <<< "${target_web_files}"

if [ "${#targets[@]}" -eq 0 ]; then
    if [ "${RUN_ALL_FILES}" = "true" ]; then
        echo "No existing TS/TSX files for query-time enum check; skipping."
    else
        echo "No existing changed TS/TSX files vs ${base_ref}; skipping."
    fi
    exit 0
fi

uv run semgrep --error \
    --disable-version-check \
    --config _scripts/rules/query-time-enum.yaml \
    "${baseline_args[@]}" \
    "${targets[@]}"
