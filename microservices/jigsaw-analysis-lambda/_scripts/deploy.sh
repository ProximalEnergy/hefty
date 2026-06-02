#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/jigsaw-lambda:latest"
LAMBDA_FUNCTION="jigsaw-analysis-docker"

export AWS_PAGER=""

uv sync --project "$MONO_ROOT/microservices/jigsaw-analysis-lambda"

aws ecr get-login-password --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com

docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --push \
  -f "$MONO_ROOT/microservices/jigsaw-analysis-lambda/Dockerfile" \
  -t "$ECR_URI" \
  "$MONO_ROOT"

aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" \
  --image-uri "$ECR_URI" \
  --publish
