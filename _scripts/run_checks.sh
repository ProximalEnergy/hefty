#!/bin/bash


set +e  # Don't exit on first error - we want to run all checks
unset VIRTUAL_ENV

# Parse command line arguments
SKIP_TESTS=false
RUN_SLOW=false
RUN_ALL=false
REQUESTED_DIFF_ONLY=true
OFFLINE=false
QUIET=true
ALL_WARNINGS=false
FAST_FAIL=false
ASYNC_OFFLINE=false
CODEX_CONTEXT_MODE="none"
CODEX_PROMPT="Fix the selected failed checks in this repo. Apply the "\
"smallest safe changes in the working tree so the checks pass. Do not "\
"only describe the fix; apply it. If blocked, explain briefly."
if [ "${AGENT_ENVIRONMENT}" = "async-offline" ]; then
    ASYNC_OFFLINE=true
fi
while [ "$#" -gt 0 ]; do
    case "$1" in
        --static)
            SKIP_TESTS=true
            shift
            ;;
        -s|--slow)
            RUN_SLOW=true
            shift
            ;;
        --all)
            RUN_ALL=true
            REQUESTED_DIFF_ONLY=false
            shift
            ;;
        --diff-only)
            RUN_ALL=false
            REQUESTED_DIFF_ONLY=true
            shift
            ;;
        --offline)
            OFFLINE=true
            shift
            ;;
        --all-warnings)
            ALL_WARNINGS=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --verbose)
            QUIET=false
            shift
            ;;
        -ff|--ff|--fast-fail)
            FAST_FAIL=true
            shift
            ;;
        --codex-context)
            if [ "$#" -gt 1 ] && [ "${2#-}" = "$2" ]; then
                CODEX_CONTEXT_MODE="$2"
                shift 2
            else
                CODEX_CONTEXT_MODE="all"
                shift
            fi
            ;;
        --codex-context=*)
            CODEX_CONTEXT_MODE="${1#*=}"
            shift
            ;;
        --codex-prompt)
            if [ "$#" -lt 2 ]; then
                echo "Missing value for --codex-prompt" >&2
                exit 2
            fi
            CODEX_PROMPT="$2"
            shift 2
            ;;
        --codex-prompt=*)
            CODEX_PROMPT="${1#*=}"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

case "${CODEX_CONTEXT_MODE}" in
    none|errors|warnings|all)
        ;;
    *)
        echo "Invalid --codex-context value: ${CODEX_CONTEXT_MODE}" >&2
        echo "Use one of: none, errors, warnings, all" >&2
        exit 2
        ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}Running relevant quality checks...${NC}\n"

# Arrays to track results
declare -a PASSED_CHECKS=()
declare -a FAILED_ERROR_CHECKS=()
declare -a FAILED_WARNING_CHECKS=()

# Arrays to store checks to be run
declare -a CHECKS_CMD=()
declare -a CHECKS_IS_PARALLEL=()
declare -a CHECKS_SEVERITY=()
declare -a CHECKS_SKIP_REASON=()
declare -a CHECKS_UI_COMPLETED=()
declare -a CHECKS_BATCH_GROUP=()
declare -a CHECKS_BATCH_RULE_ID=()
declare -a CHECKS_RESULT_STATUS=()
declare -a CHECKS_ELAPSED_SECONDS=()
CHECKS_COMPLETED_COUNT=0
LAST_COMPLETED_CHECK=""
LIVE_FAILURE_LINES=0

# Function to add a check to the list
add_check() {
    local name="$1"
    local cmd="$2"
    local severity="${3:-error}"
    local is_parallel="${4:-true}"

    # Ruff checks and Formatting should run sequentially at the end
    if [[ "$cmd" == *":ruff"* ]] || [[ "$cmd" == *":ruff_format"* ]]; then
        is_parallel="false"
    fi

    CHECKS_CMD+=("$cmd")
    CHECKS_IS_PARALLEL+=("$is_parallel")
    CHECKS_SEVERITY+=("$severity")
    CHECKS_BATCH_GROUP+=("")
    CHECKS_BATCH_RULE_ID+=("")
}

