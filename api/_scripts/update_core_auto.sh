#!/bin/bash

# Script to automatically detect the current branch and install the appropriate core version
# Usage: ./update_core_auto.sh

set -e

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect current git branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

if [ -z "$CURRENT_BRANCH" ]; then
    echo "Error: Could not detect current git branch"
    exit 1
fi

echo "Current branch: $CURRENT_BRANCH"

# Determine core version type based on branch
case "$CURRENT_BRANCH" in
    dev)
        VERSION_TYPE="beta"
        echo "Dev branch detected - will install beta version"
        ;;
    staging)
        VERSION_TYPE="rc"
        echo "Staging branch detected - will install RC version"
        ;;
    main)
        VERSION_TYPE="stable"
        echo "Main branch detected - will install stable version"
        ;;
    *)
        VERSION_TYPE="stable"
        echo "Unknown branch - defaulting to stable version"
        ;;
esac

# Call the update_core_version.sh script with the detected version type
"$SCRIPT_DIR/update_core_version.sh" "$VERSION_TYPE"
