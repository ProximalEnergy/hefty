#!/bin/bash

# Run semgrep quality checks excluding warning-only rules.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

declare -a config_args=()
declare -a scan_targets=(
    "core/src"
    "api/app"
    "microservices"
    "web-app/src"
)

while IFS= read -r rule_file; do
    config_args+=("--config" "${rule_file}")
done < <(
    find "${SCRIPT_DIR}/rules" \
        -maxdepth 1 \
        -type f \
        \( -name '*.yaml' -o -name '*.yml' \) \
        ! -name 'sqlalchemy-return.yaml' \
        | sort
)

if [ "${#config_args[@]}" -eq 0 ]; then
    echo "No semgrep rule configs found for root:semgrep."
    exit 1
fi

uvx semgrep@1.160 \
    --quiet \
    --disable-version-check \
    --error \
    "${config_args[@]}" \
    "${scan_targets[@]}" \
    --exclude "api/app/dependencies.py"
