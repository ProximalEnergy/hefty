#!/bin/bash

# Run ast-grep quality checks.
#
# Usage:
#   ./_scripts/ast_grep_check.sh [--json-stream] [--rules RULE1,...] [TARGET...]
#
# --rules  Comma-separated list of rule IDs to enable as errors.
#          Defaults to all rules when omitted.
# --json-stream  Emit ast-grep JSON stream output.
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
    python-core-require-selective-imports
    python-no-dbquery-dataframe-cast
)

json_stream=false

# Parse flags
selected_rules=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --json-stream)
            json_stream=true
            shift
            ;;
        --rules)
            shift
            if [ "$#" -eq 0 ]; then
                echo "--rules requires a comma-separated rule list" >&2
                exit 2
            fi
            IFS=',' read -ra selected_rules <<< "${1}"
            shift
            ;;
        *)
            break
            ;;
    esac
done

if [ "${#selected_rules[@]}" -eq 0 ]; then
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

ast_grep_args=(
    --config "${SCRIPT_DIR}/ast-grep/sgconfig.yml"
    --filter "${filter_regex}"
)

if [ "${json_stream}" = "true" ]; then
    ast_grep_args+=("--json=stream")
fi

ast_grep_args+=("${scan_targets[@]}")
ast_grep_args+=(--globs '!api/app/dependencies.py')

uvx --from ast-grep-cli ast-grep scan "${ast_grep_args[@]}"
