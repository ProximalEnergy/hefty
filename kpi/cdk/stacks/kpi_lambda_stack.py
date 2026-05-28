"""CDK stack for the KPI pipeline Lambda."""

from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Duration, IgnoreMode, RemovalPolicy, Stack
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_lambda import Architecture, DockerImageCode, DockerImageFunction
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_secretsmanager import Secret
from constructs import Construct

_FUNCTION_NAME = "kpi-lambda"
_SECRET_NAME = "kpi"  # noqa: S105
_IMAGE_ASSET_EXCLUDES = [
    ".cursor",
    ".git",
    ".vscode",
    "api",
    "docs-mdbook",
    "forecast",
    "issues",
    "microservices",
    "pv-eem",
    "super-admin",
    "third-party",
    "web-app",
    "core/_alembic_migrations",
    "core/requirements.txt",
    "kpi/.cursor",
    "kpi/.vscode",
    "kpi/_data",
    "kpi/_sandbox",
    "kpi/cdk",
    "kpi/docs",
    "kpi/templates",
    "kpi/tests",
]


class KpiLambdaStack(Stack):
    """Stack for the KPI pipeline Lambda."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the KPI Lambda stack.

        Args:
            scope: Parent construct.
            construct_id: Unique identifier for the stack.
            **kwargs: Additional stack properties.
        """
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).parent.parent.parent.parent

        log_group = LogGroup(
            self,
            "KpiLambdaLogGroup",
            log_group_name=f"/aws/lambda/{_FUNCTION_NAME}",
            removal_policy=RemovalPolicy.RETAIN,
            retention=RetentionDays.THREE_MONTHS,
        )

        lambda_function = DockerImageFunction(
            self,
            "KpiLambda",
            function_name=_FUNCTION_NAME,
            description="Runs the KPI pipeline",
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                exclude=_IMAGE_ASSET_EXCLUDES,
                file="kpi/Dockerfile",
                ignore_mode=IgnoreMode.DOCKER,
                platform=Platform.LINUX_ARM64,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(15),
            memory_size=10240,
            log_group=log_group,
        )

        secret = Secret.from_secret_name_v2(self, "KpiSecret", _SECRET_NAME)
        secret.grant_read(lambda_function)

        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the KPI Lambda function",
        )
        cdk.CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="Name of the KPI Lambda log group",
        )
