#!/bin/bash


set +e  # Don't exit on first error - we want to run all checks
unset VIRTUAL_ENV

# Parse command line arguments
SKIP_TESTS=false
RUN_ALL=false
REQUESTED_DIFF_ONLY=true
OFFLINE=false
QUIET=true
ALL_WARNINGS=false
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
declare -a CHECKS_NAME=()
declare -a CHECKS_CMD=()
declare -a CHECKS_IS_PARALLEL=()
declare -a CHECKS_SEVERITY=()
declare -a CHECKS_SKIP_REASON=()
declare -a CHECKS_UI_LINES_UP=()

# Function to add a check to the list
add_check() {
    local name="$1"
    local cmd="$2"
    local severity="${3:-error}"
    local is_parallel="${4:-true}"

    # Ruff checks and Formatting should run sequentially at the end
    if [[ "$name" == *"Ruff"* ]] || [[ "$name" == *"Formatting"* ]] || [[ "$name" == *"Format"* ]]; then
        is_parallel="false"
    fi

    CHECKS_NAME+=("$name")
    CHECKS_CMD+=("$cmd")
    CHECKS_IS_PARALLEL+=("$is_parallel")
    CHECKS_SEVERITY+=("$severity")
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
    check_index=$((${#CHECKS_NAME[@]} - 1))
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

add_db_check() {
    local name="$1"
    local cmd="$2"

    if [ "${ASYNC_OFFLINE}" = "true" ]; then
        add_skipped_warning_check "$name" "$cmd" "async offline env"
        return 0
    fi

    add_check "$name" "$cmd"
}

# Function to run a check and track its result
run_check() {
    local check_name="$1"
    local check_command="$2"
    local log_file

    if [ "${QUIET}" != "true" ]; then
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}Running: ${check_name}${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        if eval "$check_command"; then
            PASSED_CHECKS+=("$check_name")
            echo -e "${GREEN}✓ ${check_name} passed${NC}\n"
            return 0
        else
            FAILED_ERROR_CHECKS+=("$check_name:$check_command")
            echo -e "${RED}✗ ${check_name} failed${NC}\n"
            return 1
        fi
    fi

    log_file=$(mktemp)
    if eval "$check_command" >"$log_file" 2>&1; then
        PASSED_CHECKS+=("$check_name")
        echo -e "${GREEN}✓ ${check_name} passed${NC}"
        rm -f "$log_file"
        return 0
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Running: ${check_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    cat "$log_file"
    rm -f "$log_file"
    FAILED_ERROR_CHECKS+=("$check_name:$check_command")
    echo -e "${RED}✗ ${check_name} failed${NC}\n"
    return 1
}

cleanup_run_all_checks() {
    tput cnorm 2>/dev/null || true
    if [ -n "${RUN_CHECKS_LOG_DIR:-}" ] && [ -d "${RUN_CHECKS_LOG_DIR}" ]; then
        rm -rf "${RUN_CHECKS_LOG_DIR}"
    fi
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
            echo "check: ${CHECKS_NAME[$i]}"
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

count_errors_in_log() {
    local log_file="$1"
    local match

    if [ ! -f "$log_file" ]; then
        echo 0
        return
    fi

    match=$(
        grep -Eio 'found[[:space:]]+[0-9]+[[:space:]]+errors?' \
            "$log_file" | tail -n 1
    )
    if [ -n "$match" ]; then
        echo "$match" | grep -Eo '[0-9]+' | tail -n 1
        return
    fi

    match=$(
        grep -Eio '[0-9]+[[:space:]]+errors?,[[:space:]]*[0-9]+[[:space:]]+warnings?' \
            "$log_file" | tail -n 1
    )
    if [ -n "$match" ]; then
        echo "$match" | grep -Eo '^[0-9]+'
        return
    fi

    match=$(
        grep -Eio '[0-9]+[[:space:]]+errors?' \
            "$log_file" | tail -n 1
    )
    if [ -n "$match" ]; then
        echo "$match" | grep -Eo '[0-9]+' | tail -n 1
        return
    fi

    match=$(
        grep -Eio '[0-9]+[[:space:]]+fail(ed|ures?)' \
            "$log_file" | tail -n 1
    )
    if [ -n "$match" ]; then
        echo "$match" | grep -Eo '[0-9]+' | tail -n 1
        return
    fi

    match=$(
        grep -Eio '[0-9]+[[:space:]]+finding(s)?' \
            "$log_file" | tail -n 1
    )
    if [ -n "$match" ]; then
        echo "$match" | grep -Eo '[0-9]+' | tail -n 1
        return
    fi

    echo 1
}

get_ui_terminal_columns() {
    local cols=120

    if [ -t 1 ]; then
        cols=$(tput cols 2>/dev/null || echo 120)
    fi

    if ! [[ "$cols" =~ ^[0-9]+$ ]] || [ "$cols" -lt 20 ]; then
        cols=120
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

render_check_ui_line() {
    local color="$1"
    local symbol="$2"
    local label="$3"
    local columns
    local reserved_columns=6
    local max_label_len
    local rendered_label

    columns=$(get_ui_terminal_columns)
    max_label_len=$((columns - reserved_columns))
    if [ "$max_label_len" -lt 1 ]; then
        max_label_len=1
    fi

    rendered_label=$(truncate_ui_label "$label" "$max_label_len")
    printf "\r\033[2K%b%s%b %s\n" \
        "$color" \
        "$symbol" \
        "$NC" \
        "$rendered_label"
}

get_finished_check_ui_label() {
    local check_index="$1"
    local error_count="$2"
    local elapsed_seconds="${3:-0}"
    local skip_reason="${CHECKS_SKIP_REASON[$check_index]:-}"
    local severity="${CHECKS_SEVERITY[$check_index]}"
    local count_suffix="e"
    local elapsed_label

    if [ -n "$skip_reason" ]; then
        echo "$(get_compact_check_ui_label "$check_index")"
        return
    fi

    if [ "$severity" = "warning" ]; then
        count_suffix="w"
    fi

    elapsed_label=$(format_elapsed_seconds "$elapsed_seconds")
    echo "$(get_compact_check_ui_label "$check_index") (${error_count}${count_suffix}, \
${elapsed_label})"
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

init_check_ui_lines_up() {
    local -a error_indices=()
    local -a warning_indices=()
    local i
    local line_no=0
    local total_lines

    for i in "${!CHECKS_NAME[@]}"; do
        if [ "${CHECKS_SEVERITY[$i]}" = "warning" ]; then
            warning_indices+=("$i")
        else
            error_indices+=("$i")
        fi
    done

    if [ "${#error_indices[@]}" -gt 0 ]; then
        echo -e "${BOLD}${RED}Error-level Checks:${NC}"
        line_no=$((line_no + 1))
        for i in "${error_indices[@]}"; do
            render_check_ui_line \
                "${YELLOW}" \
                "●" \
                "$(get_compact_check_ui_label "$i")"
            line_no=$((line_no + 1))
            CHECKS_UI_LINES_UP[$i]="$line_no"
        done
    fi

    if [ "${#warning_indices[@]}" -gt 0 ]; then
        if [ "$line_no" -gt 0 ]; then
            echo ""
            line_no=$((line_no + 1))
        fi
        echo -e "${BOLD}${PURPLE}Warning-level Checks:${NC}"
        line_no=$((line_no + 1))
        for i in "${warning_indices[@]}"; do
            render_check_ui_line \
                "${YELLOW}" \
                "●" \
                "$(get_compact_check_ui_label "$i")"
            line_no=$((line_no + 1))
            CHECKS_UI_LINES_UP[$i]="$line_no"
        done
    fi

    total_lines="$line_no"
    for i in "${!CHECKS_NAME[@]}"; do
        if [ -n "${CHECKS_UI_LINES_UP[$i]:-}" ]; then
            CHECKS_UI_LINES_UP[$i]=$((total_lines - CHECKS_UI_LINES_UP[$i] + 1))
        fi
    done
}

update_check_ui_status() {
    local check_index="$1"
    local exit_code="$2"
    local error_count="$3"
    local elapsed_seconds="${4:-0}"
    local severity="${CHECKS_SEVERITY[$check_index]}"
    local skip_reason="${CHECKS_SKIP_REASON[$check_index]:-}"
    local lines_up="${CHECKS_UI_LINES_UP[$check_index]:-0}"
    local lines_down=$((lines_up - 1))
    local color="$GREEN"
    local symbol="*"
    local check_label

    check_label=$(
        get_finished_check_ui_label \
            "$check_index" \
            "$error_count" \
            "$elapsed_seconds"
    )

    if [ -n "$skip_reason" ]; then
        color="$YELLOW"
        symbol="-"
    elif [ "$exit_code" -ne 0 ]; then
        if [ "$severity" = "warning" ]; then
            color="$PURPLE"
            symbol="?"
        else
            color="$RED"
            symbol="x"
        fi
    fi

    if [ "$lines_up" -le 0 ]; then
        render_check_ui_line "$color" "$symbol" "$check_label"
        return
    fi

    printf "\033[%sA" "$lines_up"
    render_check_ui_line "$color" "$symbol" "$check_label"
    if [ "$lines_down" -gt 0 ]; then
        printf "\033[%sB" "$lines_down"
    fi
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

get_compact_check_ui_label() {
    local check_index="$1"
    get_check_ui_label "$check_index"
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
    local log_file="${RUN_CHECKS_LOG_DIR}/check_${check_index}.log"
    local error_count=0

    if [ "$status" -ne 0 ]; then
        error_count=$(count_errors_in_log "$log_file")
    fi

    update_check_ui_status \
        "$check_index" \
        "$status" \
        "$error_count" \
        "$elapsed_seconds"

    if [ "$status" -eq 0 ]; then
        PASSED_CHECKS+=("${CHECKS_NAME[$check_index]}")
        return
    fi

    if [ "${CHECKS_SEVERITY[$check_index]}" = "warning" ]; then
        FAILED_WARNING_CHECKS+=(
            "${CHECKS_NAME[$check_index]}:${CHECKS_CMD[$check_index]}"
        )
        failed_warning_indices+=("$check_index")
        return
    fi

    FAILED_ERROR_CHECKS+=("${CHECKS_NAME[$check_index]}:${CHECKS_CMD[$check_index]}")
    failed_error_indices+=("$check_index")
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

# Function to run all registered checks
run_all_checks() {
    local total_checks="${#CHECKS_NAME[@]}"
    local -a parallel_indices=()
    local -a failed_error_indices=()
    local -a failed_warning_indices=()
    local -a parallel_done_by_index=()
    local -a check_start_seconds_by_index=()
    local parallel_done=0
    local parallel_total=0
    local i
    local log_file
    local status_file
    local status_payload
    local status
    local elapsed_seconds
    local check_started_at
    local show_logs_mode="none"
    local post_log_codex_action="none"
    local displayed_failure_mode=""
    local allow_prompt_errors="false"
    local allow_prompt_warnings="false"
    local allow_prompt_codex="false"
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

    CHECKS_UI_LINES_UP=()
    init_check_ui_lines_up

    tput civis 2>/dev/null || true

    for i in "${!CHECKS_NAME[@]}"; do
        if is_check_skipped "$i"; then
            update_check_ui_status "$i" 0 0 0
        fi
    done

    # Phase 0: Run initial checks before any parallel work starts.
    for i in "${!CHECKS_NAME[@]}"; do
        if is_check_skipped "$i"; then
            continue
        fi
        if [ "${CHECKS_IS_PARALLEL[$i]}" = "initial" ]; then
            run_sync_check "$i"
        fi
    done

    # Phase 1: Kick off all parallel checks in the background.
    for i in "${!CHECKS_NAME[@]}"; do
        if is_check_skipped "$i"; then
            continue
        fi
        if [ "${CHECKS_IS_PARALLEL[$i]}" = "true" ]; then
            log_file="${RUN_CHECKS_LOG_DIR}/check_${i}.log"
            status_file="${RUN_CHECKS_LOG_DIR}/check_${i}.status"
            parallel_indices+=("$i")
            check_start_seconds_by_index[$i]="$SECONDS"
            (
                execute_check_to_log "$i" "$log_file" "$status_file"
            ) &
        fi
    done

    # Poll status files and update each completed parallel check in-place.
    parallel_total="${#parallel_indices[@]}"
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

        if [ "$parallel_done" -lt "$parallel_total" ]; then
            sleep 0.1
        fi
    done

    # Phase 2: Run sequential checks one at a time, then update in-place.
    for i in "${!CHECKS_NAME[@]}"; do
        if is_check_skipped "$i"; then
            continue
        fi
        if [ "${CHECKS_IS_PARALLEL[$i]}" = "false" ]; then
            run_sync_check "$i"
        fi
    done

    echo ""
    if [ "${#failed_error_indices[@]}" -eq 0 ] \
        && [ "${#failed_warning_indices[@]}" -eq 0 ]; then
        echo -e "${GREEN}All checks passed.${NC}"
        exit 0
    fi

    if [ "${#failed_error_indices[@]}" -gt 0 ]; then
        echo -e "${RED}Failed checks:${NC}"
        echo ""
        for i in "${failed_error_indices[@]}"; do
            echo -e "${BOLD}${RED}$(get_check_ui_label "$i")${NC}"
        done
    fi

    if [ "${#failed_warning_indices[@]}" -gt 0 ]; then
        if [ "${#failed_error_indices[@]}" -gt 0 ]; then
            echo ""
        fi
        echo -e "${PURPLE}Warning checks:${NC}"
        echo ""
        for i in "${failed_warning_indices[@]}"; do
            echo -e "${BOLD}${PURPLE}$(get_check_ui_label "$i")${NC}"
        done
    fi

    if [ -t 0 ]; then
        if [ "${#failed_error_indices[@]}" -gt 0 ]; then
            allow_prompt_errors="true"
        fi
        if [ "${#failed_warning_indices[@]}" -gt 0 ]; then
            allow_prompt_warnings="true"
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
                "$allow_prompt_codex"
        )
        if [ "$show_logs_mode" = "codex" ] \
            && [ -n "$interactive_codex_mode" ]; then
            send_failures_to_codex "$interactive_codex_mode"
        fi
        if [ "$show_logs_mode" = "errors" ] \
            || [ "$show_logs_mode" = "all" ]; then
            displayed_failure_mode="$show_logs_mode"
            echo ""
            if [ "${#failed_error_indices[@]}" -gt 0 ]; then
                echo -e "${RED}Error failure logs:${NC}"
                echo ""
                for i in "${failed_error_indices[@]}"; do
                    echo -e "${BOLD}${RED}$(get_check_ui_label "$i")${NC}"
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
                    echo -e "${BOLD}${PURPLE}$(get_check_ui_label "$i")${NC}"
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

# Function to check for core version bump
check_core_version() {
    echo "Checking for core version bump..."

    # Check for version bump
    # Ensure jq is installed
    if ! command -v jq &> /dev/null
    then
        echo "jq could not be found, please install it."
        return 1
    fi

    current_version=$(
        uv run python - <<'EOF'
import tomllib

print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])
EOF
    )
    echo "Current version in pyproject.toml: $current_version"

    # Configure AWS credentials if not already configured. This assumes the
    # user has configured their AWS CLI.
    # The user might need to run `aws configure` or `aws sso login`.
    # For CI, this would be handled by the CI environment.
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "AWS credentials not configured. Skipping version check."
        return 0
    fi


    aws_output=$(
        aws codeartifact list-package-versions \
            --domain proximal-code-artifact-domain \
            --repository proximal-hub \
            --format pypi \
            --package core \
            --sort-by PUBLISHED_TIME 2>/dev/null || echo '{"versions":[]}'
    )
    latest_version=$(echo $aws_output | jq -r '.versions[0].version')
    echo "Latest published version from CodeArtifact: $latest_version"

    if [ -z "$latest_version" ] || [ "$latest_version" == "null" ]; then
        echo "Could not determine the latest version from CodeArtifact."
        echo "Assuming this is the first release."
        latest_version="0.0.0"
    fi


    (cd core && uv run python - <<EOF
from packaging.version import Version

current = "$current_version"
latest = "$latest_version"

current_release = Version(current).release
latest_release = Version(latest).release

if current_release <= latest_release:
    print(
        "::error::Version check failed. The current version "
        f"({current}) must be greater than the latest published version "
        f"({latest}). Please bump the version in core/pyproject.toml."
    )
    exit(1)

print(f"Version check passed. Current version ({current}) > Latest version ({latest}).")
EOF
    )
    if [ $? -ne 0 ]; then
        return 1
    fi


    return 0
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
    echo "${DIFF_FILES}" | grep -E -q "${pattern}"
}

check_duplicate_classes_for_diff() {
    mise run root:duplicate_classes_diff "${DIFF_BASE}"
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
    if diff_has '^pyproject\.toml$'; then
        ROOT_PYPROJECT_CHANGED=true
        RUN_API=true
    fi
    if diff_has '^_scripts/|^_tools/|^pyproject\\.toml$|^uv\\.lock$|^\\.mise\\.toml$'; then
        RUN_ALL=true
    fi
fi

if [ "${RUN_ALL}" = "true" ]; then
    CORE_CHANGED=true
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
            "check_core_version" \
            "no core changes"
    elif [ "${OFFLINE}" = "true" ]; then
        add_skipped_warning_check \
            "Core: Version" \
            "check_core_version" \
            "offline mode"
    else
        add_warning_check "Core: Version" "check_core_version"
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
fi

if [ "${RUN_PVEEM}" = "true" ]; then
    if [ "${ROOT_PYPROJECT_CHANGED}" = "true" ]; then
        add_check "PV-EEM: Check Task" "mise run pveem:check" "error" "false"
    else
        add_check "PV-EEM: Type Checking (mypy)" "mise run pveem:types"
        add_check "PV-EEM: Pytest" "mise run pveem:pytest"
    fi
fi

if [ "${RUN_ROOT}" = "true" ]; then
    add_check "Root: Protected Lint Config Changes" \
        "mise run root:lint_config_changes"
    add_check "Root: No package.json" "mise run root:no_package_json"
    add_check "Root: Static Type ID Check" \
        "mise run root:static_type_id"
    add_check "Root: Static Name Shorts Check" \
        "mise run root:static_name_shorts"
    add_check "Root: Pyproject Dependency Check" \
        "mise run root:pyproject_dependencies"
    add_db_check "Root: Codegen" "mise run root:codegen"
    if [ "${RUN_ALL}" = "true" ] || [ "${ROOT_PYPROJECT_CHANGED}" = "true" ] || [ "${PACKAGE_JSON_CHANGED}" = "true" ]; then
        add_check "Root: pnpm Version Sync" "mise run root:pnpm_version_sync"
    fi

fi

# Global checks
if [ "${RUN_ROOT}" = "true" ] || [ "${RUN_CORE}" = "true" ] \
    || [ "${RUN_API}" = "true" ] || [ "${RUN_MICRO}" = "true" ] \
    || [ "${RUN_WEB}" = "true" ]; then
    add_check "Global: Duplicate Function Names" \
        "mise run root:duplicate_functions"
fi

if [ "${RUN_GLOBAL_WARNINGS}" = "true" ]; then
    SQLALCHEMY_RETURN_CHECK_CMD="mise run root:sqlalchemy_return"
    if [ "${ALL_WARNINGS}" = "true" ]; then
        SQLALCHEMY_RETURN_CHECK_CMD+=" -- --all-files"
    fi
    add_warning_check "Global: SQLAlchemy Return Methods" \
        "${SQLALCHEMY_RETURN_CHECK_CMD}"
    if [ "${REQUESTED_DIFF_ONLY}" = "true" ] && [ -n "${DIFF_FILES}" ]; then
        add_warning_check "Global: Duplicate Class Names" \
            "check_duplicate_classes_for_diff"
    else
        add_warning_check "Global: Duplicate Class Names" \
            "mise run root:duplicate_classes"
    fi
fi

if [ "${RUN_ROOT}" = "true" ] || [ "${RUN_CORE}" = "true" ] || [ "${RUN_API}" = "true" ] || [ "${RUN_MICRO}" = "true" ] || [ "${RUN_WEB}" = "true" ]; then
    add_check "Global: Semgrep" "mise run root:semgrep"
    add_check "Global: ast-grep" "mise run root:ast_grep"
    add_check "Global: Ruff Formatting" "mise run root:ruff_format"
    add_check "Global: Ruff Linting" "mise run root:ruff"
fi

if [ "${RUN_WEB}" = "true" ]; then
    add_check "Web-App: Type Check" "mise run web:typecheck"
    add_check "Web-App: Prettier Check" "mise run web:prettier"
    add_check "Web-App: Knip" "mise run web:knip"
    add_check "Web-App: Linting" "mise run web:lint"
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
