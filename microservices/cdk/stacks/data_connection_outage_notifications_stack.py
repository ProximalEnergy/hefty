"""CDK stack for data connection outage notifications Lambda."""

import os
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
)
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_lambda import Architecture, DockerImageCode, DockerImageFunction
from constructs import Construct

# Secrets Manager secret id (not a credential).
_DEFAULT_SM_SECRET_ID = "microservices/data_connection_outage_notification"  # noqa: S105


class DataConnectionOutageNotificationsStack(Stack):
    """Stack for data connection outage notification Lambda."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the stack.

        Args:
            scope: Parent construct.
            construct_id: Unique identifier for the stack.
            **kwargs: Additional stack properties.
        """
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).parent.parent.parent.parent

        secret_name = os.getenv(
            "DATA_CONNECTION_OUTAGE_SECRET_NAME",
            _DEFAULT_SM_SECRET_ID,
        )

        lambda_function = DockerImageFunction(
            self,
            "DataConnectionOutageNotificationsLambda",
            function_name="data_connection_outage_notifications_image",
            description=("Detects data connection outages and creates notifications"),
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                file=(
                    "microservices/data_connection_outage_notifications_lambda/"
                    "Dockerfile"
                ),
                platform=Platform.LINUX_ARM64,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
                "DATA_CONNECTION_OUTAGE_SECRET_NAME": secret_name,
            },
        )

        sm_arn = (
            f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{secret_name}*"
        )
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[sm_arn],
            )
        )

        ses_identity = "alerts@proximal.energy"
        ses_arn = f"arn:aws:ses:{self.region}:{self.account}:identity/{ses_identity}"
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                    "sesv2:SendEmail",
                ],
                resources=[ses_arn],
            )
        )

        schedule_rule = Rule(
            self,
            "DataConnectionOutageNotificationsSchedule",
            description="Trigger data connection outage notification check",
            schedule=Schedule.rate(Duration.minutes(15)),
        )

        schedule_rule.add_target(LambdaFunction(lambda_function))

        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the data connection outage notifications Lambda",
        )
