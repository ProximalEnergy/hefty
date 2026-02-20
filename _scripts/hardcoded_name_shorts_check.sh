#!/bin/bash
#
# Hardcoded Name Shorts Check Script
# ===================================
#
# This script scans the codebase for hardcoded name_shorts and name_short patterns.
# It helps enforce the use of enums/constants instead of hardcoded string values
# for sensor types, device types, and other name_short identifiers.
#
# Exit Codes:
#   - 0: No hardcoded patterns found (success)
#   - 1: Hardcoded patterns found (failure)
#
# Usage:
#   ./hardcoded_name_shorts_check.sh [--quiet]
#
# Configuration:
#   - FOLDER_PATH_EXCLUDES: Add folder paths to exclude from checks
#   - EXCLUDE_FILES: Add specific files to exclude from checks
#   - IGNORE_COMMENT_PATTERN: Pattern for ignore comments (see below)
#
# Ignore Comments:
#   You can add ignore comments to allow specific usages of hardcoded name_shorts/name_short.
#   This is useful for legitimate cases where hardcoded values are acceptable.
#
#   Supported formats:
#   - Python: # noqa: hardcoded-name-short  or  # allow: hardcoded-name-short
#   - TypeScript/TSX: // noqa: hardcoded-name-short  or  // allow: hardcoded-name-short
#   - Also supports: # noqa: hardcoded-name-long  or  // allow: hardcoded-name-long
#   
#   The comment can be on the same line as the pattern or on the previous line.
#
#   Examples:
#     # Same line comment
#     name_short="test"  # noqa: hardcoded-name-short
#     name_long="test"  # noqa: hardcoded-name-long
#     
#     # Previous line comment
#     # noqa: hardcoded-name-short
#     name_short="test"
#     
#     # TypeScript example
#     name_short: 'test',  // allow: hardcoded-name-short
#
# Patterns Checked:
#   1. Hardcoded name_shorts Arrays (Python) - e.g., sensor_type_name_shorts=["value"]
#   2. Hardcoded name_shorts Arrays (TypeScript/TSX) - e.g., nameShorts: ["value"]
#   3. Hardcoded name_short Assignments (Python) - e.g., name_short="value"
#   4. Hardcoded name_short Assignments (TypeScript/TSX) - e.g., nameShort: "value"

set -euo pipefail

# Runtime options
QUIET=false

for arg in "$@"; do
    case "$arg" in
        --quiet)
            QUIET=true
            ;;
        *)
            echo "Error: Unknown argument '$arg'" >&2
            echo "Usage: $0 [--quiet]" >&2
            exit 2
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

# ============================================================================
# Configuration Section
# ============================================================================

# Default exclude directories (common build/cache dirs that should never be checked)
# These are automatically excluded from all pattern searches
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

# Specific files to exclude from checks
# Add files here that should be excluded (e.g., generated files, schema files)
EXCLUDE_FILES=(
    "web-app/src/api/schema.d.ts"
)

# Folder paths to exclude from checks
# Add folder paths here to ignore entire folders (useful for test data, migrations, etc.)
# Paths are relative to the repository root
FOLDER_PATH_EXCLUDES=(
    "api/_data_insert"  # Data insertion scripts may contain hardcoded values
    "api/_tests"       # Test files may contain hardcoded values for testing
)

# Ignore comment pattern - lines with this comment will be ignored
# This regex pattern matches ignore comments that allow specific hardcoded values
# Supports both Python (#) and TypeScript/TSX (//) style comments
# Examples that will be matched:
#   # noqa: hardcoded-name-short
#   // allow: hardcoded-name-short
#   # noqa: hardcoded-name-long
IGNORE_COMMENT_PATTERN="noqa.*hardcoded.*name.*short|allow.*hardcoded.*name.*short"

# ============================================================================
# Pattern Management
# ============================================================================

# Arrays to store search patterns and their metadata
declare -a PATTERN_NAMES=()        # Human-readable pattern names
declare -a PATTERN_REGEXES=()     # Regex patterns to search for
declare -a PATTERN_DESCRIPTIONS=() # Descriptions of what each pattern checks
declare -a PATTERN_EXCLUDE_DIRS=() # Pattern-specific directory excludes
declare -a EXCLUDE_DIRS=("${DEFAULT_EXCLUDE_DIRS[@]}")

# Function to register a new search pattern
# Arguments:
#   $1: Pattern name (human-readable)
#   $2: Regex pattern to search for
#   $3: Description of what the pattern checks
#   $4+: Optional list of directories to exclude for this specific pattern
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

