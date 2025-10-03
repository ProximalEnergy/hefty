#!/bin/bash
# Pre-commit hook to check for line count limits in two specific files
# Usage: Place this in .git/hooks/pre-commit or use with pre-commit framework

# Define the files to check and their line limits
FILE1="src/hooks/types.ts"
LINE_LIMIT1=762

FILE2="src/hooks/api.ts"
LINE_LIMIT2=1930

# Function to check line count in a file
check_line_count() {
    local file=$1
    local limit=$2

    if [ -f "$file" ]; then
        local line_count=$(wc -l < "$file")
        if [ $line_count -gt $limit ]; then
            echo "ERROR: $file is deprecated, please use new folder structure"
            echo "($line_count lines, limit: $limit)"
            return 1
        else
            echo "OK: $file has $line_count lines (limit: $limit)."
        fi
    else
        echo "INFO: $file does not exist."
    fi
    return 0
}

# Main function
main() {
    local exit_code=0
    echo "Checking line count limits in monitored files..."

    # Check each file
    check_line_count "$FILE1" $LINE_LIMIT1 || exit_code=1
    check_line_count "$FILE2" $LINE_LIMIT2 || exit_code=1

    if [ $exit_code -eq 1 ]; then
        echo "One or more files exceed their line count limit. Commit aborted."
    else
        echo "All files are within their line count limits."
    fi

    exit $exit_code
}

main
