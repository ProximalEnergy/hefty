#!/bin/bash

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed."
    exit 1
fi

# Source the authentication script
# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
. "$MONO_ROOT/_scripts/auth_aws_codeartifact.sh"

# Simple pass-through to uv add with authentication
exec uv "$@"
