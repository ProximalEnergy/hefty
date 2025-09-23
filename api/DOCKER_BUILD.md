# Docker Build Instructions for API with Core Library

This guide explains how to build the API Docker image with proper authentication to install the private `core` library from AWS CodeArtifact.

## Prerequisites

1. **AWS CLI** installed and configured
2. **Docker** installed
3. **AWS credentials** configured (either via AWS Profile or environment variables)
4. Access to the AWS CodeArtifact repository: `proximal-code-artifact-domain-016997484973`

## Quick Start

### Option 1: Using the Build Script (Recommended)

The easiest way to build the Docker image is using the provided build script:

```bash
# Build with default settings
./build-docker.sh

# Build with custom tag
./build-docker.sh --tag v1.0.0

# Build with custom image name and tag
./build-docker.sh --image my-api --tag latest
```

### Option 2: Manual Docker Build

If you prefer to build manually, first get the CodeArtifact authentication token:

```bash
# Get authentication token
export CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
    --domain proximal-code-artifact-domain-016997484973 \
    --domain-owner 016997484973 \
    --region us-east-2 \
    --query authorizationToken \
    --output text)

# Build Docker image
docker build \
    --build-arg UV_INDEX_PROXIMAL_USERNAME=aws \
    --build-arg UV_INDEX_PROXIMAL_PASSWORD="$CODEARTIFACT_TOKEN" \
    -t proximal-api:latest \
    .
```

### Option 3: Using the Simple Dockerfile

For a more straightforward approach, use the alternative Dockerfile:

```bash
# Get authentication token
export CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
    --domain proximal-code-artifact-domain-016997484973 \
    --domain-owner 016997484973 \
    --region us-east-2 \
    --query authorizationToken \
    --output text)

# Build with simple Dockerfile
docker build \
    --build-arg UV_INDEX_PROXIMAL_USERNAME=aws \
    --build-arg UV_INDEX_PROXIMAL_PASSWORD="$CODEARTIFACT_TOKEN" \
    -t proximal-api:latest \
    -f Dockerfile.simple \
    .
```

## AWS Authentication Setup

### Using AWS Profile

```bash
# Configure AWS profile
aws configure --profile your-profile-name
export AWS_PROFILE=your-profile-name
```

### Using Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-2
```

## How It Works

The Docker build process:

1. **Authentication**: Gets a token from AWS CodeArtifact using your AWS credentials
2. **Build Arguments**: Passes the authentication credentials to the Docker build
3. **Private Repository Access**: Uses the credentials to authenticate with the private PyPI index
4. **Core Library Installation**: Downloads and installs the `core==0.2.32` library from your private repository
5. **Application Build**: Installs all other dependencies and builds the complete application

## Troubleshooting

### Common Issues

**Error: "Failed to get CodeArtifact authentication token"**
- Ensure AWS CLI is configured with proper credentials
- Verify you have access to the CodeArtifact domain
- Check that the domain name and region are correct

**Error: "Package not found" during Docker build**
- Verify the `core` library version in `pyproject.toml` exists in the repository
- Check that the PyPI index URL in `pyproject.toml` is correct
- Ensure the authentication token hasn't expired

**Error: "Permission denied"**
- Make sure the build script is executable: `chmod +x build-docker.sh`
- Verify your AWS user/role has CodeArtifact permissions

### Build Script Options

The `build-docker.sh` script supports the following options:

- `-t, --tag TAG`: Set the Docker image tag (default: `latest`)
- `-i, --image NAME`: Set the Docker image name (default: `proximal-api`)
- `-f, --file FILE`: Specify Dockerfile path (default: `Dockerfile`)
- `-h, --help`: Show help message

### Environment Variables

The build process uses these environment variables:

- `UV_INDEX_PROXIMAL_USERNAME`: Username for the private PyPI index (set to `aws`)
- `UV_INDEX_PROXIMAL_PASSWORD`: Authentication token from CodeArtifact
- `AWS_PROFILE`: AWS profile to use (optional)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS credentials (alternative to profile)

## Security Notes

- Authentication tokens are temporary and expire after 12 hours
- Tokens are not stored in the Docker image layers
- Use Docker BuildKit secrets mounting for secure credential handling
- Never commit authentication tokens to version control

## Docker Compose Integration

If you're using Docker Compose, you can integrate the authentication:

```yaml
# docker-compose.yml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        UV_INDEX_PROXIMAL_USERNAME: aws
        UV_INDEX_PROXIMAL_PASSWORD: ${CODEARTIFACT_TOKEN}
    # ... rest of your service configuration
```

Then run:

```bash
export CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
    --domain proximal-code-artifact-domain-016997484973 \
    --domain-owner 016997484973 \
    --region us-east-2 \
    --query authorizationToken \
    --output text)

docker-compose build api
```

## Running the Container

After building, run the container:

```bash
# Run the API
docker run -p 8000:8000 proximal-api:latest

# Run with environment variables
docker run -p 8000:8000 --env-file .env proximal-api:latest

# Run in development mode with volume mounting
docker run -p 8000:8000 -v $(pwd):/app proximal-api:latest
```

The API will be available at `http://localhost:8000`.