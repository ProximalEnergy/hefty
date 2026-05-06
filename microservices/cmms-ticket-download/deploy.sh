#!/bin/bash

set -euo pipefail

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SERVICE_DIR/../.." && pwd)"

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/cmms-ticket-download-docker:latest"
LAMBDA_FUNCTION="cmms-ticket-download-lambda"
IMAGE_NAME="cmms-ticket-download-image:latest"

# Disable AWS CLI pager for non-interactive script runs
export AWS_PAGER=""

# Ensure Docker Desktop is open on macOS
open -a Docker

# Wait until Docker daemon is ready (max ~60s)
for _ in {1..30}; do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker info >/dev/null 2>&1

# Build and publish container image
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  -f "$SERVICE_DIR/Dockerfile" \
  -t "$IMAGE_NAME" \
  "$MONO_ROOT"
aws ecr get-login-password --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
docker tag "$IMAGE_NAME" "$ECR_URI"
docker push "$ECR_URI"

# Update Lambda to latest pushed image
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" \
  --image-uri "$ECR_URI" \
  --publish
