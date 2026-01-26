"""CDK stack for weather alerts Lambda function."""

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


class WeatherAlertsStack(Stack):
    """Stack for weather alerts Lambda function."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the weather alerts stack.

        Args:
            scope: Parent construct.
            construct_id: Unique identifier for the stack.
            **kwargs: Additional stack properties.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Get the repository root (mono directory)
        # This assumes CDK is run from the mono directory
        repo_root = Path(__file__).parent.parent.parent.parent

        # Lambda function using Docker image
        # Note: DockerImageCode.from_image_asset will automatically create
        # an ECR repository for the image. If you want to use an existing
        # repository instead, use DockerImageCode.from_ecr_image() after
        # building and pushing the image separately.
        lambda_function = DockerImageFunction(
            self,
            "WeatherAlertsLambda",
            function_name="nws_weather_notifications_image",
            description=(
                "Checks NWS weather forecast polygons and creates notifications"
            ),
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                file="microservices/weather_alerts_lambda/Dockerfile",
                platform=Platform.LINUX_ARM64,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                # Note: AWS_REGION is automatically set by Lambda runtime,
                # don't set it here
                "NWS_SECRET_NAME": os.getenv(
                    "NWS_SECRET_NAME", "nws/weather/notifications"
                ),
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
            },
        )

        # Grant Lambda permission to read from Secrets Manager
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:nws/weather/notifications*"
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

        # EventBridge rule to trigger Lambda every 30 minutes
        schedule_rule = Rule(
            self,
            "WeatherAlertsSchedule",
            description="Trigger weather alerts check every 30 minutes",
            schedule=Schedule.rate(Duration.minutes(30)),
        )

        schedule_rule.add_target(LambdaFunction(lambda_function))

        # Output the Lambda function name
        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the weather alerts Lambda function",
        )
