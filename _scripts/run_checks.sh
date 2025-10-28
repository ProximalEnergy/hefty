#!/bin/bash

# Script to run all quality checks across the monorepo with a summary at the end
# This script runs each check independently and tracks which ones pass/fail

set +e  # Don't exit on first error - we want to run all checks

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

# Run all checks
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
run_check "API: Hurl Tests" "mise run api:hurl"
run_check "Root: No package.json" "check_root_for_package_json"
run_check "Web-App: TypeScript & Format Check" "mise run web:check"
run_check "Web-App: ESLint" "mise run web:lint"

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
