#!/bin/bash

# Run SQLAlchemy return-method semgrep only on changed Python files.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

base_ref="dev"

if ! git rev-parse --verify --quiet "dev^{commit}" >/dev/null; then
    if git rev-parse --verify --quiet "origin/dev^{commit}" >/dev/null; then
        base_ref="origin/dev"
    fi
fi

if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
    echo "No dev base available for SQLAlchemy return check; skipping."
    exit 0
fi

if ! diff_files="$("${SCRIPT_DIR}/diff_files_vs_dev.sh" "${base_ref}")"; then
    echo "Unable to detect changed files vs ${base_ref}; skipping."
    exit 0
fi

changed_python_files=$(
    printf '%s\n' "${diff_files}" \
        | grep -E '\.py$' \
        | grep -Ev '(^|/)_scripts/' || true
)

if [ -z "${changed_python_files}" ]; then
    echo "No changed Python files for SQLAlchemy return check; skipping."
    exit 0
fi

declare -a targets=()
while IFS= read -r file; do
    if [ -n "${file}" ] && [ -f "${file}" ]; then
        targets+=("${file}")
    fi
done <<< "${changed_python_files}"

if [ "${#targets[@]}" -eq 0 ]; then
    echo "No existing changed Python files for SQLAlchemy return check; skipping."
    exit 0
fi

uv run semgrep --error \
    --disable-version-check \
    --config "${SCRIPT_DIR}/rules/sqlalchemy-return.yaml" \
    "${targets[@]}"
