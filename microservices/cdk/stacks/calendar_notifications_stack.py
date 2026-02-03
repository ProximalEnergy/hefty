"""CDK stack for calendar notifications Lambda function."""

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


class CalendarNotificationsStack(Stack):
    """Stack for calendar notifications Lambda function."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the calendar notifications stack.

        Args:
            scope: Parent construct.
            construct_id: Unique identifier for the stack.
            **kwargs: Additional stack properties.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Get the repository root (mono directory)
        # This assumes CDK is run from the mono directory
        repo_root = Path(__file__).parent.parent.parent.parent

        # Check if CORE_VERSION is set for pinning
        core_version = os.getenv("CORE_VERSION")
        codeartifact_token = os.getenv("CODEARTIFACT_TOKEN")
        aws_region = self.region or "us-east-2"

        # Prepare build args if CORE_VERSION is set
        build_args = {}
        if core_version:
            if not codeartifact_token:
                raise ValueError(
                    "CODEARTIFACT_TOKEN environment variable is required when "
                    "CORE_VERSION is set"
                )
            build_args = {
                "CORE_VERSION": core_version,
                "CODEARTIFACT_TOKEN": codeartifact_token,
                "AWS_REGION": aws_region,
            }

        # Lambda function using Docker image
        lambda_function = DockerImageFunction(
            self,
            "CalendarNotificationsLambda",
            function_name="calendar_notifications_image",
            description="Checks calendar items and sends reminder notifications",
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                file="microservices/calendar_notifications_lambda/Dockerfile",
                platform=Platform.LINUX_ARM64,
                build_args=build_args or None,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                # Note: AWS_REGION is automatically set by Lambda runtime,
                # don't set it here
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
            },
        )

        # Grant Lambda permission to read from Secrets Manager
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:calendar/reminders*"
                ],
            )
        )

        # Grant Lambda permission to send emails via SES (v1 and v2 APIs)
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                    "sesv2:SendEmail",
                ],
                resources=[
                    f"arn:aws:ses:{self.region}:{self.account}:identity/alerts@proximal.energy"
                ],
            )
        )

        # Note: VPC configuration is not needed as the database is publicly
        # accessible via SSL. The Lambda connects using DATABASE_URL from
        # environment variables (loaded from Secrets Manager).

        # EventBridge rule to trigger Lambda daily at 9am ET (14:00 UTC = 9am EST,
        # 10am EDT). Rules are UTC-only; for true 9am ET year-round use Scheduler.
        schedule_rule = Rule(
            self,
            "CalendarNotificationsSchedule",
            description="Trigger calendar notifications check daily",
            schedule=Schedule.cron(minute="0", hour="14"),
        )

        schedule_rule.add_target(LambdaFunction(lambda_function))

        # Output the Lambda function name
        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the calendar notifications Lambda function",
        )
