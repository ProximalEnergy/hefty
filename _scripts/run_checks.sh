#!/bin/bash

# Script to run all quality checks across the monorepo with a summary at the end
# This script runs each check independently and tracks which ones pass/fail

set +e  # Don't exit on first error - we want to run all checks

# Parse command line arguments
SKIP_HURL=false
for arg in "$@"; do
    case $arg in
        --static)
            SKIP_HURL=true
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

echo -e "${BOLD}${BLUE}Running all quality checks...${NC}\n"

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
        echo "Error: package.json or package-lock.json found in the root directory. These files should not exist at the monorepo root."
        return 1
    else
        echo "No package.json or package-lock.json found in the root directory. Check passed."
        return 0
    fi
}

# Function to check for core documentation and version bump
check_core_documentation_and_version() {
    echo "Checking for core documentation and version bump..."

    # Check for documentation changes
    if ! git diff --name-only dev...HEAD -- 'core/' | grep -q '^core/_docs/releases/'; then
        if git diff --name-only dev...HEAD -- 'core/' | grep -q -v '^core/_docs/releases/'; then
            echo "::error::Changes were made to 'core/' source files, but no corresponding documentation update was found in 'core/_docs/releases/'. Please add a release note for your changes."
            return 1
        fi
    fi
    echo "Documentation check passed."

    # Check for version bump
    # Ensure jq is installed
    if ! command -v jq &> /dev/null
    then
        echo "jq could not be found, please install it."
        return 1
    fi

    current_version=$(uv run python -c "import tomllib; print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])")
    echo "Current version in pyproject.toml: $current_version"

    # Configure AWS credentials if not already configured. This assumes the user has configured their AWS CLI.
    # The user might need to run `aws configure` or `aws sso login`.
    # For CI, this would be handled by the CI environment.
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "AWS credentials not configured. Skipping version check."
        return 0
    fi


    aws_output=$(aws codeartifact list-package-versions --domain proximal-code-artifact-domain --repository proximal-hub --format pypi --package core --sort-by PUBLISHED_TIME 2>/dev/null || echo '{"versions":[]}')
    latest_version=$(echo $aws_output | jq -r '.versions[0].version')
    echo "Latest published version from CodeArtifact: $latest_version"

    if [ -z "$latest_version" ] || [ "$latest_version" == "null" ]; then
        echo "Could not determine the latest version from CodeArtifact. Assuming this is the first release."
        latest_version="0.0.0"
    fi


    (cd core && uv run python - <<EOF
from packaging.version import parse as V

current = "$current_version"
latest = "$latest_version"

if V(current) <= V(latest):
    print(f"::error::Version check failed. The current version ({current}) must be greater than the latest published version ({latest}). Please bump the version in core/pyproject.toml.")
    exit(1)

print(f"Version check passed. Current version ({current}) > Latest version ({latest}).")
EOF
    )
    if [ $? -ne 0 ]; then
        return 1
    fi


    return 0
}


# Run all checks
run_check "Core: Documentation and Version" "check_core_documentation_and_version"
run_check "Core: Type Checking (mypy)" "mise run core:types"
run_check "Core: Ruff Linting" "mise run core:ruff_check"
run_check "Core: Ruff Formatting" "mise run core:ruff_format"
run_check "Core: Star Syntax Check" "mise run core:star_syntax"
run_check "Core: Enum Validation" "mise run core:enum"
run_check "Core: Unused Import Check" "mise run core:deptry"
run_check "Core: Dead Code Check" "mise run core:vulture"
run_check "API: Type Checking (mypy)" "mise run api:types"
run_check "API: Star Syntax Check" "mise run api:star_syntax"
run_check "API: Ruff Linting" "mise run api:ruff"
run_check "API: Ruff Formatting" "mise run api:format"
run_check "API: Unused Import Check" "mise run api:deptry"
run_check "API: Dead Code Check" "mise run api:vulture"
run_check "API: Pytest" "mise run api:pytest"
if [ "$SKIP_HURL" != "true" ]; then
    run_check "API: Hurl Tests" "mise run api:hurl"
fi
run_check "Root: No package.json" "check_root_for_package_json"
run_check "Root: Hardcoded Type ID Check" "mise run hardcoded_type_id_check"
run_check "Web-App: TypeScript & Format Check" "mise run web:check"

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
