#!/bin/bash

# Run ast-grep star-syntax quality checks.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [ "$#" -gt 0 ]; then
    scan_targets=("$@")
else
    scan_targets=(
        "core/src"
        "api/app"
        "microservices"
    )
fi

uvx --from ast-grep-cli ast-grep scan \
    --config "${SCRIPT_DIR}/ast-grep/sgconfig.yml" \
    --error=python-enforce-keyword-only-args \
    "${scan_targets[@]}" \
    --globs '!api/app/dependencies.py'
