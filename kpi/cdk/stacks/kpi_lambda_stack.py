"""CDK stack for the KPI pipeline Lambda."""

from __future__ import annotations

import json
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Duration, IgnoreMode, RemovalPolicy, Stack
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_iam import PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_lambda import Architecture, DockerImageCode, DockerImageFunction
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_scheduler import CfnSchedule
from aws_cdk.aws_secretsmanager import Secret
from aws_cdk.aws_stepfunctions import (
    DefinitionBody,
    IChainable,
    JitterType,
    Map,
    ProcessorMode,
    QueryLanguage,
    StateMachine,
    StateMachineType,
    TaskInput,
)
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke
from constructs import Construct

_PIPELINE_FUNCTION_NAME = "kpi-lambda"
_FETCHER_FUNCTION_NAME = "kpi-fetcher-lambda"
_STATE_MACHINE_NAME = "kpi-state-machine"
_SCHEDULE_NAME = "kpi-daily-schedule"
_SECRET_NAME = "kpi"  # noqa: S105
_STATE_MACHINE_COMMENT = (
    "event payload is \n"
    "{\n"
    "    start: str = [today],\n"
    "    end: str = [today],\n"
    "    backfill_days: int = 0,\n"
    "    project_name_short_list: list[str] | None = None,\n"
    "    kpi_type_ids: list[KPIType] | None = None\n"
    "}"
)
_LAMBDA_RETRY_ERRORS = [
    "Lambda.ServiceException",
    "Lambda.AWSLambdaException",
    "Lambda.SdkClientException",
    "Lambda.TooManyRequestsException",
]
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

        pipeline_log_group = LogGroup(
            self,
            "KpiLambdaLogGroup",
            log_group_name=f"/aws/lambda/{_PIPELINE_FUNCTION_NAME}",
            removal_policy=RemovalPolicy.RETAIN,
            retention=RetentionDays.THREE_MONTHS,
        )

        pipeline_lambda_function = DockerImageFunction(
            self,
            "KpiLambda",
            function_name=_PIPELINE_FUNCTION_NAME,
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
            log_group=pipeline_log_group,
        )

        fetcher_log_group = LogGroup(
            self,
            "KpiFetcherLambdaLogGroup",
            log_group_name=f"/aws/lambda/{_FETCHER_FUNCTION_NAME}",
            removal_policy=RemovalPolicy.RETAIN,
            retention=RetentionDays.THREE_MONTHS,
        )

        fetcher_lambda_function = DockerImageFunction(
            self,
            "KpiFetcherLambda",
            function_name=_FETCHER_FUNCTION_NAME,
            description="Builds KPI pipeline Step Functions inputs",
            code=DockerImageCode.from_image_asset(
                directory=str(repo_root),
                exclude=_IMAGE_ASSET_EXCLUDES,
                file="kpi/Dockerfile.fetcher",
                ignore_mode=IgnoreMode.DOCKER,
                platform=Platform.LINUX_ARM64,
            ),
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(3),
            memory_size=512,
            log_group=fetcher_log_group,
        )

        secret = Secret.from_secret_name_v2(self, "KpiSecret", _SECRET_NAME)
        secret.grant_read(pipeline_lambda_function)
        secret.grant_read(fetcher_lambda_function)

        definition = _state_machine_definition(
            scope=self,
            fetcher_lambda_function=fetcher_lambda_function,
            pipeline_lambda_function=pipeline_lambda_function,
        )

        state_machine = StateMachine(
            self,
            "KpiStateMachine",
            comment=_STATE_MACHINE_COMMENT,
            state_machine_name=_STATE_MACHINE_NAME,
            state_machine_type=StateMachineType.STANDARD,
            definition_body=DefinitionBody.from_chainable(definition),
            query_language=QueryLanguage.JSONATA,
        )

        scheduler_role = Role(
            self,
            "KpiSchedulerRole",
            assumed_by=ServicePrincipal("scheduler.amazonaws.com"),
        )
        scheduler_role.add_to_policy(
            PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        schedule = CfnSchedule(
            self,
            "KpiDailySchedule",
            name=_SCHEDULE_NAME,
            description="Runs kpi pipeline for the previous 3 days",
            flexible_time_window=CfnSchedule.FlexibleTimeWindowProperty(
                maximum_window_in_minutes=30,
                mode="FLEXIBLE",
            ),
            schedule_expression="cron(0 2 * * ? *)",
            schedule_expression_timezone="America/Los_Angeles",
            state="ENABLED",
            target=CfnSchedule.TargetProperty(
                arn=state_machine.state_machine_arn,
                input=json.dumps({"backfill_days": 3}, indent=4),
                retry_policy=CfnSchedule.RetryPolicyProperty(
                    maximum_event_age_in_seconds=86400,
                    maximum_retry_attempts=0,
                ),
                role_arn=scheduler_role.role_arn,
            ),
        )

        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=pipeline_lambda_function.function_name,
            description="Name of the KPI Lambda function",
        )
        cdk.CfnOutput(
            self,
            "LogGroupName",
            value=pipeline_log_group.log_group_name,
            description="Name of the KPI Lambda log group",
        )
        cdk.CfnOutput(
            self,
            "FetcherLambdaFunctionName",
            value=fetcher_lambda_function.function_name,
            description="Name of the KPI fetcher Lambda function",
        )
        cdk.CfnOutput(
            self,
            "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="ARN of the KPI Step Functions state machine",
        )
        cdk.CfnOutput(
            self,
            "ScheduleName",
            value=schedule.name or _SCHEDULE_NAME,
            description="Name of the KPI daily schedule",
        )


