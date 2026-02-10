#!/bin/bash

# Script to run all quality checks across the monorepo with a summary at the end
# This script runs each check independently and tracks which ones pass/fail

set +e  # Don't exit on first error - we want to run all checks

# Parse command line arguments
SKIP_TESTS=false
RUN_ALL=false
OFFLINE=false
ASYNC_OFFLINE=false
if [ "${AGENT_ENVIRONMENT}" = "async-offline" ]; then
    ASYNC_OFFLINE=true
fi
for arg in "$@"; do
    case $arg in
        --static)
            SKIP_TESTS=true
            shift
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --offline)
            OFFLINE=true
            shift
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}Running relevant quality checks...${NC}\n"

# Arrays to track results
declare -a PASSED_CHECKS=()
declare -a FAILED_CHECKS=()

# Arrays to store checks to be run
declare -a CHECKS_NAME=()
declare -a CHECKS_CMD=()
declare -a CHECKS_IS_PARALLEL=()

# Function to add a check to the list
add_check() {
    local name="$1"
    local cmd="$2"
    local is_parallel="true"

    # Ruff checks and Formatting should run sequentially at the end
    if [[ "$name" == *"Ruff"* ]] || [[ "$name" == *"Formatting"* ]] || [[ "$name" == *"Format"* ]]; then
        is_parallel="false"
    fi

    CHECKS_NAME+=("$name")
    CHECKS_CMD+=("$cmd")
    CHECKS_IS_PARALLEL+=("$is_parallel")
}

add_db_check() {
    local name="$1"
    local cmd="$2"

    if [ "${ASYNC_OFFLINE}" = "true" ]; then
        echo -e "${YELLOW}Skipping ${name} (async offline env)${NC}"
        return 0
    fi

    add_check "$name" "$cmd"
}

