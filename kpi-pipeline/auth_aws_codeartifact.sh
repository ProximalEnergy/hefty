#!/bin/bash

# AWS CodeArtifact Authentication Script
# This script sets up authentication for accessing the core package from AWS CodeArtifact

set -e

DOMAIN_NAME="proximal-code-artifact-domain"
ACCOUNT_ID="016997484973"
REGION="us-east-2"
REPOSITORY_NAME="proximal-hub"

echo "🔐 Authenticating with AWS CodeArtifact..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed or not in PATH"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' or set AWS environment variables."
    exit 1
fi

export AWS_DEFAULT_REGION="$REGION"

echo "📍 Using AWS region: $REGION"
echo "🏢 Using domain: $DOMAIN_NAME"
echo "🗂️  Using repository: $REPOSITORY_NAME"

echo "🎫 Retrieving CodeArtifact authorization token..."
export AWS_CODEARTIFACT_TOKEN="$(
    aws codeartifact get-authorization-token \
    --domain "$DOMAIN_NAME" \
    --domain-owner "$ACCOUNT_ID" \
    --region "$REGION" \
    --query authorizationToken \
    --output text
)"

if [ -z "$AWS_CODEARTIFACT_TOKEN" ]; then
    echo "❌ Failed to retrieve CodeArtifact authorization token"
    exit 1
fi

export UV_INDEX_PROXIMAL_USERNAME=aws
export UV_INDEX_PROXIMAL_PASSWORD="$AWS_CODEARTIFACT_TOKEN"

echo "✅ AWS CodeArtifact authentication configured successfully"
echo "🔑 Token set for UV authentication"

# Export variables for use in other scripts
# echo "export AWS_CODEARTIFACT_TOKEN=\"$AWS_CODEARTIFACT_TOKEN\""
# echo "export UV_INDEX_PROXIMAL_USERNAME=aws"
# echo "export UV_INDEX_PROXIMAL_PASSWORD=\"$AWS_CODEARTIFACT_TOKEN\""
