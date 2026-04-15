set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "$(git -C "$MONO_ROOT" status --short)" ]]; then
  echo "Error: deployment requires a clean git working tree." >&2
  echo "Commit or stash all changes before running deploy." >&2
  exit 1
fi

# Pre-deploy checks (same as `mise run kpi:mypy` + `mise run kpi:pytest`)
(
  mise run kpi:mypy
  mise run kpi:pytest
)

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest"
LAMBDA_FUNCTION="kpi-pipeline-lambda"
IMAGE_NAME="kpi-pipeline-image:latest"

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
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --load \
  -t "$IMAGE_NAME" \
  -f "$SCRIPT_DIR/Dockerfile" \
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
