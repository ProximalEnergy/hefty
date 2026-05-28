#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Ensure Docker's uv export --frozen will use a current lockfile.
if ! uv lock --check --project "$MONO_ROOT/kpi"; then
  echo "Error: uv.lock is out of date for kpi." >&2
  echo "Run 'uv lock' from the repository root and review the lockfile changes." >&2
  exit 1
fi

# Pre-deploy checks (same as `mise run kpi:mypy` + `mise run kpi:pytest`)
(
  mise run kpi:mypy
  mise run kpi:pytest
  mise run kpi:deptry
)

# Disable AWS CLI pager for non-interactive script runs
export AWS_PAGER=""
export AWS_DEFAULT_REGION="us-east-2"
export AWS_REGION="us-east-2"
export CDK_DISABLE_CLI_TELEMETRY=true
export JSII_SILENCE_WARNING_DEPRECATED_NODE_VERSION=1

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is not running." >&2
  echo "Open Docker Desktop and try again." >&2
  exit 1
fi

# CDK builds and publishes the image asset, then updates the Lambda stack.
(
  cd "$MONO_ROOT/kpi/cdk"
  uv sync
  npx --yes aws-cdk@2 deploy KpiLambdaStack --require-approval never
)

rm -rf "$MONO_ROOT/kpi/cdk/cdk.out"
