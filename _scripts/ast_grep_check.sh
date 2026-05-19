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
    python-hardcoded-type-id
    ts-hardcoded-type-id
    python-enforce-keyword-only-args
    python-missing-args-in-docstring
    python-disallow-sqlalchemy-query-filter
    python-disallow-sqlalchemy-array-agg
    fastapi-project-id-requires-access
    fastapi-project-id-requires-access-prefix
    forbidden-with-async-db-usage
    python-core-require-selective-imports
    python-no-dbquery-dataframe-cast
    api-no-python-logger-definitions-outside-logger
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
ast_grep_args+=(--globs '!**/node_modules/**')
ast_grep_args+=(--globs '!**/__pycache__/**')
ast_grep_args+=(--globs '!**/.git/**')
ast_grep_args+=(--globs '!**/.venv/**')
ast_grep_args+=(--globs '!**/venv/**')
ast_grep_args+=(--globs '!**/dist/**')
ast_grep_args+=(--globs '!**/build/**')
ast_grep_args+=(--globs '!**/.next/**')
ast_grep_args+=(--globs '!**/.cache/**')
ast_grep_args+=(--globs '!**/*.egg-info/**')
ast_grep_args+=(--globs '!**/.pytest_cache/**')
ast_grep_args+=(--globs '!**/.mypy_cache/**')
ast_grep_args+=(--globs '!**/.ruff_cache/**')
ast_grep_args+=(--globs '!_scripts/**')
ast_grep_args+=(--globs '!**/_scripts/**')
ast_grep_args+=(--globs '!api/_tests/**')
ast_grep_args+=(--globs '!pv-eem/_tests/**')
ast_grep_args+=(--globs '!web-app/src/api/schema.d.ts')
ast_grep_args+=(--globs '!web-app/rollup-plugin-visualizer-stats.html')
ast_grep_args+=(--globs '!api/app/dependencies.py')

uvx --from ast-grep-cli ast-grep scan "${ast_grep_args[@]}"