add_batched_ast_grep_check() {
    local name="$1"
    local cmd="$2"
    local rule_id="$3"
    local check_index

    add_check "$name" "$cmd"
    check_index=$((${#CHECKS_CMD[@]} - 1))
    CHECKS_BATCH_GROUP[$check_index]="root_ast_grep"
    CHECKS_BATCH_RULE_ID[$check_index]="$rule_id"
}

add_warning_check() {
    local name="$1"
    local cmd="$2"

    add_check "$name" "$cmd" "warning"
}

add_initial_check() {
    local name="$1"
    local cmd="$2"
    local severity="${3:-error}"

    add_check "$name" "$cmd" "$severity" "initial"
}

add_skipped_check() {
    local name="$1"
    local cmd="$2"
    local skip_reason="$3"
    local severity="${4:-error}"
    local is_parallel="${5:-true}"
    local check_index

    add_check "$name" "$cmd" "$severity" "$is_parallel"
    check_index=$((${#CHECKS_CMD[@]} - 1))
    CHECKS_SKIP_REASON[$check_index]="$skip_reason"
}

add_skipped_warning_check() {
    local name="$1"
    local cmd="$2"
    local skip_reason="$3"

    add_skipped_check "$name" "$cmd" "$skip_reason" "warning"
}

add_skipped_error_check() {
    local name="$1"
    local cmd="$2"
    local skip_reason="$3"
    local is_parallel="${4:-true}"

    add_skipped_check "$name" "$cmd" "$skip_reason" "error" "$is_parallel"
}

add_slow_check() {
    local name="$1"
    local cmd="$2"
    local severity="${3:-error}"
    local is_parallel="${4:-true}"

    if [ "${RUN_SLOW}" = "true" ]; then
        add_check "$name" "$cmd" "$severity" "$is_parallel"
    else
        add_skipped_check \
            "$name" \
            "$cmd" \
            "slow check; use -s" \
            "$severity" \
            "$is_parallel"
    fi
}

add_db_check() {
    local name="$1"
    local cmd="$2"

    if [ "${ASYNC_OFFLINE}" = "true" ]; then
        add_skipped_warning_check "$name" "$cmd" "async offline env"
        return 0
    fi

    add_check "$name" "$cmd"
}

cleanup_run_all_checks() {
    tput cnorm 2>/dev/null || true
    if [ -n "${RUN_CHECKS_LOG_DIR:-}" ] && [ -d "${RUN_CHECKS_LOG_DIR}" ]; then
        rm -rf "${RUN_CHECKS_LOG_DIR}"
    fi
}

with_check_ui_lock() {
    local lock_dir
    local status

    if [ -z "${RUN_CHECKS_LOG_DIR:-}" ]; then
        "$@"
        return $?
    fi

    lock_dir="${RUN_CHECKS_LOG_DIR}/check_ui.lock"
    while ! mkdir "$lock_dir" 2>/dev/null; do
        sleep 0.02
    done

    "$@"
    status=$?
    rmdir "$lock_dir" 2>/dev/null || true
    return "$status"
}

is_check_skipped() {
    local check_index="$1"

    [ -n "${CHECKS_SKIP_REASON[$check_index]:-}" ]
}

codex_cli_available() {
    command -v codex >/dev/null 2>&1
}

prompt_failure_action() {
    local show_logs_input
    local allow_errors="${1:-false}"
    local allow_warnings="${2:-false}"
    local allow_codex="${3:-false}"
    local allow_successes="${4:-false}"
    local prompt_body
    local prompt_text
    local valid_input_text
    local -a prompt_options=()
    local -a valid_inputs=()

    if [ "$allow_errors" = "true" ]; then
        prompt_options+=("(e)rrors")
        valid_inputs+=("e")
    fi
    if [ "$allow_warnings" = "true" ]; then
        prompt_options+=("(w)arnings")
        valid_inputs+=("w")
    fi
    if [ "$allow_errors" = "true" ] && [ "$allow_warnings" = "true" ]; then
        prompt_options+=("(a)ll")
        valid_inputs+=("a")
    fi
    if [ "$allow_successes" = "true" ]; then
        prompt_options+=("(s)uccesses")
        valid_inputs+=("s")
    fi

    prompt_options+=("(n)one")
    valid_inputs+=("n")

    if [ "$allow_codex" = "true" ]; then
        prompt_options+=("(c)odex")
        valid_inputs+=("c")
    fi

    printf -v prompt_body '%s/' "${prompt_options[@]}"
    prompt_body="${prompt_body%/}"
    prompt_text="Failure action? [${prompt_body}]: "

    printf -v valid_input_text '%s, ' "${valid_inputs[@]}"
    valid_input_text="${valid_input_text%, }"

    while true; do
        read -r -p "$prompt_text" show_logs_input
        show_logs_input=$(
            printf '%s' "$show_logs_input" | tr '[:upper:]' '[:lower:]'
        )
        case "$show_logs_input" in
            e|errors)
                if [ "$allow_errors" = "true" ]; then
                    echo "errors"
                    return 0
                fi
                ;;
            w|warnings)
                if [ "$allow_warnings" = "true" ]; then
                    echo "warnings"
                    return 0
                fi
                ;;
            a|all)
                if [ "$allow_errors" = "true" ] \
                    && [ "$allow_warnings" = "true" ]; then
                    echo "all"
                    return 0
                fi
                ;;
            s|success|successes)
                if [ "$allow_successes" = "true" ]; then
                    echo "successes"
                    return 0
                fi
                ;;
            n|none)
                echo "none"
                return 0
                ;;
            c|codex)
                if [ "$allow_codex" = "true" ]; then
                    echo "codex"
                    return 0
                fi
                ;;
            *)
                echo "Please enter one of: ${valid_input_text}."
                ;;
        esac
    done
}

prompt_all_passed_action() {
    local show_passed_input

    while true; do
        read -r -p \
            "All checks passed. Show [(n)one/(p)assed]: " \
            show_passed_input
        show_passed_input=$(
            printf '%s' "$show_passed_input" | tr '[:upper:]' '[:lower:]'
        )
        case "$show_passed_input" in
            n|none)
                echo "none"
                return 0
                ;;
            p|passed)
                echo "passed"
                return 0
                ;;
            *)
                echo "Please enter one of: n, p."
                ;;
        esac
    done
}

prompt_post_log_codex_action() {
    local codex_mode="$1"
    local prompt_subject="failures"
    local codex_input

    case "$codex_mode" in
        errors)
            prompt_subject="errors"
            ;;
        warnings)
            prompt_subject="warnings"
            ;;
    esac

    while true; do
        read -r -p \
            "Pass displayed ${prompt_subject} to Codex? [(c)odex/(n)one]: " \
            codex_input
        codex_input=$(
            printf '%s' "$codex_input" | tr '[:upper:]' '[:lower:]'
        )
        case "$codex_input" in
            c|codex)
                echo "codex"
                return 0
                ;;
            n|none)
                echo "none"
                return 0
                ;;
            *)
                echo "Please enter one of: c, n."
                ;;
        esac
    done
}

send_failures_to_codex() {
    local codex_mode="$1"
    local codex_context_file
    local log_file
    local i
    local -a selected_codex_indices=()

    if ! codex_cli_available; then
        echo ""
        echo "codex CLI not found; skipping Codex context handoff."
        return 1
    fi

    case "${codex_mode}" in
        errors)
            selected_codex_indices=("${failed_error_indices[@]}")
            ;;
        warnings)
            selected_codex_indices=("${failed_warning_indices[@]}")
            ;;
        all)
            selected_codex_indices=(
                "${failed_error_indices[@]}"
                "${failed_warning_indices[@]}"
            )
            ;;
        *)
            echo ""
            echo "Invalid Codex context mode: ${codex_mode}"
            return 1
            ;;
    esac

    if [ "${#selected_codex_indices[@]}" -eq 0 ]; then
        echo ""
        echo "No matching failures for Codex handoff."
        return 1
    fi

    codex_context_file="${RUN_CHECKS_LOG_DIR}/codex_context.txt"
    {
        echo "run_checks codex context"
        echo "mode: ${codex_mode}"
        echo ""
        for i in "${selected_codex_indices[@]}"; do
            echo "---"
            echo "check: $(get_check_ui_label "$i")"
            echo "command: ${CHECKS_CMD[$i]}"
            echo "severity: ${CHECKS_SEVERITY[$i]}"
            echo ""
            log_file="${RUN_CHECKS_LOG_DIR}/check_${i}.log"
            if [ -f "$log_file" ]; then
                cat "$log_file"
            else
                echo "No log file found for this check."
            fi
            echo ""
        done
    } >"${codex_context_file}"

    echo ""
    echo "Running Codex fix attempt..."
    {
        echo "${CODEX_PROMPT}"
        echo ""
        echo "Use this check output context:"
        echo ""
        cat "${codex_context_file}"
    } | codex exec \
        --full-auto \
        -C "$(pwd)" \
        - || true
}

