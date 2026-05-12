#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Ensure Docker's uv export --frozen will use a current lockfile.
if ! uv lock --check --project "$MONO_ROOT/kpi"; then
  echo "Error: uv.lock is out of date for kpi." >&2
  echo "Run 'uv lock' from the repository root and review the lockfile changes." >&2
  exit 1
fi

# Pre-deploy checks (same as `mise run kpi:mypy` + `mise run kpi:pytest`)
(
  mise run kpi:mypy
  mise run kpi:pytest
  mise run kpi:deptry
)

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest"
LAMBDA_FUNCTION="kpi-pipeline-lambda"

# Disable AWS CLI pager for non-interactive script runs
export AWS_PAGER=""
export AWS_DEFAULT_REGION="us-east-2"
export AWS_REGION="us-east-2"

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is not running." >&2
  echo "Open Docker Desktop and try again." >&2
  exit 1
fi

# Build and publish container image
aws ecr get-login-password --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --push \
  -f "$MONO_ROOT/kpi/Dockerfile" \
  -t "$ECR_URI" \
  "$MONO_ROOT"

# Update Lambda to latest pushed image
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" \
  --image-uri "$ECR_URI" \
  --publish
