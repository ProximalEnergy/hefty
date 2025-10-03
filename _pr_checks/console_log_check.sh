#!/bin/bash
# Pre-commit hook to block TypeScript files containing console.log statements in the src folder

# Check if src directory exists
if [ ! -d "src" ]; then
    echo "Warning: 'src' directory not found"
    exit 0
fi

# Find all TypeScript files in the src directory
ts_files=$(find src -type f -name "*.ts" -o -name "*.tsx")

if [ -z "$ts_files" ]; then
    echo "No TypeScript/TSX files found in the src folder."
    exit 0
fi

found_console=0

for file in $ts_files; do
    # Look for console.log statements, excluding comments and strings where possible
    matches=$(grep -n "console.log(" "$file" | grep -v "^\s*//" | grep -v "\`console.log(" | grep -v "'console.log(" | grep -v "\"console.log(")

    if [ ! -z "$matches" ]; then
        echo "❌ File $file contains console.log statements:"
        echo "$matches"
        found_console=1
    fi
done

if [ $found_console -eq 1 ]; then
    echo "Commit rejected. Please remove console.log statements before committing."
    exit 1
else
    echo "✅ No console.log statements found in src TypeScript/TSX files."
    exit 0
fi
