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
# Activate venv and deploy the Lambda stack (disable telemetry). From mono/:
source .venv/bin/activate && cd microservices/cdk && CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk deploy WeatherAlertsLambdaStack
```

Or step by step:

```bash
cd microservices/cdk

# Synthesize CloudFormation template
cdk synth

# Deploy the stack
cdk deploy WeatherAlertsLambdaStack

# Or deploy with specific environment variables
NWS_SECRET_NAME=nws/weather/notifications ENVIRONMENT=production cdk deploy WeatherAlertsLambdaStack
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

The stack uses these environment variables (with defaults):

- `NWS_SECRET_NAME`: Secrets Manager secret name (default: `nws/weather/notifications`)
- `ENVIRONMENT`: Environment name (default: `development`)

Set them when deploying:

```bash
NWS_SECRET_NAME=nws/weather/notifications ENVIRONMENT=production cdk deploy
```
