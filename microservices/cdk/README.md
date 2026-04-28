# CDK Infrastructure for Microservices

This directory contains AWS CDK infrastructure code for deploying microservices, including the weather alerts Lambda function.

## Prerequisites

1. Install AWS CDK CLI:

   ```bash
   npm install -g aws-cdk
   ```

2. Install Python dependencies:

   ```bash
   cd microservices/cdk
   uv sync
   ```

3. Bootstrap CDK in your AWS account (first time only):
   ```bash
   cdk bootstrap aws://016997484973/us-east-2
   ```

## Weather Alerts Lambda

The `WeatherAlertsStack` deploys:

- ECR repository for the Docker image
- Lambda function with Docker image
- EventBridge schedule (every 30 minutes)
- IAM permissions for Secrets Manager access

### Deployment

From the `mono` directory:

```bash
export CORE_VERSION="$(
  python3 -c "import tomllib; print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])"
)"
export CODEARTIFACT_TOKEN="$(aws codeartifact get-authorization-token \
  --domain proximal-code-artifact-domain \
  --domain-owner 016997484973 \
  --query authorizationToken \
  --output text)"

# Activate venv and deploy the Lambda stack (disable telemetry). From mono/:
source .venv/bin/activate && cd microservices/cdk && CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk deploy WeatherAlertsLambdaStack
```

Or step by step:

```bash
export CORE_VERSION="$(
  python3 -c "import tomllib; print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])"
)"
export CODEARTIFACT_TOKEN="$(aws codeartifact get-authorization-token \
  --domain proximal-code-artifact-domain \
  --domain-owner 016997484973 \
  --query authorizationToken \
  --output text)"

cd microservices/cdk

# Synthesize CloudFormation template
cdk synth

# Deploy the stack
cdk deploy WeatherAlertsLambdaStack

# Or deploy with specific environment variables
NWS_SECRET_NAME=nws/weather/notifications ENVIRONMENT=production \
  cdk deploy WeatherAlertsLambdaStack
```

### What CDK Does

1. **Builds and pushes Docker image**: CDK automatically builds the Docker image from the Dockerfile and pushes it to ECR
2. **Creates Lambda function**: Deploys the Lambda function with the Docker image
3. **Sets up schedule**: Configures EventBridge to trigger the Lambda every 30 minutes
4. **Configures permissions**: Grants the Lambda permission to read from Secrets Manager

### Updating the Lambda

After making code changes:

```bash
cd microservices/cdk
cdk deploy WeatherAlertsLambdaStack
```

CDK will automatically rebuild the Docker image and update the Lambda function.

### Useful Commands

- `cdk synth` - Synthesize CloudFormation template
- `cdk deploy` - Deploy the stack
- `cdk diff` - Compare deployed stack with current state
- `cdk destroy` - Delete the stack
- `cdk ls` - List all stacks

### Environment Variables

The stack uses these environment variables:

- `CORE_VERSION`: required; pinned `core` package version for the Docker build
- `CODEARTIFACT_TOKEN`: required; token used to install pinned `core`
- `NWS_SECRET_NAME`: optional; defaults to `nws/weather/notifications`
- `ENVIRONMENT`: optional; defaults to `development`

Set them when deploying:

```bash
CORE_VERSION="$(
  python3 -c "import tomllib; print(tomllib.load(open('core/pyproject.toml', 'rb'))['project']['version'])"
)" \
CODEARTIFACT_TOKEN="$(aws codeartifact get-authorization-token \
  --domain proximal-code-artifact-domain \
  --domain-owner 016997484973 \
  --query authorizationToken \
  --output text)" \
NWS_SECRET_NAME=nws/weather/notifications \
ENVIRONMENT=production \
cdk deploy WeatherAlertsLambdaStack
```

## Issues Pipeline Lambda

The `IssuesPipelineLambdaStack` deploys:

- CDK-managed ECR image asset for the issues pipeline Docker image
- Lambda function named `issues-pipeline`
- EventBridge rule that invokes the Lambda hourly
- CloudWatch log group `/aws/lambda/issues-pipeline`
- Secrets Manager access for the issues pipeline secret

### Required Configuration

The image build creates fresh `core` and `issues` wheels from the local repo
contents at deploy time. No CodeArtifact token or published `core` wheel is
required.

The Lambda loads runtime configuration from Secrets Manager. By default it uses
`microservices/issues_pipeline`. The secret must be a JSON object containing
`DATABASE_URL`, for example:

```json
{
  "DATABASE_URL": "postgresql://...",
  "ENVIRONMENT": "production"
}
```

The secret is already set.

Optional:

```bash
export ISSUES_PIPELINE_SCHEDULE_ENABLED="false"
```

Setting `ISSUES_PIPELINE_SCHEDULE_ENABLED=false` disables the EventBridge integration, such that the Lambda may only be invoked manually.

### Deployment

From the `mono` directory:

```bash
cd microservices/cdk
uv sync

source .venv/bin/activate

CDK_DISABLE_CLI_TELEMETRY=true \
  npx --yes aws-cdk deploy IssuesPipelineLambdaStack
```

### Manual Validation

Invoke a controlled project run before enabling the hourly schedule:

```bash
aws lambda invoke \
  --function-name issues-pipeline \
  /tmp/issues-pipeline-response.json
```

The Lambda logs may be inspected in AWS CloudWatch, under `aws/lambda/issues-pipeline`.