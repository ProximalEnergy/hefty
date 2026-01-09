#!/bin/bash

# Script to run all quality checks across the monorepo with a summary at the end
# This script runs each check independently and tracks which ones pass/fail

set +e  # Don't exit on first error - we want to run all checks

# Parse command line arguments
SKIP_TESTS=false
RUN_ALL=false
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
    DIFF_FILES=$(git diff --name-only "${DIFF_BASE}...HEAD")
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


# Run all checks
if [ "${RUN_CORE}" = "true" ]; then
    run_check "Core: Version" "check_core_version"
    run_check "Core: Type Checking (mypy)" "mise run core:types"
    run_check "Core: Ruff Linting" "mise run core:ruff_check"
    run_check "Core: Ruff Formatting" "mise run core:ruff_format"
    run_check "Core: Star Syntax Check" "mise run core:star_syntax"
    run_check "Core: SQLAlchemy Query/Filter Check" "mise run core:sqlalchemy"
    run_check "Core: Enum Validation" "mise run core:enum"
    run_check "Core: Unused Import Check" "mise run core:deptry"
    run_check "Core: Dead Code Check" "mise run core:vulture"
    run_check "Core: Docstring Args Check" "mise run core:docstring_args"
fi

if [ "${RUN_MICRO}" = "true" ]; then
    run_check "Micro: Type Checking (mypy)" "mise run micro:types"
    run_check "Micro: Ruff Linting" "mise run micro:ruff_check"
    run_check "Micro: Ruff Formatting" "mise run micro:ruff_format"
    run_check "Micro: Star Syntax Check" "mise run micro:star_syntax"
    run_check "Micro: SQLAlchemy Query/Filter Check" "mise run micro:sqlalchemy"
    run_check "Micro: Docstring Args Check" "mise run micro:docstring_args"
fi

if [ "${RUN_SQL_ADMIN}" = "true" ]; then
    run_check "SQL-Admin: Ruff Linting" "mise run sql-admin:ruff_check"
fi

if [ "${RUN_API}" = "true" ]; then
    run_check "API: Type Checking (mypy)" "mise run api:types"
    run_check "API: Star Syntax Check" "mise run api:star_syntax"
    run_check "API: SQLAlchemy Query/Filter Check" "mise run api:sqlalchemy"
    run_check "API: Ruff Linting" "mise run api:ruff"
    run_check "API: Ruff Formatting" "mise run api:format"
    run_check "API: Unused Import Check" "mise run api:deptry"
    run_check "API: Dead Code Check" "mise run api:vulture"
    run_check "API: DbQuery.get Check" "mise run api:db_query_get"
    run_check "API: _with_async_db Usage Check" "mise run api:with_async_db"
    run_check "API: Pytest" "mise run api:pytest"
    run_check "API: Docstring Args Check" "mise run api:docstring_args"
    run_check "API: Unused Routes Check" \
        "mise run api:unused_routes_detailed"
    run_check "API: Docstring Args Check" "mise run api:docstring_args"
fi

if [ "${RUN_ROOT}" = "true" ]; then
    run_check "Root: No package.json" "check_root_for_package_json"
    run_check "Root: Ruff Linting (_tools)" "mise run tools:ruff"
    run_check "Root: Ruff Formatting (_tools)" "mise run tools:format"
    run_check "Root: Hardcoded Type ID Check" \
        "mise run hardcoded_type_id_check"
    run_check "Root: Hardcoded Name Shorts Check" \
        "mise run hardcoded_name_shorts_check"
    run_check "Root: Codegen" "mise run codegen"
fi

if [ "${RUN_WEB}" = "true" ]; then
    run_check "Web-App: TypeScript & Format Check" "mise run web:check"
    run_check "Web-App: Console Log Check" \
        "mise run web:console_log_check"
fi

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