# Function to run a check and track its result
run_check() {
    local check_name="$1"
    local check_command="$2"

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Running: ${check_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if eval "$check_command"; then
        PASSED_CHECKS+=("$check_name")
        echo -e "${GREEN}✓ ${check_name} passed${NC}\n"
        return 0
    else
        FAILED_CHECKS+=("$check_name:$check_command")
        echo -e "${RED}✗ ${check_name} failed${NC}\n"
        return 1
    fi
}

# Function to run all registered checks
run_all_checks() {
    local LOG_DIR
    LOG_DIR=$(mktemp -d)
    if [[ -z "$LOG_DIR" || ! -d "$LOG_DIR" ]]; then
        echo -e "${RED}Failed to create temporary directory.${NC}"
        return 1
    fi
    trap 'rm -rf "$LOG_DIR"' EXIT

    local pids=()
    local parallel_indices=()

    # Start parallel checks
    for i in "${!CHECKS_NAME[@]}"; do
        if [ "${CHECKS_IS_PARALLEL[$i]}" = "true" ]; then
            local name="${CHECKS_NAME[$i]}"
            local cmd="${CHECKS_CMD[$i]}"
            local log_file="$LOG_DIR/check_$i.log"
            local status_file="$LOG_DIR/check_$i.status"

            parallel_indices+=("$i")
            (
                # Run the check and capture output
                if eval "$cmd" > "$log_file" 2>&1; then
                    echo 0 > "$status_file"
                else
                    echo $? > "$status_file"
                fi
            ) &
            pids+=($!)
        fi
    done

    # If we have parallel checks, notify the user
    if [ ${#parallel_indices[@]} -gt 0 ]; then
        echo -e "${BLUE}Starting ${#parallel_indices[@]} checks in parallel...${NC}\n"
    fi

    # Wait for parallel checks and print results as they finish
    # To maintain a stable output, we'll wait for them in order
    for idx in "${!parallel_indices[@]}"; do
        local i="${parallel_indices[$idx]}"
        local name="${CHECKS_NAME[$i]}"
        local cmd="${CHECKS_CMD[$i]}"
        local log_file="$LOG_DIR/check_$i.log"
        local status_file="$LOG_DIR/check_$i.status"

        wait "${pids[$idx]}"
        local status
        if [ -f "$status_file" ]; then
            status=$(cat "$status_file")
        else
            status=1 # Indicate failure
            echo -e "${RED}Error: Could not determine status of '${name}'. Status file not found.${NC}" >> "$log_file"
        fi

        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}Finished: ${name}${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        cat "$log_file"

        if [ "$status" -eq 0 ]; then
            PASSED_CHECKS+=("$name")
            echo -e "${GREEN}✓ ${name} passed${NC}\n"
        else
            FAILED_CHECKS+=("$name:$cmd")
            echo -e "${RED}✗ ${name} failed${NC}\n"
        fi
    done

    # Run sequential checks (Ruff, Formatting)
    for i in "${!CHECKS_NAME[@]}"; do
        if [ "${CHECKS_IS_PARALLEL[$i]}" = "false" ]; then
            run_check "${CHECKS_NAME[$i]}" "${CHECKS_CMD[$i]}"
        fi
    done
}

# Function to check for package.json or package-lock.json in the root
check_root_for_package_json() {
    if [ -f "package.json" ] || [ -f "package-lock.json" ]; then
        echo "Error: package.json or package-lock.json found in the root"
        echo "directory. These files should not exist at the monorepo"
        echo "root."
        return 1
    else
        echo "No package.json or package-lock.json found in the root"
        echo "directory. Check passed."
        return 0
    fi
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

# Detect changes vs dev to run only relevant checks
DIFF_BASE="dev"
if ! git show-ref --verify --quiet "refs/heads/${DIFF_BASE}"; then
    if git show-ref --verify --quiet "refs/remotes/origin/${DIFF_BASE}"; then
        DIFF_BASE="origin/${DIFF_BASE}"
    else
        RUN_ALL=true
        echo "No dev branch found; running all checks."
    fi
fi

DIFF_FILES=""
if [ "${RUN_ALL}" = "false" ]; then
    # Include committed, staged, and unstaged changes vs base.
    DIFF_FILES=$(
        {
            git diff --name-only "${DIFF_BASE}...HEAD"
            git diff --name-only HEAD
        } | sort -u
    )
fi

if [ "${RUN_ALL}" = "false" ] && [ -z "${DIFF_FILES}" ]; then
    echo "No changes detected vs ${DIFF_BASE}; skipping checks."
    exit 0
fi

diff_has() {
    local pattern="$1"
    echo "${DIFF_FILES}" | grep -E -q "${pattern}"
}

RUN_CORE=false
RUN_API=false
RUN_MICRO=false
RUN_SQL_ADMIN=false
RUN_WEB=false
RUN_ROOT=false

if [ "${RUN_ALL}" = "false" ]; then
    if diff_has '^core/'; then
        RUN_CORE=true
        RUN_ROOT=true
    fi
    if diff_has '^api/'; then
        RUN_API=true
        RUN_ROOT=true
    fi
    if diff_has '^microservices/'; then
        RUN_MICRO=true
        RUN_ROOT=true
    fi
    if diff_has '^sql-admin/'; then
        RUN_SQL_ADMIN=true
        RUN_ROOT=true
    fi
    if diff_has '^web-app/'; then
        RUN_WEB=true
    fi
    if diff_has '^_scripts/|^_tools/|^pyproject\\.toml$|^uv\\.lock$|^\\.mise\\.toml$'; then
        RUN_ALL=true
    fi
fi

if [ "${RUN_ALL}" = "true" ]; then
    RUN_CORE=true
    RUN_API=true
    RUN_MICRO=true
    RUN_SQL_ADMIN=true
    RUN_WEB=true
    RUN_ROOT=true
fi


# Register all checks
if [ "${RUN_CORE}" = "true" ]; then
    if [ "${OFFLINE}" = "true" ]; then
        echo -e "${YELLOW}Skipping Core: Version (offline mode)${NC}"
    else
        add_check "Core: Version" "check_core_version"
    fi
    add_check "Core: Type Checking (mypy)" "mise run core:types"
    add_db_check "Core: Enum Validation" "mise run core:enum"
    add_check "Core: Unused Import Check" "mise run core:deptry"
    add_check "Core: Dead Code Check" "mise run core:vulture"
    add_check "Core: Docstring Args Check" "mise run core:docstring_args"
fi

if [ "${RUN_MICRO}" = "true" ]; then
    add_check "Micro: Type Checking (mypy)" "mise run micro:types"
    add_check "Micro: Docstring Args Check" "mise run micro:docstring_args"
fi

if [ "${RUN_SQL_ADMIN}" = "true" ]; then
    # We'll handle SQL-Admin linting in the global Ruff check
    :
fi

if [ "${RUN_API}" = "true" ]; then
    add_check "API: Type Checking (mypy)" "mise run api:types"
    add_check "API: Unused Import Check" "mise run api:deptry"
    add_check "API: Dead Code Check" "mise run api:vulture"
    add_check "API: DbQuery.get Check" "mise run api:db_query_get"
    add_check "API: Pytest" "mise run api:pytest"
    add_check "API: Docstring Args Check" "mise run api:docstring_args"
    add_check "API: Unused Routes Check" \
        "mise run api:unused_routes_detailed"
fi

if [ "${RUN_ROOT}" = "true" ]; then
    add_check "Root: No package.json" "check_root_for_package_json"
    add_check "Root: Hardcoded Type ID Check" \
        "mise run hardcoded_type_id_check"
    add_check "Root: Hardcoded Name Shorts Check" \
        "mise run hardcoded_name_shorts_check"
    add_check "Root: Pyproject Dependency Check" \
        "uv run python _scripts/check_pyproject_dependencies.py"
    add_check "Root: Codegen" "mise run codegen"
fi

# Global Checks (Run if any project changed)
if [ "${RUN_ROOT}" = "true" ] || [ "${RUN_CORE}" = "true" ] || [ "${RUN_API}" = "true" ] || [ "${RUN_MICRO}" = "true" ] || [ "${RUN_SQL_ADMIN}" = "true" ] || [ "${RUN_WEB}" = "true" ]; then
    add_check "Global: Semgrep" "mise run semgrep:check"
    add_check "Global: Ruff Linting" "mise run ruff:check"
    add_check "Global: Ruff Formatting" "mise run ruff:format"
    add_check "Tools: Ruff Linting" "mise run tools:ruff"
    add_check "Tools: Ruff Formatting" "mise run tools:format"
fi

if [ "${RUN_WEB}" = "true" ]; then
    add_check "Web-App: Type Check" "cd web-app && npm run check"
    add_check "Web-App: Linting" "cd web-app && npm run lint"
    add_check "Web-App: Console Log Check" \
        "mise run web:console_log_check"
fi

# Run all registered checks
run_all_checks

# Print summary
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}                    CHECK SUMMARY                     ${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Print passed checks
if [ ${#PASSED_CHECKS[@]} -gt 0 ]; then
    echo -e "${BOLD}${GREEN}Passed (${#PASSED_CHECKS[@]}):${NC}"
    for check in "${PASSED_CHECKS[@]}"; do
        echo -e "  ${GREEN}✓${NC} $check"
    done
    echo ""
fi

# Print failed checks
if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "${BOLD}${RED}Failed (${#FAILED_CHECKS[@]}):${NC}"
    for check_info in "${FAILED_CHECKS[@]}"; do
        check_name="${check_info%%:*}"
        check_command="${check_info#*:}"
        echo -e "  ${RED}✗${NC} ${check_name}: ${BOLD}${check_command}${NC}"
    done
    echo ""
fi

# Print overall result
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${BOLD}${GREEN}All checks passed! ✓${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    exit 0
else
    echo -e "${BOLD}${RED}${#FAILED_CHECKS[@]} check(s) failed ✗${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    exit 1
fi
