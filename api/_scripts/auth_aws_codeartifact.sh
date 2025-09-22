#!/bin/bash

# auth_aws_codeartifact.sh - Common AWS CodeArtifact authentication logic
# This script sets up authentication for AWS CodeArtifact and exports necessary environment variables
# Usage: source this script or call it to set up authentication

# --- Checks ---
# Check if AWS CLI is authenticated
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS CLI is not authenticated. Please run 'aws configure' or set up your AWS credentials."
    exit 1
fi

# Check if region is set to us-east-2
# Try to get region from config first, then fall back to environment variables
CURRENT_REGION=$(aws configure get region 2>/dev/null || echo "")
if [ -z "$CURRENT_REGION" ]; then
    CURRENT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-}}"
fi
if [ "$CURRENT_REGION" != "us-east-2" ]; then
    echo "❌ AWS region must be set to us-east-2."
    exit 1
fi

# --- Authentication Logic ---
export AWS_CODEARTIFACT_TOKEN="$(
    aws codeartifact get-authorization-token \
    --domain proximal-code-artifact-domain \
    --domain-owner 016997484973 \
    --query authorizationToken \
    --output text
)"

echo $AWS_CODEARTIFACT_TOKEN

if [ -z "$AWS_CODEARTIFACT_TOKEN" ]; then
    echo "❌ AWS CodeArtifact Token is empty"
    exit 1
fi

# Set UV environment variables for authentication
export UV_INDEX_PROXIMAL_USERNAME=aws
export UV_INDEX_PROXIMAL_PASSWORD="$AWS_CODEARTIFACT_TOKEN"

echo "✅ AWS CodeArtifact authentication successful"
