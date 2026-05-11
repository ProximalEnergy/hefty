set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-fetcher-ecr:latest"
LAMBDA_FUNCTION="kpi-pipeline-fetcher-lambda"

# Load AWS/CodeArtifact auth vars
. "$MONO_ROOT/_scripts/auth_aws_codeartifact.sh"

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
INDEX_USER_ARG="UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME=\
${UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME}"
INDEX_PASSWORD_ARG="UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD=\
${UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD}"

aws ecr get-login-password --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --build-arg "${INDEX_USER_ARG}" \
  --build-arg "${INDEX_PASSWORD_ARG}" \
  -t "$ECR_URI" \
  --push \
  .

# Update Lambda to latest pushed image
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" \
  --image-uri "$ECR_URI" \
  --publish
