"""CDK app entry point for KPI infrastructure."""

from __future__ import annotations

import aws_cdk as cdk
from stacks.kpi_lambda_stack import KpiLambdaStack

app = cdk.App()

KpiLambdaStack(
    app,
    "KpiLambdaStack",
    env=cdk.Environment(
        account="016997484973",
        region="us-east-2",
    ),
    description="Lambda function for the KPI pipeline",
)

app.synth()
