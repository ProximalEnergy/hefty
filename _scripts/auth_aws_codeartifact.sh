#!/bin/bash

# Common AWS CodeArtifact authentication logic for this monorepo.
# Source this file to populate credentials for uv package index auth.

DOMAIN_NAME="proximal-code-artifact-domain"
ACCOUNT_ID="016997484973"
REGION="us-east-2"

fail() {
  echo "Error: $1" >&2
  return 1 2>/dev/null || exit 1
}

if ! command -v aws >/dev/null 2>&1; then
  fail "AWS CLI is not installed or not in PATH."
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  fail "AWS credentials are not configured."
fi

export AWS_DEFAULT_REGION="$REGION"
export AWS_REGION="$REGION"

AWS_CODEARTIFACT_TOKEN="$(
  aws codeartifact get-authorization-token \
    --domain "$DOMAIN_NAME" \
    --domain-owner "$ACCOUNT_ID" \
    --region "$REGION" \
    --query authorizationToken \
    --output text
)"

if [ -z "$AWS_CODEARTIFACT_TOKEN" ] || [ "$AWS_CODEARTIFACT_TOKEN" = "None" ]; then
  fail "Failed to retrieve AWS CodeArtifact token."
fi

export AWS_CODEARTIFACT_TOKEN
export UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME="aws"
export UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD="$AWS_CODEARTIFACT_TOKEN"

echo "AWS CodeArtifact authentication configured."
