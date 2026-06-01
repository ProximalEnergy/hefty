# KPI CDK

CDK infrastructure for the KPI pipeline Lambdas and Step Functions workflow.

## Current Scope

`KpiLambdaStack` creates:

- A Docker image Lambda named `kpi-lambda`
- A Docker image Lambda named `kpi-fetcher-lambda`
- A Standard Step Functions state machine named `kpi-state-machine`
- An EventBridge Scheduler schedule named `kpi-daily-schedule`

The pipeline Lambda mirrors the existing manually deployed
`kpi-pipeline-lambda` runtime settings:

- Python Docker image from `kpi/Dockerfile`
- `arm64`
- 15 minute timeout
- 10240 MB memory
- `/aws/lambda/kpi-lambda` log group
- Secrets Manager read access for the `kpi` secret

The fetcher Lambda uses:

- Python Docker image from `kpi/Dockerfile.fetcher`
- `arm64`
- 3 minute timeout
- 512 MB memory
- `/aws/lambda/kpi-fetcher-lambda` log group
- Secrets Manager read access for the `kpi` secret

The state machine fetches project/day KPI work items, then runs `kpi-lambda`
with `MaxConcurrency=2`. The daily schedule runs at 2:00 AM
`America/Los_Angeles` with input `{ "backfill_days": 3 }`.

## Commands

From this directory:

```bash
uv sync
```

Synthesize:

```bash
CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk@latest synth KpiLambdaStack
```

Deploy:

```bash
CDK_DISABLE_CLI_TELEMETRY=true npx --yes aws-cdk@latest deploy KpiLambdaStack
```
