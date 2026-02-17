#!/bin/bash

#!/bin/bash
set -e

# Source the authentication script
. auth_aws_codeartifact.sh

IMAGE_NAME="kpi-pipeline-image"
ECR_REPOSITORY_NAME="kpi-pipeline-ecr"

echo "Build docker image"

docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --build-arg UV_INDEX_PROXIMAL_USERNAME=$UV_INDEX_PROXIMAL_USERNAME \
  --build-arg UV_INDEX_PROXIMAL_PASSWORD=$UV_INDEX_PROXIMAL_PASSWORD \
  -t $IMAGE_NAME:latest \
  .

aws ecr get-login-password \
  --region us-east-2 | docker login \
  --username AWS \
  --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com

docker tag $IMAGE_NAME:latest 016997484973.dkr.ecr.us-east-2.amazonaws.com/$ECR_REPOSITORY_NAME:latest

docker push 016997484973.dkr.ecr.us-east-2.amazonaws.com/$ECR_REPOSITORY_NAME:latest

aws lambda update-function-code \
  --function-name kpi-pipeline-lambda \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/$ECR_REPOSITORY_NAME:latest \
  --publish