get_ui_terminal_columns() {
    local cols=80
    local tput_cols

    if [ -t 1 ]; then
        tput_cols=$(tput cols 2>/dev/null || echo 80)
        if [[ "${COLUMNS:-}" =~ ^[0-9]+$ ]]; then
            cols="$COLUMNS"
        fi
        if [[ "$tput_cols" =~ ^[0-9]+$ ]] && [ "$tput_cols" -lt "$cols" ]; then
            cols="$tput_cols"
        fi
    fi

    if ! [[ "$cols" =~ ^[0-9]+$ ]] || [ "$cols" -lt 20 ]; then
        cols=80
    fi

    echo "$cols"
}

truncate_ui_label() {
    local label="$1"
    local max_len="$2"

    if [ "$max_len" -le 0 ]; then
        echo ""
        return
    fi

    if [ "${#label}" -le "$max_len" ]; then
        echo "$label"
        return
    fi

    if [ "$max_len" -le 3 ]; then
        printf "%.*s" "$max_len" "$label"
        return
    fi

    printf "%.*s..." "$((max_len - 3))" "$label"
}

format_elapsed_seconds() {
    local elapsed_seconds="$1"
    local minutes
    local seconds

    if ! [[ "$elapsed_seconds" =~ ^[0-9]+$ ]]; then
        echo "0s"
        return
    fi

    if [ "$elapsed_seconds" -lt 60 ]; then
        echo "${elapsed_seconds}s"
        return
    fi

    minutes=$((elapsed_seconds / 60))
    seconds=$((elapsed_seconds % 60))

    if [ "$seconds" -eq 0 ]; then
        echo "${minutes}m"
        return
    fi

    echo "${minutes}m ${seconds}s"
}

