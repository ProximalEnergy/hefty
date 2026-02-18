set -euo pipefail

# Pre-deploy checks (stop on first failure)
mypy src/kpi_pipeline
mypy lambda_function.py
python -m kpi_pipeline.services.calc
python -m kpi_pipeline.services.process

# Deployment configuration
ECR_URI="016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest"
LAMBDA_FUNCTION="kpi-pipeline-lambda"
IMAGE_NAME="kpi-pipeline-image:latest"

# Load AWS/CodeArtifact auth vars
. ./auth_aws_codeartifact.sh


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
  --build-arg UV_INDEX_PROXIMAL_PASSWORD="$UV_INDEX_PROXIMAL_PASSWORD" \
  -t "$IMAGE_NAME" \
  .
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

