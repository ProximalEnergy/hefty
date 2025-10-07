#!/bin/bash
# Script to update core dependency in mono-repo setup
# This uses the local editable core dependency from ../core

set -e

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CORE_PATH="$(cd "$PROJECT_ROOT/../core" && pwd)"

# Verify we're in a mono-repo setup
if [ ! -d "$CORE_PATH" ]; then
    echo "Error: Core directory not found at $CORE_PATH"
    echo "This script expects the mono-repo structure with core at ../core"
    exit 1
fi

echo "Mono-repo detected: Using local core from $CORE_PATH"

# Check if pyproject.toml has the correct workspace configuration
if ! grep -q 'core = { path = "../core"' "$PROJECT_ROOT/pyproject.toml"; then
    echo "Warning: pyproject.toml may not have the correct workspace configuration"
    echo "Expected: core = { path = \"../core\", editable = true }"
fi

# Sync dependencies (this will use the local core)
echo "Syncing dependencies with local core..."
cd "$PROJECT_ROOT"
uv sync

echo "✓ Successfully synced with local core dependency"
echo "Core version: $(cd "$CORE_PATH" && git describe --tags --always 2>/dev/null || echo 'unknown')"
