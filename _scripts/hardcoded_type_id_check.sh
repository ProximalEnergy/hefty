#!/bin/bash
# Script to check for hardcoded type IDs across the codebase
# Exits with non-zero code if any matches are found
#
# Usage:
#   ./hardcoded_type_id_check.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default exclude directories (common build/cache dirs)
DEFAULT_EXCLUDE_DIRS=(
    "node_modules"
    "__pycache__"
    ".git"
    ".venv"
    "venv"
    "dist"
    "build"
    ".next"
    ".cache"
    "*.egg-info"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    "_scripts"
)

# Arrays to store patterns
declare -a PATTERN_NAMES=()
declare -a PATTERN_REGEXES=()
declare -a PATTERN_DESCRIPTIONS=()
declare -a PATTERN_EXCLUDE_DIRS=()  # Array of arrays for pattern-specific excludes
declare -a EXCLUDE_DIRS=("${DEFAULT_EXCLUDE_DIRS[@]}")

# Function to add a pattern
add_pattern() {
    local name="$1"
    local pattern="$2"
    local description="${3:-}"
    local pattern_exclude_dirs=("${@:4}")
    
    PATTERN_NAMES+=("$name")
    PATTERN_REGEXES+=("$pattern")
    PATTERN_DESCRIPTIONS+=("$description")
    
    # Store pattern-specific exclude dirs as a space-separated string
    # (bash doesn't support arrays of arrays easily)
    if [ ${#pattern_exclude_dirs[@]} -gt 0 ]; then
        PATTERN_EXCLUDE_DIRS+=("$(IFS=' '; echo "${pattern_exclude_dirs[*]}")")
    else
        PATTERN_EXCLUDE_DIRS+=("")
    fi
}

# Embedded patterns for hardcoded type IDs
load_patterns() {
    add_pattern "Hardcoded Type IDs Arrays (Python)" \
        "\\w+_type_ids\\s*=\\s*\\[\\s*(#|\\d)" \
        "Checks for hardcoded type_ids array assignments in Python (e.g., kpi_type_ids=[18, 19] or multiline with comments)" \
        "_scripts"
    
    add_pattern "Hardcoded Type IDs Arrays (TypeScript/TSX)" \
        "\\w+[Tt]ype[Ii]ds?\\s*[:=]\\s*\\[\\s*['\"]?\\d" \
        "Checks for hardcoded typeIds/type_ids array assignments in TypeScript/TSX (e.g., device_type_ids: [2, 6, 9] or deviceTypeIds: [2])"
    
    add_pattern "Hardcoded Type ID Comparisons" \
        "\\w+_type_id\\s*[!=]==?\\s*\\d+" \
        "Checks for hardcoded type_id comparisons (e.g., first_device_type_id == 29, user_type_id === 1)" \
        "_scripts"
}

# Load patterns
load_patterns

# Track overall result
OVERALL_FAILED=0
TOTAL_MATCHES=0

echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}          Hardcoded Type ID Check                    ${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if ripgrep is available
if ! command -v rg &> /dev/null; then
    echo -e "${YELLOW}Warning: ripgrep (rg) not found. Falling back to grep.${NC}"
    USE_RIPGREP=false
else
    USE_RIPGREP=true
fi

# Check each pattern
for i in "${!PATTERN_NAMES[@]}"; do
    pattern_name="${PATTERN_NAMES[$i]}"
    pattern_regex="${PATTERN_REGEXES[$i]}"
    pattern_desc="${PATTERN_DESCRIPTIONS[$i]}"
    pattern_exclude_str="${PATTERN_EXCLUDE_DIRS[$i]}"
    
    echo -e "${BLUE}Checking pattern: ${BOLD}${pattern_name}${NC}"
    if [ -n "$pattern_desc" ]; then
        echo -e "  ${BLUE}Description: ${pattern_desc}${NC}"
    fi
    echo -e "  ${BLUE}Pattern: ${pattern_regex}${NC}\n"
    
    MATCHES_FOUND=0
    
    if [ "$USE_RIPGREP" = true ]; then
        # Build exclude args for this pattern
        local_exclude_args=()
        
        # Start with default excludes
        for dir in "${EXCLUDE_DIRS[@]}"; do
            local_exclude_args+=("--glob" "!$dir/**")
        done
        
        # Add pattern-specific excludes
        if [ -n "$pattern_exclude_str" ]; then
            read -ra pattern_excludes <<< "$pattern_exclude_str"
            for dir in "${pattern_excludes[@]}"; do
                local_exclude_args+=("--glob" "!$dir/**")
            done
        fi
        
        # Use ripgrep for faster searching
        matches=$(rg -n --color=never "${local_exclude_args[@]}" "$pattern_regex" . 2>/dev/null || true)
    else
        # Fallback to grep
        grep_exclude_args=()
        for dir in "${EXCLUDE_DIRS[@]}"; do
            grep_exclude_args+=("--exclude-dir=$dir")
        done
        
        # Add pattern-specific excludes for grep
        if [ -n "$pattern_exclude_str" ]; then
            read -ra pattern_excludes <<< "$pattern_exclude_str"
            for dir in "${pattern_excludes[@]}"; do
                grep_exclude_args+=("--exclude-dir=$dir")
            done
        fi
        
        matches=$(grep -rn --color=never "${grep_exclude_args[@]}" -E "$pattern_regex" . 2>/dev/null || true)
    fi
    
    if [ -n "$matches" ]; then
        echo -e "${RED}❌ Found matches for pattern '${pattern_name}':${NC}"
        match_count=$(echo "$matches" | wc -l)
        echo "$matches" | while IFS= read -r line; do
            echo -e "  ${RED}${line}${NC}"
        done
        echo ""
        TOTAL_MATCHES=$((TOTAL_MATCHES + match_count))
        OVERALL_FAILED=1
    else
        echo -e "${GREEN}✅ No matches found for pattern '${pattern_name}'${NC}\n"
    fi
done

# Print summary
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $OVERALL_FAILED -eq 0 ]; then
    echo -e "${BOLD}${GREEN}All hardcoded type ID checks passed! ✓${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    exit 0
else
    echo -e "${BOLD}${RED}Hardcoded type ID check failed: Found ${TOTAL_MATCHES} match(es)${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    exit 1
fi

