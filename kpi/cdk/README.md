# KPI CDK

CDK infrastructure for the KPI pipeline Lambda.

## Current Scope

`KpiLambdaStack` creates a Docker image Lambda named `kpi-lambda`.

It mirrors the existing manually deployed `kpi-pipeline-lambda` runtime settings:

- Python Docker image from `kpi/Dockerfile`
- `arm64`
- 15 minute timeout
- 10240 MB memory
- `/aws/lambda/kpi-lambda` log group
- Secrets Manager read access for the `kpi` secret

Step Functions, EventBridge, and explicit ECR repository management are not yet
included.

## Commands

From this directory:

```bash
uv sync
```

Synthesize:

```bash
CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk@2 synth KpiLambdaStack
```

Deploy:

```bash
CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk@2 deploy KpiLambdaStack
```