# Function to filter out matches that have ignore comments
# This function checks each match to see if it has an ignore comment on the
# same line or the previous line, and filters out those matches.
# Arguments:
#   $1: String containing all matches (one per line, format: path:line:content)
# Returns:
#   String containing only matches that don't have ignore comments
filter_ignored_matches() {
    local matches="$1"
    local temp_file=$(mktemp)
    local filtered_matches=""
    
    if [ -z "$matches" ]; then
        echo ""
        return
    fi
    
    # Write matches to temp file for processing
    echo "$matches" > "$temp_file"
    
    # Process each match line
    while IFS= read -r line || [ -n "$line" ]; do
        # Extract file path and line number from match (format: path:line:content)
        # Handle both ./path:line:content and path:line:content formats
        file_path=$(echo "$line" | sed 's|^\./||' | cut -d: -f1)
        line_num=$(echo "$line" | cut -d: -f2)
        
        # Skip if file path or line number extraction failed
        if [ -z "$file_path" ] || [ -z "$line_num" ] || ! [[ "$line_num" =~ ^[0-9]+$ ]]; then
            filtered_matches="${filtered_matches}${line}"$'\n'
            continue
        fi
        
        # Check if file exists
        if [ ! -f "$file_path" ]; then
            filtered_matches="${filtered_matches}${line}"$'\n'
            continue
        fi
        
        # Check current line and previous line for ignore comment
        current_line=$(sed -n "${line_num}p" "$file_path" 2>/dev/null || echo "")
        prev_line_num=$((line_num - 1))
        prev_line=""
        if [ "$prev_line_num" -gt 0 ]; then
            prev_line=$(sed -n "${prev_line_num}p" "$file_path" 2>/dev/null || echo "")
        fi
        
        # Check if ignore comment is present (case-insensitive)
        # Supports both Python (#) and TypeScript/TSX (//) style comments
        if echo "$current_line" | grep -qiE "(#|//).*$IGNORE_COMMENT_PATTERN" || \
           echo "$prev_line" | grep -qiE "(#|//).*$IGNORE_COMMENT_PATTERN"; then
            # Skip this match - it has an ignore comment
            continue
        else
            # Include this match
            filtered_matches="${filtered_matches}${line}"$'\n'
        fi
    done < "$temp_file"
    
    rm -f "$temp_file"
    
    # Remove trailing newline and return
    echo -n "${filtered_matches%$'\n'}"
}

# ============================================================================
# Pattern Definitions
# ============================================================================

# Define all patterns to check for hardcoded name_shorts/name_short values
# Each pattern is registered with a name, regex, description, and optional excludes
load_patterns() {
    add_pattern "Hardcoded name_shorts Arrays (Python)" \
        "\\w+_name_shorts\\s*=\\s*\\[\\s*['\"]" \
        "Checks for hardcoded name_shorts array assignments in Python (e.g., sensor_type_name_shorts=[\"pv_dc_combiner_current\"] or device_type_name_shorts=['meter_active_power'])" \
        "_scripts"
    
    add_pattern "Hardcoded name_shorts Arrays (TypeScript/TSX)" \
        "[a-zA-Z_]*[Nn]ame_?[Ss]horts?\\s*[:=]\\s*\\[\\s*['\"]" \
        "Checks for hardcoded nameShorts/name_shorts array assignments in TypeScript/TSX (e.g., sensorTypeNameShorts: [\"pv_dc_combiner_current\"] or device_name_shorts: ['meter_active_power'])"
    
    add_pattern "Hardcoded name_short Assignments (Python)" \
        "\\w*_?name_short\\s*=\\s*['\"]" \
        "Checks for hardcoded name_short string assignments in Python (e.g., name_short=\"proximal_pv_dc_capacity\" or sensor_type_name_short='meter_active_power')" \
        "_scripts"
    
    add_pattern "Hardcoded name_short Assignments (TypeScript/TSX)" \
        "[a-zA-Z_]*[Nn]ame_?[Ss]hort\\s*[:=]\\s*['\"]" \
        "Checks for hardcoded nameShort/name_short string assignments in TypeScript/TSX (e.g., nameShort: \"proximal_pv_dc_capacity\" or sensor_type_name_short: 'meter_active_power')" \
        ""
}

# ============================================================================
# Main Execution
# ============================================================================

# Load all search patterns
load_patterns

# Initialize tracking variables
OVERALL_FAILED=0
TOTAL_MATCHES=0

