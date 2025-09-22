#!/bin/bash
# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. "
    exit 1
fi
# Source the authentication script
# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/auth_aws_codeartifact.sh"

# Get the latest stable version (excluding pre-release versions)
LATEST_STABLE_VERSION=$(aws codeartifact list-package-versions \
    --package core \
    --domain proximal-code-artifact-domain \
    --domain-owner 016997484973 \
    --repository proximal-hub \
    --sort-by PUBLISHED_TIME \
    --format pypi \
    --status Published \
    --output text \
    --query 'versions[?status==`Published`] | [?!contains(version, `rc`) && !contains(version, `a`) && !contains(version, `b`) && !contains(version, `dev`)] | [0].version' \
    )

if [ -z "$LATEST_STABLE_VERSION" ]; then
    echo "No stable version found"
    exit 1
fi

echo "Installing core version: $LATEST_STABLE_VERSION"
uv add "core==$LATEST_STABLE_VERSION"
