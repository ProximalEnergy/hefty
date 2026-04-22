#!/usr/bin/env bash

# Build and publish the package to AWS CodeArtifact.
# This mirrors the temp-artifact flow used in CI.

set -euo pipefail

# --- Configuration ---
# You can change these variables if your setup differs.
AWS_DOMAIN="proximal-code-artifact-domain"
AWS_REGION="us-east-2"
CODEARTIFACT_HOST="proximal-code-artifact-domain-016997484973.d."\
"codeartifact.us-east-2.amazonaws.com"
UV_PUBLISH_URL="https://$CODEARTIFACT_HOST/pypi/proximal-hub/"
UV_PUBLISH_CHECK_URL="https://$CODEARTIFACT_HOST/pypi/proximal-hub/simple/"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CORE_DIR/.." && pwd)"
BUILD_ROOT="$(mktemp -d)"
BUILD_DIR="$BUILD_ROOT/core"

cleanup() {
    rm -rf "$BUILD_ROOT"
}

trap cleanup EXIT

# --- Prerequisite Checks ---
echo "--> Checking for required tools: aws, python3, uv..."

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI (aws) is required. Install and configure it first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required. Install it before running this script."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv is required. Install it: https://github.com/astral-sh/uv"
    exit 1
fi

echo "--> All required tools are present."
echo

VERSION="$(awk -F'"' '/^version = / { print $2; exit }' "$CORE_DIR/pyproject.toml")"

if [ -z "$VERSION" ]; then
    echo "Error: Could not determine the core package version."
    exit 1
fi

# --- AWS CodeArtifact Authentication ---
echo "--> Authenticating with AWS CodeArtifact..."
export AWS_CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
  --domain "$AWS_DOMAIN" \
  --region "$AWS_REGION" \
  --query authorizationToken \
  --output text)

if [ -z "$AWS_CODEARTIFACT_TOKEN" ]; then
    echo "Error: Failed to get AWS CodeArtifact token. Check AWS auth first."
    exit 1
fi

echo "--> Successfully authenticated with AWS CodeArtifact."
echo

# --- Set UV Environment Variables ---
# These are named from the root pyproject index alias: proximal-package-index.
echo "--> Setting environment variables for uv..."
export UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME="aws"
export UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
export UV_PUBLISH_USERNAME="aws"
export UV_PUBLISH_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
export UV_PUBLISH_URL
export UV_PUBLISH_CHECK_URL
echo "--> Environment variables set."
echo

echo "--> Preparing temporary core publish artifact..."
cp -R "$CORE_DIR" "$BUILD_DIR"

python3 "$REPO_ROOT/_scripts/prepare_core_publish_artifact.py" inject \
  --root-pyproject "$REPO_ROOT/pyproject.toml" \
  --core-pyproject "$CORE_DIR/pyproject.toml" \
  --build-pyproject "$BUILD_DIR/pyproject.toml" \
  --version "$VERSION"

echo "--> Prepared temporary publish artifact in $BUILD_DIR."
echo

# --- Build Wheel ---
echo "--> Building the package wheel with uv..."
(
  cd "$BUILD_DIR"
  uv build --out-dir dist
)
echo "--> Build complete."
echo

echo "--> Verifying built wheel metadata..."
shopt -s nullglob
wheels=("$BUILD_DIR"/dist/*.whl)

if [ "${#wheels[@]}" -ne 1 ]; then
    echo "Error: Expected exactly one built wheel, found ${#wheels[@]}."
    exit 1
fi

python3 "$REPO_ROOT/_scripts/prepare_core_publish_artifact.py" verify-wheel \
  --root-pyproject "$REPO_ROOT/pyproject.toml" \
  --core-pyproject "$CORE_DIR/pyproject.toml" \
  --wheel "${wheels[0]}"
echo "--> Wheel metadata matches the root-managed dependency pins."
echo

# --- Publish to AWS CodeArtifact ---
echo "--> Publishing package to AWS CodeArtifact..."
(
  cd "$BUILD_DIR"
  uv publish \
    --publish-url "$UV_PUBLISH_URL" \
    --check-url "$UV_PUBLISH_CHECK_URL" \
    dist/*
)
echo "--> Successfully published to AWS CodeArtifact."
echo

echo "✅ Build and publish process completed successfully!"
