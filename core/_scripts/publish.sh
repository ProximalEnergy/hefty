#!/bin/bash

# A script to build and publish the package to AWS CodeArtifact.
# This script is designed to replicate the publishing steps in the .github/workflows/publish.yml CI/CD pipeline.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# You can change these variables if your setup differs.
AWS_DOMAIN="proximal-code-artifact-domain"
AWS_REGION="us-east-2"
UV_INDEX_NAME="proximal-package-index"

# --- Prerequisite Checks ---
echo "--> Checking for required tools: aws, uv..."

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI (aws) could not be found. Please install and configure it before running this script."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: Astral's uv could not be found. Please install it: https://github.com/astral-sh/uv"
    exit 1
fi

echo "--> All required tools are present."
echo

# --- AWS CodeArtifact Authentication ---
echo "--> Authenticating with AWS CodeArtifact..."
export AWS_CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
  --domain "$AWS_DOMAIN" \
  --region "$AWS_REGION" \
  --query authorizationToken \
  --output text)

if [ -z "$AWS_CODEARTIFACT_TOKEN" ]; then
    echo "Error: Failed to get AWS CodeArtifact token. Please check your AWS credentials and permissions."
    exit 1
fi

echo "--> Successfully authenticated with AWS CodeArtifact."
echo

# --- Set UV Environment Variables ---
# These are named based on the index alias configured in pyproject.toml.
# For example, an index named 'proximal-private-package-index' would require
# UV_INDEX_PROXIMAL_PRIVATE_PACKAGE_INDEX_USERNAME and UV_INDEX_PROXIMAL_PRIVATE_PACKAGE_INDEX_PASSWORD.
echo "--> Setting environment variables for uv..."
export UV_INDEX_PROXIMAL_PRIVATE_PACKAGE_INDEX_USERNAME="aws"
export UV_INDEX_PROXIMAL_PRIVATE_PACKAGE_INDEX_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
export UV_PUBLISH_USERNAME="aws"
export UV_PUBLISH_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
echo "--> Environment variables set."
echo

# --- Build Wheel ---
echo "--> Building the package wheel with uv..."
uv build
echo "--> Build complete."
echo

# --- Publish to AWS CodeArtifact ---
echo "--> Publishing package to AWS CodeArtifact..."
uv publish --index "$UV_INDEX_NAME"
echo "--> Successfully published to AWS CodeArtifact."
echo

echo "✅ Build and publish process completed successfully!"
