#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/cmms-integration-fetcher-docker:latest"
LAMBDA_FUNCTION="cmms-integration-fetcher-lambda"

# Disable AWS CLI pager for non-interactive script runs
export AWS_PAGER=""

# Build and publish container image (context is monorepo root)
aws ecr get-login-password --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --push \
  -f "$MONO_ROOT/microservices/cmms-integration-fetcher/Dockerfile" \
  -t "$ECR_URI" \
  "$MONO_ROOT"

# Update Lambda to latest pushed image
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" \
  --image-uri "$ECR_URI" \
  --publish

