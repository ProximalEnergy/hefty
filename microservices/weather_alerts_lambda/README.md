# Weather Alerts Lambda Deployment

This directory contains the AWS Lambda function for weather alert notifications.

## Overview

The Lambda function runs on a schedule (every 30 minutes) to check NWS weather forecast polygons and create notifications for affected projects.

## Deployment

### Deploy with Pinned Core Version

Production deploys must set `CORE_VERSION` so the image installs a pinned
`core` package from CodeArtifact instead of resolving unpinned transitive
dependencies from local source.

To deploy the Lambda function from the `mono` directory:

```bash
# Read the current core version from the repo and fetch a CodeArtifact token
CORE_VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])")
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
  -f microservices/weather_alerts_lambda/Dockerfile \
  -t 016997484973.dkr.ecr.us-east-2.amazonaws.com/nws-weather-notifications:latest \
  --build-arg CORE_VERSION="$CORE_VERSION" \
  --build-arg CODEARTIFACT_TOKEN="$CODEARTIFACT_TOKEN" \
  --build-arg AWS_REGION=us-east-2 \
  --push \
  --provenance=false --sbom=false \
  .

# Update the Lambda function with the new image
aws lambda update-function-code \
  --function-name nws_weather_notifications_image \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/nws-weather-notifications:latest
```

**Note:** Replace the `CORE_VERSION` command if you need a different published
core release. You can list available versions with:

```bash
aws codeartifact list-package-versions \
  --domain proximal-code-artifact-domain \
  --repository proximal-hub \
  --format pypi \
  --package core \
  --sort-by PUBLISHED_TIME
```

### Build from Local Source

For local-only testing, you can still omit `CORE_VERSION`. In that case the
Dockerfile resolves `core` from `../../core` via project metadata while using
the repo root `uv.lock` to pin shared dependencies.

```bash
docker buildx create --name lambda-builder --use >/dev/null 2>&1 || true
docker buildx inspect --bootstrap

docker buildx build --platform linux/arm64 \
  -f microservices/weather_alerts_lambda/Dockerfile \
  -t weather-alerts-test:local \
  --load \
  --provenance=false --sbom=false \
  .
```

## Path Verification

The deployment script assumes:

- Build context: `/Users/robvanhaaren/Desktop/Proximal/mono` (the `mono`
  directory)
- Dockerfile location: `microservices/weather_alerts_lambda/Dockerfile`
  (relative to build context)
- The Dockerfile:
  - Copies `core` and `microservices/weather_alerts_lambda` into build paths
  - Installs the Lambda from `microservices/weather_alerts_lambda/pyproject.toml`
  - Resolves `core` as follows:
    - If `CORE_VERSION` is set: installs `core` from CodeArtifact and ignores
      local `tool.uv.sources`
    - If `CORE_VERSION` is not set: resolves `core` from `../../core` via
      project metadata while constraining shared dependencies with the repo
      root `uv.lock`

All paths are correct and relative to the build context.

**Note:** The Lambda installs from local project metadata for local builds, and
its app logic still lives in `core`, not `api/app`:

- Notification CRUD: `core.crud.admin.notifications`
- Notification type IDs: `core.enumerations.NotificationType` (no DB lookup by
  name)
- Notification utilities: `core.utils.notifications`
- Weather alerts domain: `core.domain.notifications.weather_alerts`
- NWS provider: `core.domain.gis.providers.nws`

## Local Testing

### Test Docker Build

To test the Docker build without pushing to ECR:

```bash
cd /Users/robvanhaaren/Desktop/Proximal/mono

# Build locally (without push)
docker buildx build --platform linux/arm64 \
  -f microservices/weather_alerts_lambda/Dockerfile \
  -t weather-alerts-test:local \
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
  -e NWS_SECRET_NAME=nws/weather/notifications \
  -e ENVIRONMENT=development \
  weather-alerts-test:local \
  python weather_alerts_lambda.py
```

### Test Locally with Python

To test directly with Python (requires dependencies and environment setup):

```bash
cd /Users/robvanhaaren/Desktop/Proximal/mono

# Set up environment variables
export AWS_REGION=us-east-2
export NWS_SECRET_NAME=nws/weather/notifications
export ENVIRONMENT=development

# Run the script
python microservices/weather_alerts_lambda/weather_alerts_lambda.py
```

Note: Local testing requires database credentials and AWS credentials to be
configured.

## Notes

- The Lambda uses ARM64 architecture (`linux/arm64`)
- The image is pushed to ECR in the `us-east-2` region
- The function name is `nws_weather_notifications_image`
- After code changes, you must rebuild and redeploy the Lambda for changes to
  take effect
