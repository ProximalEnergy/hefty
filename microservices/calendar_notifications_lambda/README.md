# Calendar Notifications Lambda Deployment

This directory contains the AWS Lambda function for calendar reminder notifications.

## Overview

The Lambda function runs on a schedule (daily) to check calendar items with `notify_offsets` configured and create notifications for events that need reminders sent today.

## Deployment

### Deploy with Source Code (Default)

To deploy the Lambda function using the current source code, run the following commands from the `mono` directory:

```bash
# Create and configure buildx builder (if it doesn't exist)
docker buildx create --name lambda-builder --use >/dev/null 2>&1 || true
docker buildx inspect --bootstrap

# Build and push the Docker image to ECR
docker buildx build --platform linux/arm64 \
  -f microservices/calendar_notifications_lambda/Dockerfile \
  -t 016997484973.dkr.ecr.us-east-2.amazonaws.com/calendar-notifications:latest \
  --push \
  --provenance=false --sbom=false \
  .

# Update the Lambda function with the new image
aws lambda update-function-code \
  --function-name calendar_notifications_image \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/calendar-notifications:latest
```

### Deploy with Pinned Core Version

To pin a specific version of the `core` package from Code Artifact, you need to:

1. Get a Code Artifact token
2. Build with the `CORE_VERSION` build argument

```bash
# Get Code Artifact token
CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
  --domain proximal-code-artifact-domain \
  --domain-owner 016997484973 \
  --query authorizationToken \
  --output text)

# Create and configure buildx builder (if it doesn't exist)
docker buildx create --name lambda-builder --use >/dev/null 2>&1 || true
docker buildx inspect --bootstrap

# Build and push with pinned core version
docker buildx build --platform linux/arm64 \
  -f microservices/calendar_notifications_lambda/Dockerfile \
  -t 016997484973.dkr.ecr.us-east-2.amazonaws.com/calendar-notifications:latest \
  --build-arg CORE_VERSION=0.3.38 \
  --build-arg CODEARTIFACT_TOKEN="$CODEARTIFACT_TOKEN" \
  --build-arg AWS_REGION=us-east-2 \
  --push \
  --provenance=false --sbom=false \
  .

# Update the Lambda function with the new image
aws lambda update-function-code \
  --function-name calendar_notifications_image \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/calendar-notifications:latest
```

**Note:** Replace `0.3.38` with the desired core version. You can list available versions with:

```bash
aws codeartifact list-package-versions \
  --domain proximal-code-artifact-domain \
  --repository proximal-hub \
  --format pypi \
  --package core \
  --sort-by PUBLISHED_TIME
```

## Path Verification

The deployment script assumes:

- Build context: `/Users/robvanhaaren/Desktop/Proximal/mono` (the `mono` directory)
- Dockerfile location: `microservices/calendar_notifications_lambda/Dockerfile` (relative to build context)
- The Dockerfile:
  - Always copies `microservices/calendar_notifications_lambda/calendar_notifications_lambda.py` → `./calendar_notifications_lambda.py` (Lambda handler)
  - Conditionally handles `core`:
    - If `CORE_VERSION` is set: Installs `core` from Code Artifact and removes the copied source
    - If `CORE_VERSION` is not set: Copies `core/src/core` → `./core` (uses source code)

All paths are correct and relative to the build context.

**Note:** The lambda only depends on `core`, not `api/app`. All calendar notifications functionality is in `core`:

- Notification CRUD: `core.crud.admin.notifications`
- Notification utilities: `core.utils.notifications`
- Calendar notifications domain: `core.domain.notifications.calendar_notifications`

## Local Testing

### Test Docker Build

To test the Docker build without pushing to ECR:

```bash
cd /Users/robvanhaaren/Desktop/Proximal/mono

# Build locally (without push)
docker buildx build --platform linux/arm64 \
  -f microservices/calendar_notifications_lambda/Dockerfile \
  -t calendar-notifications-test:local \
  --load \
  --provenance=false --sbom=false \
  .
```

### Test in Docker Container

To run the Lambda handler in the Docker container (requires AWS credentials):

```bash
# Run the container with AWS credentials and environment variables
docker run --rm \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  -e AWS_REGION=us-east-2 \
  -e ENVIRONMENT=development \
  calendar-notifications-test:local \
  python calendar_notifications_lambda.py
```

### Test Locally with Python

To test directly with Python (requires dependencies and environment setup):

```bash
cd /Users/robvanhaaren/Desktop/Proximal/mono

# Set up environment variables
export AWS_REGION=us-east-2
export ENVIRONMENT=development

# Run the script
python microservices/calendar_notifications_lambda/calendar_notifications_lambda.py
```

Note: Local testing requires database credentials and AWS credentials to be configured.

## Notes

- The Lambda uses ARM64 architecture (`linux/arm64`)
- The image is pushed to ECR in the `us-east-2` region
- The function name is `calendar_notifications_image`
- The function runs daily via EventBridge schedule
- After code changes, you must rebuild and redeploy the Lambda for changes to take effect
