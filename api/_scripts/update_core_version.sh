#!/bin/bash

# Script to update core dependency based on environment
# Usage: ./update_core_version.sh [beta|rc|stable|latest]
# If no argument provided, defaults to "stable"

set -e

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the authentication script
. "$SCRIPT_DIR/auth_aws_codeartifact.sh"

# Get the environment type from argument or default to stable
ENV_TYPE="${1:-stable}"

echo "Updating core dependency for environment: $ENV_TYPE"

# Determine version constraint based on environment
case "$ENV_TYPE" in
    beta|dev)
        echo "Fetching latest beta version..."
        LATEST_VERSION=$(aws codeartifact list-package-versions \
            --package core \
            --domain proximal-code-artifact-domain \
            --domain-owner 016997484973 \
            --repository proximal-hub \
            --sort-by PUBLISHED_TIME \
            --format pypi \
            --status Published \
            --output text \
            --query 'versions[?status==`Published` && contains(version, `b`)] | [0].version' \
        )

        if [ -z "$LATEST_VERSION" ] || [ "$LATEST_VERSION" = "None" ]; then
            echo "No beta version found, falling back to stable"
            ENV_TYPE="stable"
        else
            echo "Installing beta version: $LATEST_VERSION"
            uv add "core==$LATEST_VERSION"
            exit 0
        fi
        ;;

    rc|staging)
        echo "Fetching latest release candidate version..."
        LATEST_VERSION=$(aws codeartifact list-package-versions \
            --package core \
            --domain proximal-code-artifact-domain \
            --domain-owner 016997484973 \
            --repository proximal-hub \
            --sort-by PUBLISHED_TIME \
            --format pypi \
            --status Published \
            --output text \
            --query 'versions[?status==`Published` && contains(version, `rc`)] | [0].version' \
        )

        if [ -z "$LATEST_VERSION" ] || [ "$LATEST_VERSION" = "None" ]; then
            echo "No RC version found, falling back to stable"
            ENV_TYPE="stable"
        else
            echo "Installing RC version: $LATEST_VERSION"
            uv add "core==$LATEST_VERSION"
            exit 0
        fi
        ;;

    stable|main|production)
        echo "Fetching latest stable version..."
        ;;

    latest)
        echo "Fetching absolute latest version (including pre-releases)..."
        LATEST_VERSION=$(aws codeartifact list-package-versions \
            --package core \
            --domain proximal-code-artifact-domain \
            --domain-owner 016997484973 \
            --repository proximal-hub \
            --sort-by PUBLISHED_TIME \
            --format pypi \
            --status Published \
            --output text \
            --query 'versions[?status==`Published`] | [0].version' \
        )

        if [ -z "$LATEST_VERSION" ] || [ "$LATEST_VERSION" = "None" ]; then
            echo "No version found"
            exit 1
        fi

        echo "Installing latest version: $LATEST_VERSION"
        uv add "core==$LATEST_VERSION"
        exit 0
        ;;

    *)
        echo "Error: Unknown environment type '$ENV_TYPE'"
        echo "Usage: $0 [beta|rc|stable|latest]"
        exit 1
        ;;
esac

# If we reach here, we're installing stable
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

if [ -z "$LATEST_STABLE_VERSION" ] || [ "$LATEST_STABLE_VERSION" = "None" ]; then
    echo "Error: No stable version found"
    exit 1
fi

echo "Installing stable version: $LATEST_STABLE_VERSION"
uv add "core==$LATEST_STABLE_VERSION"