def _state_machine_definition(
    *,
    scope: Construct,
    fetcher_lambda_function: DockerImageFunction,
    pipeline_lambda_function: DockerImageFunction,
) -> IChainable:
    """Return the KPI Step Functions chain.

    Args:
        scope: Construct scope for state definitions.
        fetcher_lambda_function: Fetcher Lambda function.
        pipeline_lambda_function: Pipeline Lambda function.

    Returns:
        Chainable Step Functions definition.
    """
    fetch_inputs = _lambda_invoke_state(
        scope=scope,
        construct_id="FetchKpiPipelineInputs",
        state_name="Fetch KPI Pipeline Inputs",
        lambda_function=fetcher_lambda_function,
    )
    run_pipeline = _lambda_invoke_state(
        scope=scope,
        construct_id="RunKpiPipelinePerProjectPerDay",
        state_name="Run KPI Pipeline per Project per Day",
        lambda_function=pipeline_lambda_function,
    )

    map_state = Map(
        scope,
        "KpiPipelineMap",
        max_concurrency=2,
        query_language=QueryLanguage.JSONATA,
        state_name="Map",
    )
    map_state.item_processor(run_pipeline, mode=ProcessorMode.INLINE)

    return fetch_inputs.next(map_state)


def _lambda_invoke_state(
    *,
    scope: Construct,
    construct_id: str,
    state_name: str,
    lambda_function: DockerImageFunction,
) -> LambdaInvoke:
    """Create a JSONata Lambda invoke state with the shared retry policy.

    Args:
        scope: Construct scope for the state.
        construct_id: Construct identifier.
        state_name: State name rendered in ASL.
        lambda_function: Lambda function to invoke.

    Returns:
        Lambda invoke state.
    """
    state = LambdaInvoke(
        scope,
        construct_id,
        lambda_function=lambda_function,
        payload=TaskInput.from_text("{% $states.input %}"),
        outputs="{% $states.result.Payload %}",
        query_language=QueryLanguage.JSONATA,
        retry_on_service_exceptions=False,
        state_name=state_name,
    )
    state.add_retry(
        errors=_LAMBDA_RETRY_ERRORS,
        interval=Duration.seconds(1),
        max_attempts=3,
        backoff_rate=2,
        jitter_strategy=JitterType.FULL,
    )
    return state