if [ "$QUIET" != "true" ]; then
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}    Hardcoded name_shorts/name_short Check          ${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
fi

# Check for required tools
# ripgrep is preferred for speed, but grep is used as a fallback
if ! command -v rg &> /dev/null; then
    if [ "$QUIET" != "true" ]; then
        echo -e "${YELLOW}⚠️  Warning: ripgrep (rg) not found. Falling back to grep (may be slower).${NC}"
        echo -e "${YELLOW}   Install ripgrep for better performance: https://github.com/BurntSushi/ripgrep${NC}\n"
    fi
    USE_RIPGREP=false
else
    if [ "$QUIET" != "true" ]; then
        echo -e "${GREEN}✓ Using ripgrep for fast pattern matching${NC}\n"
    fi
    USE_RIPGREP=true
fi

# Check each pattern
for i in "${!PATTERN_NAMES[@]}"; do
    pattern_name="${PATTERN_NAMES[$i]}"
    pattern_regex="${PATTERN_REGEXES[$i]}"
    pattern_desc="${PATTERN_DESCRIPTIONS[$i]}"
    pattern_exclude_str="${PATTERN_EXCLUDE_DIRS[$i]}"

    if [ "$QUIET" != "true" ]; then
        echo -e "${BLUE}Checking pattern: ${BOLD}${pattern_name}${NC}"
        if [ -n "$pattern_desc" ]; then
            echo -e "  ${BLUE}Description: ${pattern_desc}${NC}"
        fi
        echo -e "  ${BLUE}Pattern: ${pattern_regex}${NC}\n"
    fi

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
        
        # Exclude specific files
        for file in "${EXCLUDE_FILES[@]}"; do
            local_exclude_args+=("--glob" "!$file")
        done
        
        # Exclude folder paths
        for folder_path in "${FOLDER_PATH_EXCLUDES[@]}"; do
            local_exclude_args+=("--glob" "!$folder_path/**")
        done
        
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
        
        # Exclude specific files for grep
        for file in "${EXCLUDE_FILES[@]}"; do
            grep_exclude_args+=("--exclude=$file")
        done
        
        # Exclude folder paths for grep
        for folder_path in "${FOLDER_PATH_EXCLUDES[@]}"; do
            grep_exclude_args+=("--exclude-dir=$(basename "$folder_path")")
            # Also try to exclude by full path pattern
            grep_exclude_args+=("--exclude-dir=$folder_path")
        done
        
        matches=$(grep -rn --color=never "${grep_exclude_args[@]}" -E "$pattern_regex" . 2>/dev/null || true)
    fi
    
    if [ -n "$matches" ]; then
        # Filter out comment lines
        filtered_matches=$(echo "$matches" | grep -v -E "^[[:space:]]*(//|#|\*)" || true)
        if [ -z "$filtered_matches" ]; then
            matches=""
        else
            matches="$filtered_matches"
        fi
        
        # Filter out matches with ignore comments
        if [ -n "$matches" ]; then
            matches=$(filter_ignored_matches "$matches")
        fi
        
        if [ -n "$matches" ]; then
            match_count=$(echo "$matches" | wc -l)
            echo -e "${RED}❌ Found ${match_count} match(es) for pattern '${pattern_name}':${NC}"
            echo -e "${RED}   (Add '# noqa: hardcoded-name-short' or '// noqa: hardcoded-name-short' to ignore specific lines)${NC}"
            echo "$matches" | while IFS= read -r line; do
                # Remove ./ prefix from file paths to make them clickable in IDEs
                cleaned_line=$(echo "$line" | sed 's|^\./||')
                echo -e "  ${RED}${cleaned_line}${NC}"
            done
            echo ""
            TOTAL_MATCHES=$((TOTAL_MATCHES + match_count))
            OVERALL_FAILED=1
        else
            if [ "$QUIET" != "true" ]; then
                echo -e "${GREEN}✓ No matches found for pattern '${pattern_name}'${NC}\n"
            fi
        fi
    else
        if [ "$QUIET" != "true" ]; then
            echo -e "${GREEN}✓ No matches found for pattern '${pattern_name}'${NC}\n"
        fi
    fi
done

# ============================================================================
# Summary and Exit
# ============================================================================

if [ $OVERALL_FAILED -eq 0 ]; then
    if [ "$QUIET" != "true" ]; then
        echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}${GREEN}✓ All hardcoded name_shorts/name_short checks passed!${NC}"
        echo -e "${BOLD}${GREEN}  No hardcoded patterns found in the codebase.${NC}"
        echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    fi
    exit 0
else
    if [ "$QUIET" != "true" ]; then
        echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
    echo -e "${BOLD}${RED}✗ Hardcoded name_shorts/name_short check failed${NC}"
    echo -e "${BOLD}${RED}  Found ${TOTAL_MATCHES} hardcoded pattern(s) that need to be addressed.${NC}"
    echo -e "${BOLD}${YELLOW}  To fix:${NC}"
    echo -e "${BOLD}${YELLOW}    1. Replace hardcoded values with enums/constants where possible${NC}"
    echo -e "${BOLD}${YELLOW}    2. Add ignore comments for legitimate cases:${NC}"
    echo -e "${BOLD}${YELLOW}       Python:   # noqa: hardcoded-name-short${NC}"
    echo -e "${BOLD}${YELLOW}       TS/TSX:   // noqa: hardcoded-name-short${NC}"
    if [ "$QUIET" != "true" ]; then
        echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    else
        echo ""
    fi
    exit 1
fi
