#!/bin/bash

# Run ast-grep quality checks.
#
# Usage:
#   ./_scripts/ast_grep_check.sh [--rules RULE1,RULE2,...] [TARGET...]
#
# --rules  Comma-separated list of rule IDs to enable as errors.
#          Defaults to all rules when omitted.
# TARGET   One or more paths to scan (default: core/src api/app microservices).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

ALL_RULES=(
    python-enforce-keyword-only-args
    python-missing-args-in-docstring
    python-disallow-sqlalchemy-query-filter
    python-disallow-sqlalchemy-array-agg
    fastapi-project-id-requires-access
    fastapi-project-id-requires-access-prefix
    forbidden-with-async-db-usage
)

# Parse --rules flag
selected_rules=()
if [ "${1:-}" = "--rules" ]; then
    shift
    IFS=',' read -ra selected_rules <<< "${1}"
    shift
else
    selected_rules=("${ALL_RULES[@]}")
fi

# Remaining args are scan targets
if [ "$#" -gt 0 ]; then
    scan_targets=("$@")
else
    scan_targets=(
        "core/src"
        "api/app"
        "microservices"
    )
fi

filter_regex="^("
for i in "${!selected_rules[@]}"; do
    if [ "$i" -gt 0 ]; then
        filter_regex+="|"
    fi
    filter_regex+="${selected_rules[$i]}"
done
filter_regex+=")$"

uvx --from ast-grep-cli ast-grep scan \
    --config "${SCRIPT_DIR}/ast-grep/sgconfig.yml" \
    --filter "${filter_regex}" \
    "${scan_targets[@]}" \
    --globs '!api/app/dependencies.py'