render_live_summary() {
    local total_checks="${#CHECKS_CMD[@]}"
    local passed_count="${#PASSED_CHECKS[@]}"
    local failed_count="${#FAILED_ERROR_CHECKS[@]}"
    local warning_count="${#FAILED_WARNING_CHECKS[@]}"
    local columns
    local max_line_len
    local prefix
    local label
    local max_label_len

    if [ ! -t 1 ]; then
        return
    fi

    columns=$(get_ui_terminal_columns)
    max_line_len=$((columns - 8))
    if [ "$max_line_len" -gt 72 ]; then
        max_line_len=72
    fi
    if [ "$max_line_len" -lt 1 ]; then
        max_line_len=1
    fi

    prefix="Progress ${CHECKS_COMPLETED_COUNT}/${total_checks} | "
    prefix="${prefix}Pass ${passed_count} | "
    prefix="${prefix}Fail ${failed_count} | Warn ${warning_count} | Last "
    if [ "${#prefix}" -gt "$max_line_len" ]; then
        prefix=$(truncate_ui_label "$prefix" "$max_line_len")
    fi

    max_label_len=$((max_line_len - ${#prefix}))
    if [ "$max_label_len" -lt 0 ]; then
        max_label_len=0
    fi

    label=$(truncate_ui_label "$LAST_COMPLETED_CHECK" "$max_label_len")
    printf "\r\033[2K%s%s" "$prefix" "$label"
}

update_check_ui_running() {
    with_check_ui_lock update_check_ui_running_unlocked "$@"
}

update_check_ui_running_unlocked() {
    : "$1"
    render_live_summary
}

update_check_ui_status() {
    with_check_ui_lock update_check_ui_status_unlocked "$@"
}

update_check_ui_status_unlocked() {
    local check_index="$1"

    if [ "${CHECKS_UI_COMPLETED[$check_index]:-0}" -eq 0 ]; then
        CHECKS_UI_COMPLETED[$check_index]=1
        CHECKS_COMPLETED_COUNT=$((CHECKS_COMPLETED_COUNT + 1))
    fi

    LAST_COMPLETED_CHECK="$(get_check_ui_label "$check_index")"
    render_live_summary
}

print_live_check_failure() {
    local check_index="$1"
    local color="$2"
    local lines_down

    if [ ! -t 1 ]; then
        return
    fi

    lines_down=$((LIVE_FAILURE_LINES + 1))
    printf "\033[%sB\r\033[2K" "$lines_down"
    printf "%b✗ %s%b" \
        "${BOLD}${color}" \
        "$(get_timed_check_ui_label "$check_index")" \
        "${NC}"
    LIVE_FAILURE_LINES=$((LIVE_FAILURE_LINES + 1))
    printf "\033[%sA\r" "$LIVE_FAILURE_LINES"
}

finish_live_summary() {
    if [ ! -t 1 ]; then
        echo ""
        return
    fi

    printf "\033[%sB\r" "$((LIVE_FAILURE_LINES + 1))"
}

get_check_ui_label() {
    local check_index="$1"
    local skip_reason="${CHECKS_SKIP_REASON[$check_index]:-}"
    local check_label="${CHECKS_CMD[$check_index]}"

    check_label="${check_label#mise run }"

    if [ -n "$skip_reason" ]; then
        check_label="${check_label} (skipped: ${skip_reason})"
    fi

    echo "$check_label"
}

get_timed_check_ui_label() {
    local check_index="$1"
    local elapsed_seconds="${CHECKS_ELAPSED_SECONDS[$check_index]:-}"
    local check_label

    check_label=$(get_check_ui_label "$check_index")
    if [[ "$elapsed_seconds" =~ ^[0-9]+$ ]]; then
        check_label="${check_label} ($(format_elapsed_seconds "$elapsed_seconds"))"
    fi

    echo "$check_label"
}

print_passed_checks() {
    local i

    if [ "${#PASSED_CHECKS[@]}" -eq 0 ]; then
        return
    fi

    echo ""
    echo -e "${GREEN}Passed checks:${NC}"
    echo ""
    for i in "${!CHECKS_CMD[@]}"; do
        if [ "${CHECKS_RESULT_STATUS[$i]:-}" = "0" ]; then
            echo -e "${GREEN}✓ $(get_timed_check_ui_label "$i")${NC}"
        fi
    done
    echo ""
}

print_failed_check_summary() {
    local i

    if [ "${#failed_error_indices[@]}" -gt 0 ]; then
        echo -e "${RED}Failed checks:${NC}"
        echo ""
        for i in "${failed_error_indices[@]}"; do
            echo -e "${BOLD}${RED}✗ $(get_timed_check_ui_label "$i")${NC}"
        done
    fi

    if [ "${#failed_warning_indices[@]}" -gt 0 ]; then
        if [ "${#failed_error_indices[@]}" -gt 0 ]; then
            echo ""
        fi
        echo -e "${PURPLE}Warning checks:${NC}"
        echo ""
        for i in "${failed_warning_indices[@]}"; do
            echo -e "${BOLD}${PURPLE}✗ $(get_timed_check_ui_label "$i")${NC}"
        done
    fi
}

CHECK_EXECUTION_STATUS=0
CHECK_EXECUTION_ELAPSED_SECONDS=0

execute_check_to_log() {
    local check_index="$1"
    local log_file="$2"
    local status_file="${3:-}"
    local cmd="${CHECKS_CMD[$check_index]}"
    local check_started_at="$SECONDS"
    local status
    local elapsed_seconds

    if eval "$cmd" >"$log_file" 2>&1; then
        status=0
    else
        status=$?
    fi

    elapsed_seconds=$((SECONDS - check_started_at))
    CHECK_EXECUTION_STATUS="$status"
    CHECK_EXECUTION_ELAPSED_SECONDS="$elapsed_seconds"

    if [ -n "$status_file" ]; then
        printf "%s:%s\n" "$status" "$elapsed_seconds" >"$status_file"
    fi
}

record_check_result() {
    local check_index="$1"
    local status="$2"
    local elapsed_seconds="${3:-0}"

    if ! [[ "$elapsed_seconds" =~ ^[0-9]+$ ]]; then
        elapsed_seconds=0
    fi

    CHECKS_RESULT_STATUS[$check_index]="$status"
    CHECKS_ELAPSED_SECONDS[$check_index]="$elapsed_seconds"

    if [ "$status" -eq 0 ]; then
        PASSED_CHECKS+=("$(get_check_ui_label "$check_index")")
    elif [ "${CHECKS_SEVERITY[$check_index]}" = "warning" ]; then
        FAILED_WARNING_CHECKS+=(
            "$(get_check_ui_label "$check_index"):${CHECKS_CMD[$check_index]}"
        )
        failed_warning_indices+=("$check_index")
    else
        FAILED_ERROR_CHECKS+=(
            "$(get_check_ui_label "$check_index"):${CHECKS_CMD[$check_index]}"
        )
        failed_error_indices+=("$check_index")
    fi

    update_check_ui_status "$check_index"

    if [ "$status" -eq 0 ]; then
        return
    fi
    if [ "${CHECKS_SEVERITY[$check_index]}" = "warning" ]; then
        print_live_check_failure "$check_index" "$PURPLE"
    else
        print_live_check_failure "$check_index" "$RED"
    fi
}

run_sync_check() {
    local check_index="$1"
    local log_file="${RUN_CHECKS_LOG_DIR}/check_${check_index}.log"

    execute_check_to_log "$check_index" "$log_file"
    record_check_result \
        "$check_index" \
        "$CHECK_EXECUTION_STATUS" \
        "$CHECK_EXECUTION_ELAPSED_SECONDS"
}

run_fast_fail_checks() {
    local i

    for i in "${!CHECKS_CMD[@]}"; do
        if is_check_skipped "$i"; then
            continue
        fi

        update_check_ui_running "$i"
        run_sync_check "$i"
        if [ "${CHECKS_RESULT_STATUS[$i]:-0}" -ne 0 ]; then
            break
        fi
    done
}

is_root_ast_grep_batch_check() {
    local check_index="$1"

    [ "${CHECKS_BATCH_GROUP[$check_index]:-}" = "root_ast_grep" ]
}

count_root_ast_grep_findings() {
    local raw_log="$1"

    python3 - "$raw_log" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

count = 0
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    if data.get("ruleId"):
        count += 1

print(count)
PY
}

write_root_ast_grep_rule_log() {
    local check_index="$1"
    local raw_log="$2"
    local batch_status="$3"
    local total_findings="$4"
    local rule_id="${CHECKS_BATCH_RULE_ID[$check_index]}"
    local log_file="${RUN_CHECKS_LOG_DIR}/check_${check_index}.log"

    python3 - \
        "$raw_log" \
        "$log_file" \
        "$rule_id" \
        "$batch_status" \
        "$total_findings" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

raw_log = pathlib.Path(sys.argv[1])
log_file = pathlib.Path(sys.argv[2])
rule_id = sys.argv[3]
batch_status = int(sys.argv[4])
total_findings = int(sys.argv[5])

findings: list[str] = []
raw_lines = raw_log.read_text().splitlines()
for line in raw_lines:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    if data.get("ruleId") != rule_id:
        continue

    file_path = data.get("file", "<unknown>")
    start = data.get("range", {}).get("start", {})
    line_number = int(start.get("line", -1)) + 1
    text = " ".join(data.get("text", "").split())
    findings.append(f"{file_path}:{line_number}:{rule_id}: {text}")

with log_file.open("w") as file:
    if findings:
        print(f"Found {len(findings)} findings for {rule_id}.", file=file)
        for finding in findings:
            print(finding, file=file)
    elif batch_status != 0 and total_findings == 0:
        print(f"ast-grep batch failed before reporting {rule_id}.", file=file)
        for line in raw_lines:
            print(line, file=file)
    else:
        print(f"{rule_id} passed.", file=file)

print(len(findings))
PY
}

execute_root_ast_grep_batch_to_logs() {
    local status_file="$1"
    local raw_log="${RUN_CHECKS_LOG_DIR}/root_ast_grep_batch.jsonl"
    local command_status
    local non_type_id_rules
    local type_id_rules
    local check_started_at="$SECONDS"
    local status
    local elapsed_seconds
    local total_findings
    local rule_findings
    local i

    non_type_id_rules="python-enforce-keyword-only-args"
    non_type_id_rules="${non_type_id_rules},python-missing-args-in-docstring"
    non_type_id_rules="${non_type_id_rules},python-disallow-sqlalchemy-query-filter"
    non_type_id_rules="${non_type_id_rules},python-disallow-sqlalchemy-array-agg"
    non_type_id_rules="${non_type_id_rules},fastapi-project-id-requires-access"
    non_type_id_rules="${non_type_id_rules},fastapi-project-id-requires-access-prefix"
    non_type_id_rules="${non_type_id_rules},forbidden-with-async-db-usage"
    non_type_id_rules="${non_type_id_rules},python-no-dbquery-dataframe-cast"
    type_id_rules="python-hardcoded-type-id,ts-hardcoded-type-id"
    status=0
    : >"$raw_log"

    ./_scripts/ast_grep_check.sh \
        --json-stream \
        --rules "$non_type_id_rules" \
        >>"$raw_log" 2>&1
    command_status=$?
    if [ "$command_status" -ne 0 ]; then
        status="$command_status"
    fi

    ./_scripts/ast_grep_check.sh \
        --json-stream \
        --rules "$type_id_rules" \
        . \
        >>"$raw_log" 2>&1
    command_status=$?
    if [ "$command_status" -ne 0 ] && [ "$status" -eq 0 ]; then
        status="$command_status"
    fi

    total_findings=$(count_root_ast_grep_findings "$raw_log")
    for i in "${!CHECKS_CMD[@]}"; do
        if ! is_root_ast_grep_batch_check "$i"; then
            continue
        fi

        rule_findings=$(
            write_root_ast_grep_rule_log \
                "$i" \
                "$raw_log" \
                "$status" \
                "$total_findings"
        )
        printf "%s\n" "$rule_findings" \
            >"${RUN_CHECKS_LOG_DIR}/check_${i}.count"
    done

    elapsed_seconds=$((SECONDS - check_started_at))
    printf "%s:%s:%s\n" \
        "$status" \
        "$elapsed_seconds" \
        "$total_findings" \
        >"$status_file"
}

record_root_ast_grep_batch_results() {
    local batch_status="$1"
    local elapsed_seconds="$2"
    local total_findings="$3"
    local rule_findings
    local status
    local count_file
    local i

    shift 3

    for i in "$@"; do
        count_file="${RUN_CHECKS_LOG_DIR}/check_${i}.count"
        rule_findings=0
        if [ -f "$count_file" ]; then
            rule_findings=$(cat "$count_file")
        fi

        if ! [[ "$rule_findings" =~ ^[0-9]+$ ]]; then
            rule_findings=0
        fi

        status=0
        if [ "$batch_status" -ne 0 ] && [ "$total_findings" -eq 0 ]; then
            status="$batch_status"
        elif [ "$rule_findings" -gt 0 ]; then
            status=1
        fi

        record_check_result "$i" "$status" "$elapsed_seconds"
    done
}

# Function to run all registered checks
run_all_checks() {
    local total_checks="${#CHECKS_CMD[@]}"
    local -a parallel_indices=()
    local -a failed_error_indices=()
    local -a failed_warning_indices=()
    local -a parallel_done_by_index=()
    local -a root_ast_grep_indices=()
    local -a check_start_seconds_by_index=()
    local parallel_done=0
    local parallel_total=0
    local root_ast_grep_done=0
    local root_ast_grep_status_file=""
    local i
    local log_file
    local status_file
    local status_payload
    local status
    local elapsed_seconds
    local total_findings
    local check_started_at
    local check_name
    local show_logs_mode="none"
    local post_log_codex_action="none"
    local displayed_failure_mode=""
    local allow_prompt_errors="false"
    local allow_prompt_warnings="false"
    local allow_prompt_codex="false"
    local allow_prompt_successes="false"
    local interactive_codex_mode=""

    if [ "$total_checks" -eq 0 ]; then
        echo -e "${GREEN}No checks were scheduled.${NC}"
        exit 0
    fi

    RUN_CHECKS_LOG_DIR=$(mktemp -d)
    if [[ -z "${RUN_CHECKS_LOG_DIR}" || ! -d "${RUN_CHECKS_LOG_DIR}" ]]; then
        echo -e "${RED}Failed to create temporary directory.${NC}"
        exit 1
    fi
    trap cleanup_run_all_checks EXIT
    trap 'exit 130' INT TERM

    CHECKS_UI_COMPLETED=()
    CHECKS_RESULT_STATUS=()
    CHECKS_ELAPSED_SECONDS=()
    CHECKS_COMPLETED_COUNT=0
    LAST_COMPLETED_CHECK=""
    LIVE_FAILURE_LINES=0

    tput civis 2>/dev/null || true
    render_live_summary

    for i in "${!CHECKS_CMD[@]}"; do
        if is_check_skipped "$i"; then
            update_check_ui_status "$i"
        fi
    done

    if [ "${FAST_FAIL}" = "true" ]; then
        run_fast_fail_checks
    else
        # Phase 0: Run initial checks before any parallel work starts.
        for i in "${!CHECKS_CMD[@]}"; do
            if is_check_skipped "$i"; then
                continue
            fi
            if [ "${CHECKS_IS_PARALLEL[$i]}" = "initial" ]; then
                update_check_ui_running "$i"
                run_sync_check "$i"
            fi
        done

        # Phase 1: Kick off all parallel checks in the background.
        for i in "${!CHECKS_CMD[@]}"; do
            if is_check_skipped "$i"; then
                continue
            fi
            if [ "${CHECKS_IS_PARALLEL[$i]}" = "true" ]; then
                if is_root_ast_grep_batch_check "$i"; then
                    root_ast_grep_indices+=("$i")
                    continue
                fi

                log_file="${RUN_CHECKS_LOG_DIR}/check_${i}.log"
                status_file="${RUN_CHECKS_LOG_DIR}/check_${i}.status"
                parallel_indices+=("$i")
                check_start_seconds_by_index[$i]="$SECONDS"
                update_check_ui_running "$i"
                (
                    execute_check_to_log "$i" "$log_file" "$status_file"
                ) &
            fi
        done

        if [ "${#root_ast_grep_indices[@]}" -gt 0 ]; then
            for i in "${root_ast_grep_indices[@]}"; do
                update_check_ui_running "$i"
            done
            root_ast_grep_status_file="${RUN_CHECKS_LOG_DIR}/root_ast_grep_batch.status"
            (
                execute_root_ast_grep_batch_to_logs \
                    "$root_ast_grep_status_file"
            ) &
        fi

        # Poll status files and update the live summary for each completed check.
        parallel_total=$(( \
            ${#parallel_indices[@]} + ${#root_ast_grep_indices[@]} \
        ))
        while [ "$parallel_done" -lt "$parallel_total" ]; do
            for i in "${parallel_indices[@]}"; do
                if [ "${parallel_done_by_index[$i]:-0}" -eq 1 ]; then
                    continue
                fi

                status_file="${RUN_CHECKS_LOG_DIR}/check_${i}.status"
                if [ -f "$status_file" ]; then
                    status_payload=$(cat "$status_file")
                    status="${status_payload%%:*}"
                    elapsed_seconds="${status_payload#*:}"
                    if ! [[ "$status" =~ ^[0-9]+$ ]]; then
                        continue
                    fi
                    if [ "$status_payload" = "$status" ]; then
                        check_started_at="${check_start_seconds_by_index[$i]:-0}"
                        elapsed_seconds=$((SECONDS - check_started_at))
                    fi
                    if ! [[ "$elapsed_seconds" =~ ^[0-9]+$ ]]; then
                        elapsed_seconds=0
                    fi
                    parallel_done_by_index[$i]=1
                    parallel_done=$((parallel_done + 1))

                    record_check_result "$i" "$status" "$elapsed_seconds"
                fi
            done

            if [ "${#root_ast_grep_indices[@]}" -gt 0 ] \
                && [ "$root_ast_grep_done" -eq 0 ] \
                && [ -f "$root_ast_grep_status_file" ]; then
                status_payload=$(cat "$root_ast_grep_status_file")
                status="${status_payload%%:*}"
                status_payload="${status_payload#*:}"
                elapsed_seconds="${status_payload%%:*}"
                total_findings="${status_payload#*:}"

                if ! [[ "$status" =~ ^[0-9]+$ ]]; then
                    status=1
                fi
                if ! [[ "$elapsed_seconds" =~ ^[0-9]+$ ]]; then
                    elapsed_seconds=0
                fi
                if ! [[ "$total_findings" =~ ^[0-9]+$ ]]; then
                    total_findings=0
                fi

                root_ast_grep_done=1
                parallel_done=$((parallel_done + ${#root_ast_grep_indices[@]}))
                record_root_ast_grep_batch_results \
                    "$status" \
                    "$elapsed_seconds" \
                    "$total_findings" \
                    "${root_ast_grep_indices[@]}"
            fi

            if [ "$parallel_done" -lt "$parallel_total" ]; then
                sleep 0.1
            fi
        done

        # Phase 2: Run sequential checks one at a time, then update in-place.
        for i in "${!CHECKS_CMD[@]}"; do
            if is_check_skipped "$i"; then
                continue
            fi
            if [ "${CHECKS_IS_PARALLEL[$i]}" = "false" ]; then
                update_check_ui_running "$i"
                run_sync_check "$i"
            fi
        done
    fi

    finish_live_summary
    if [ "${#failed_error_indices[@]}" -eq 0 ] \
        && [ "${#failed_warning_indices[@]}" -eq 0 ]; then
        if [ -t 0 ]; then
            show_logs_mode=$(prompt_all_passed_action)
            if [ "$show_logs_mode" = "passed" ]; then
                print_passed_checks
            fi
        else
            echo -e "${GREEN}All checks passed.${NC}"
        fi
        exit 0
    fi

    if [ "${FAST_FAIL}" = "true" ]; then
        print_failed_check_summary
        if [ "${#failed_error_indices[@]}" -gt 0 ]; then
            exit 1
        fi
        echo ""
        echo -e "${PURPLE}Warning checks failed, but error checks passed.${NC}"
        exit 0
    fi

    if [ ! -t 1 ]; then
        print_failed_check_summary
    fi

    if [ -t 0 ]; then
        if [ "${#failed_error_indices[@]}" -gt 0 ]; then
            allow_prompt_errors="true"
        fi
        if [ "${#failed_warning_indices[@]}" -gt 0 ]; then
            allow_prompt_warnings="true"
        fi
        if [ "${#PASSED_CHECKS[@]}" -gt 0 ]; then
            allow_prompt_successes="true"
        fi
        if [ "${CODEX_CONTEXT_MODE}" = "none" ] && codex_cli_available; then
            if [ "$allow_prompt_errors" = "true" ] \
                && [ "$allow_prompt_warnings" = "true" ]; then
                allow_prompt_codex="true"
                interactive_codex_mode="all"
            elif [ "$allow_prompt_errors" = "true" ]; then
                allow_prompt_codex="true"
                interactive_codex_mode="errors"
            elif [ "$allow_prompt_warnings" = "true" ]; then
                allow_prompt_codex="true"
                interactive_codex_mode="warnings"
            fi
        fi

        echo ""
        show_logs_mode=$(
            prompt_failure_action \
                "$allow_prompt_errors" \
                "$allow_prompt_warnings" \
                "$allow_prompt_codex" \
                "$allow_prompt_successes"
        )
        if [ "$show_logs_mode" = "codex" ] \
            && [ -n "$interactive_codex_mode" ]; then
            send_failures_to_codex "$interactive_codex_mode"
        fi
        if [ "$show_logs_mode" = "successes" ]; then
            print_passed_checks
        fi
        if [ "$show_logs_mode" = "errors" ] \
            || [ "$show_logs_mode" = "all" ]; then
            displayed_failure_mode="$show_logs_mode"
            echo ""
            if [ "${#failed_error_indices[@]}" -gt 0 ]; then
                echo -e "${RED}Error failure logs:${NC}"
                echo ""
                for i in "${failed_error_indices[@]}"; do
                    echo -e "${BOLD}${RED}$(get_timed_check_ui_label "$i")${NC}"
                    log_file="${RUN_CHECKS_LOG_DIR}/check_${i}.log"
                    if [ -f "$log_file" ]; then
                        cat "$log_file"
                    else
                        echo "No log file found for this check."
                    fi
                    echo ""
                done
            fi
        fi
        if [ "$show_logs_mode" = "warnings" ] \
            || [ "$show_logs_mode" = "all" ]; then
            displayed_failure_mode="$show_logs_mode"
            echo ""
            if [ "${#failed_warning_indices[@]}" -gt 0 ]; then
                echo -e "${PURPLE}Warning failure logs:${NC}"
                echo ""
                for i in "${failed_warning_indices[@]}"; do
                    echo -e \
                        "${BOLD}${PURPLE}$(get_timed_check_ui_label "$i")${NC}"
                    log_file="${RUN_CHECKS_LOG_DIR}/check_${i}.log"
                    if [ -f "$log_file" ]; then
                        cat "$log_file"
                    else
                        echo "No log file found for this check."
                    fi
                    echo ""
                done
            fi
        fi
        if [ "$allow_prompt_codex" = "true" ] \
            && [ -n "$displayed_failure_mode" ]; then
            echo ""
            post_log_codex_action=$(
                prompt_post_log_codex_action "$displayed_failure_mode"
            )
            if [ "$post_log_codex_action" = "codex" ]; then
                send_failures_to_codex "$displayed_failure_mode"
            fi
        fi
    elif [ "${QUIET}" = "true" ]; then
        echo ""
        echo "Rerun with --verbose to see full output from failing checks."
    fi

    if [ "${CODEX_CONTEXT_MODE}" != "none" ]; then
        send_failures_to_codex "${CODEX_CONTEXT_MODE}"
    fi

    if [ "${#failed_error_indices[@]}" -gt 0 ]; then
        exit 1
    fi

    echo ""
    echo -e "${PURPLE}Warning checks failed, but error checks passed.${NC}"
    exit 0
}

# Detect changes vs dev when running diff-only checks.
DIFF_BASE="dev"
if [ "${RUN_ALL}" = "false" ]; then
    if ! git show-ref --verify --quiet "refs/heads/${DIFF_BASE}"; then
        if git show-ref --verify --quiet "refs/remotes/origin/${DIFF_BASE}"; then
            DIFF_BASE="origin/${DIFF_BASE}"
        else
            RUN_ALL=true
            echo "No dev branch found; running all checks."
        fi
    fi
fi

DIFF_FILES=""
if [ "${RUN_ALL}" = "false" ]; then
    if ! DIFF_FILES="$(
        ./_scripts/diff_files_vs_dev.sh "${DIFF_BASE}"
    )"; then
        RUN_ALL=true
        DIFF_FILES=""
        echo "Failed to detect diff files vs ${DIFF_BASE}; running all checks."
    fi
fi

if [ "${RUN_ALL}" = "false" ] && [ -z "${DIFF_FILES}" ]; then
    echo "No changes detected vs ${DIFF_BASE}."
fi

diff_has() {
    local pattern="$1"
    printf "%s\n" "${DIFF_FILES}" | rg -q "${pattern}"
}

RUN_CORE=false
RUN_API=false
RUN_MICRO=false
RUN_KPI=false
RUN_WEB=false
RUN_PVEEM=false
RUN_ROOT=false
CORE_CHANGED=false
ROOT_PYPROJECT_CHANGED=false
PYPROJECT_CHANGED=false
PACKAGE_JSON_CHANGED=false

RUN_CORE_WARNINGS=false
RUN_WEB_WARNINGS=false
RUN_GLOBAL_WARNINGS=false

if [ "${RUN_ALL}" = "false" ]; then
    if [ -n "${DIFF_FILES}" ]; then
        RUN_ROOT=true
    fi
    if diff_has '^core/'; then
        CORE_CHANGED=true
        RUN_CORE=true
        RUN_API=true
    fi
    if diff_has '^api/'; then
        RUN_API=true
    fi
    if diff_has '^microservices/'; then
        RUN_MICRO=true
    fi
    if diff_has '^kpi/'; then
        RUN_KPI=true
    fi
    if diff_has '^web-app/package\.json$'; then
        PACKAGE_JSON_CHANGED=true
    fi

    if diff_has '^web-app/'; then
        RUN_WEB=true
    fi
    if diff_has '^pv-eem/'; then
        RUN_PVEEM=true
    fi
    if diff_has '(^|/)pyproject\.toml$'; then
        PYPROJECT_CHANGED=true
    fi
    if diff_has '^pyproject\.toml$'; then
        ROOT_PYPROJECT_CHANGED=true
        RUN_API=true
    fi
    if diff_has \
        '^_scripts/|^_tools/|^pyproject\\.toml$|^uv\\.lock$|^\\.mise\\.toml$'; then
        RUN_ALL=true
    fi
fi

if [ "${RUN_ALL}" = "true" ]; then
    RUN_CORE=true
    RUN_API=true
    RUN_MICRO=true
    RUN_KPI=true
    RUN_WEB=true
    RUN_PVEEM=true
    RUN_ROOT=true
fi

if [ "${RUN_CORE}" = "true" ] || [ "${ALL_WARNINGS}" = "true" ]; then
    RUN_CORE_WARNINGS=true
fi

if [ "${RUN_WEB}" = "true" ] || [ "${ALL_WARNINGS}" = "true" ]; then
    RUN_WEB_WARNINGS=true
fi

if [ "${RUN_ROOT}" = "true" ] || [ "${RUN_CORE}" = "true" ] \
    || [ "${RUN_API}" = "true" ] || [ "${RUN_MICRO}" = "true" ] \
    || [ "${RUN_WEB}" = "true" ] \
    || [ "${ALL_WARNINGS}" = "true" ]; then
    RUN_GLOBAL_WARNINGS=true
fi

if [ "${OFFLINE}" = "true" ]; then
    add_skipped_error_check \
        "Root: uv.lock Check" \
        "mise run root:uv_lock_check" \
        "offline mode" \
        "initial"
else
    add_initial_check \
        "Root: uv.lock Check" \
        "mise run root:uv_lock_check"
fi

# Register all checks
if [ "${RUN_CORE}" = "true" ]; then
    if [ "${ROOT_PYPROJECT_CHANGED}" = "true" ]; then
        add_check "Core: Check Task" "mise run core:check" "error" "false"
    else
        add_check "Core: Type Checking (mypy)" "mise run core:types"
        add_db_check "Core: Enum Validation" "mise run core:enum"
        add_check "Core: Unused Import Check" "mise run core:deptry"
        add_check "Core: Dead Code Check" "mise run core:vulture"
        add_check "Core: Pytest" "mise run core:pytest"
    fi
fi

if [ "${RUN_CORE_WARNINGS}" = "true" ]; then
    if [ "${CORE_CHANGED}" != "true" ] \
        && [ "${ALL_WARNINGS}" != "true" ]; then
        add_skipped_warning_check \
            "Core: Version" \
            "mise run core:version-check" \
            "no core changes"
    elif [ "${OFFLINE}" = "true" ]; then
        add_skipped_warning_check \
            "Core: Version" \
            "mise run core:version-check" \
            "offline mode"
    else
        add_warning_check "Core: Version" "mise run core:version-check"
    fi
fi

if [ "${RUN_MICRO}" = "true" ]; then
    add_check "Micro: Type Checking (mypy)" "mise run micro:types"
fi


if [ "${RUN_KPI}" = "true" ]; then
    add_check "KPI: Mypy" "mise run kpi:mypy"
    add_check "KPI: Unused Import Check" "mise run kpi:deptry"
    add_check "KPI: Pytest" "mise run kpi:pytest"
fi

if [ "${RUN_API}" = "true" ]; then
    add_check "API: Dependency Sync" "mise run api:sync" "error" "false"
    add_check "API: Type Checking (mypy)" "mise run api:types"
    add_check "API: Unused Import Check" "mise run api:deptry"
    add_check "API: Dead Code Check" "mise run api:vulture"
    add_check "API: DbQuery.get Check" "mise run api:db_query_get"
    add_check "API: Pytest" "mise run api:pytest"
    add_check "API: Unused Routes Check" \
        "mise run api:unused_routes_detailed"
    add_check "API: Project ID Path Check" "mise run api:project_id_path"
fi

if [ "${RUN_PVEEM}" = "true" ]; then
    if [ "${ROOT_PYPROJECT_CHANGED}" = "true" ]; then
        add_check "PV-EEM: Type Checking (mypy)" "mise run pveem:types"
        add_check "PV-EEM: Ruff" "mise run pveem:ruff"
        add_slow_check "PV-EEM: Pytest" "mise run pveem:pytest"
    else
        add_check "PV-EEM: Type Checking (mypy)" "mise run pveem:types"
        add_slow_check "PV-EEM: Pytest" "mise run pveem:pytest"
    fi
fi

if [ "${RUN_ROOT}" = "true" ]; then
    add_check "Root: Protected Lint Config Changes" \
        "mise run root:lint_config_changes"
    add_check "Root: No package.json" "mise run root:no_package_json"
    add_check "Root: Static Name Shorts Check" \
        "mise run root:static_name_shorts" \
        "error" \
        "false"
    add_check "Root: Pyproject Dependency Check" \
        "mise run root:pyproject_deps"
    if [ "${REQUESTED_DIFF_ONLY}" = "false" ] \
        || [ "${PYPROJECT_CHANGED}" = "true" ]; then
        add_check "Root: Workspace Dependency Check" \
            "mise run root:workspace_deps"
    fi
    add_check "Root: DbQuery Enforcement" \
        "mise run root:dbquery_enforcement"
    add_db_check "Root: Codegen" "mise run root:codegen"
    if [ "${RUN_ALL}" = "true" ] \
        || [ "${ROOT_PYPROJECT_CHANGED}" = "true" ] \
        || [ "${PACKAGE_JSON_CHANGED}" = "true" ]; then
        add_check "Root: pnpm Version Sync" "mise run root:pnpm_version_sync"
    fi

fi

# Global checks
if [ "${RUN_ROOT}" = "true" ] || [ "${RUN_CORE}" = "true" ] \
    || [ "${RUN_API}" = "true" ] || [ "${RUN_MICRO}" = "true" ] \
    || [ "${RUN_WEB}" = "true" ]; then
    add_check "Global: Duplicate Function Names" \
        "mise run root:duplicate_functions"
    add_check "Global: Duplicate Class Names" \
        "mise run root:duplicate_classes"
fi

if [ "${RUN_ROOT}" = "true" ] \
    || [ "${RUN_CORE}" = "true" ] \
    || [ "${RUN_API}" = "true" ] \
    || [ "${RUN_MICRO}" = "true" ] \
    || [ "${RUN_WEB}" = "true" ]; then
    add_batched_ast_grep_check \
        "python-static-type-id" \
        "mise run root:static_type_id" \
        "python-hardcoded-type-id"
    add_batched_ast_grep_check \
        "ts-static-type-id" \
        "mise run root:static_type_id" \
        "ts-hardcoded-type-id"
    add_batched_ast_grep_check \
        "kw-only-args" \
        "mise run root:kw_only_args" \
        "python-enforce-keyword-only-args"
    add_batched_ast_grep_check \
        "docstring-args" \
        "mise run root:docstring_args" \
        "python-missing-args-in-docstring"
    add_batched_ast_grep_check \
        "sa-query-filter" \
        "mise run root:sa_query_filter" \
        "python-disallow-sqlalchemy-query-filter"
    add_batched_ast_grep_check \
        "sa-array-agg" \
        "mise run root:sa_array_agg" \
        "python-disallow-sqlalchemy-array-agg"
    add_batched_ast_grep_check \
        "project-id-access" \
        "mise run root:project_id_access" \
        "fastapi-project-id-requires-access"
    add_batched_ast_grep_check \
        "project-id-prefix" \
        "mise run root:project_id_prefix" \
        "fastapi-project-id-requires-access-prefix"
    add_batched_ast_grep_check \
        "async-db-usage" \
        "mise run root:async_db_usage" \
        "forbidden-with-async-db-usage"
    add_batched_ast_grep_check \
        "dbquery-dataframe-cast" \
        "mise run root:no_dbquery_dataframe_cast" \
        "python-no-dbquery-dataframe-cast"
    add_batched_ast_grep_check \
        "api-logger-definitions" \
        "mise run api:no_logger_definitions" \
        "api-no-python-logger-definitions-outside-logger"
    add_check "Global: Ruff Formatting" "mise run root:ruff_format"
    add_check "Global: Ruff Linting" "mise run root:ruff"
fi

if [ "${RUN_WEB}" = "true" ]; then
    add_check "Web-App: Type Check" "mise run web:typecheck"
    add_check "Web-App: Oxfmt" "mise run web:format"
    add_check "Web-App: Knip" "mise run web:knip"
    add_check "Web-App: Linting" "mise run web:lint"
    add_check "Web-App: Barrel Files" "mise run web:barrel"
    add_check "Web-App: Bulletproof Imports" \
        "mise run web:bulletproof-imports"
fi

if [ "${RUN_WEB_WARNINGS}" = "true" ]; then
    WEB_JSX_CALCS_CHECK_CMD="mise run web:jsx_calcs"
    WEB_QUERY_TIME_ENUM_CHECK_CMD="mise run web:query_time_enum"
    if [ "${ALL_WARNINGS}" = "true" ]; then
        WEB_JSX_CALCS_CHECK_CMD+=" -- --all-files"
        WEB_QUERY_TIME_ENUM_CHECK_CMD+=" -- --all-files"
    fi
    add_warning_check "Web-App: JSX Calculations" \
        "${WEB_JSX_CALCS_CHECK_CMD}"
    add_warning_check "Web-App: Query Time Enum" \
        "${WEB_QUERY_TIME_ENUM_CHECK_CMD}"
fi

# Run all registered checks
run_all_checks
