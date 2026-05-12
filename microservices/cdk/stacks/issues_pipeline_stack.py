"""CDK stack for the automated issues pipeline Lambda."""

import os
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_lambda import Architecture, DockerImageCode, DockerImageFunction
from aws_cdk.aws_logs import LogGroup, RetentionDays
from constructs import Construct

_DEFAULT_SECRET_NAME = "microservices/issues_pipeline"  # noqa: S105


class IssuesPipelineStack(Stack):
    """Stack for the scheduled issues pipeline Lambda."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the issues pipeline stack.

        Args:
            scope: Parent construct.
            construct_id: Unique identifier for the stack.
            **kwargs: Additional stack properties.
        """
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).parent.parent.parent.parent
        function_name = "issues-pipeline"
        secret_name = os.getenv("ISSUES_PIPELINE_SECRET_NAME", _DEFAULT_SECRET_NAME)

        log_group = LogGroup(
            self,
            "IssuesPipelineLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            removal_policy=RemovalPolicy.RETAIN,
            retention=RetentionDays.THREE_MONTHS,
        )

        lambda_function = DockerImageFunction(
            self,
            "IssuesPipelineLambda",
            function_name=function_name,
            description="Runs the automated issues detection pipeline",
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                file="microservices/issues_pipeline_lambda/Dockerfile",
                platform=Platform.LINUX_ARM64,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
                "ISSUES_PIPELINE_SECRET_NAME": secret_name,
            },
            log_group=log_group,
        )

        secret_arn = (
            f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{secret_name}*"
        )
        lambda_function.add_to_role_policy(
            PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[secret_arn],
            )
        )

        schedule_rule = Rule(
            self,
            "IssuesPipelineSchedule",
            description="Trigger the issues pipeline every hour at minute zero",
            enabled=self._schedule_enabled(),
            schedule=Schedule.cron(minute="0"),
        )
        schedule_rule.add_target(LambdaFunction(lambda_function))

        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the issues pipeline Lambda function",
        )
        cdk.CfnOutput(
            self,
            "ScheduleRuleName",
            value=schedule_rule.rule_name,
            description="Name of the issues pipeline EventBridge rule",
        )
        cdk.CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="Name of the issues pipeline CloudWatch log group",
        )

    @staticmethod
    def _schedule_enabled() -> bool:
        raw_value = os.getenv("ISSUES_PIPELINE_SCHEDULE_ENABLED", "true")
        return raw_value.lower() != "false"
