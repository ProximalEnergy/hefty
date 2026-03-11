import os
from hashlib import sha256
from typing import cast

import json5
from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct


class PVEEMStack(Stack):
    """PVEEMStack."""

    VALID_ENVIRONMENTS = {"DEV", "STAGE", "PROD", "VALIDATE"}

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Default Configuration Values ---
        default_config = {
            "simulation_temporal_mode": "instantaneous",
            "soiling": "measured",
            "degradation": "none",
            "dc_wiring_to_combiner": "target_stc",
            "dc_wiring_to_inverter": "target_stc",
        }

        # --- Project Configurations ---
        config_path = os.path.join(
            os.path.dirname(__file__),
            "project_configs.json5",
        )
        with open(config_path, encoding="utf-8") as f:
            project_configs_raw = json5.load(f)

        # Apply defaults to each project config
        project_configs = []
        for config in project_configs_raw:
            full_config = default_config.copy()
            full_config.update(config)
            project_configs.append(full_config)

        image_tag = self._get_image_tag()
        runtime_environment = self._get_runtime_environment()
        simulation_function = self._build_simulation_lambda(
            image_tag=image_tag,
            runtime_environment=runtime_environment,
        )

        # --- EventBridge Rules ---
        for index, config in enumerate(project_configs):
            project_name = config["project_name_short"]

            events.Rule(
                self,
                f"{project_name.replace('_', '-')}-5min-trigger-rule-{index}",
                rule_name=f"{project_name.replace('_', '-')}-5min-trigger-{index}",
                description=f"{project_name} simulations at 5 minute intervals",
                schedule=events.Schedule.cron(
                    minute=self._get_staggered_5_minute_slot(
                        project_name_short=project_name,
                    )
                ),
                targets=[
                    cast(
                        events.IRuleTarget,
                        targets.LambdaFunction(
                            simulation_function,
                            event=events.RuleTargetInput.from_object({"body": config}),
                        ),
                    )
                ],
            )

    @staticmethod
    def _get_staggered_5_minute_slot(*, project_name_short: str) -> str:
        digest = sha256(project_name_short.encode("utf-8")).digest()
        minute_offset = int.from_bytes(digest[:2], byteorder="big") % 5 + 1
        return f"{minute_offset}/5"

    def _get_image_tag(self) -> str:
        context_image_tag = self.node.try_get_context("imageTag")
        if isinstance(context_image_tag, str) and context_image_tag:
            return context_image_tag

        env_image_tag = os.getenv("PVEEM_IMAGE_TAG")
        if env_image_tag:
            return env_image_tag

        return "latest"

    def _get_runtime_environment(self) -> str:
        raw_runtime_environment = self.node.try_get_context("runtimeEnvironment")
        if raw_runtime_environment is None:
            raw_runtime_environment = os.getenv("PVEEM_RUNTIME_ENVIRONMENT")

        if raw_runtime_environment is None:
            return "PROD"

        if not isinstance(raw_runtime_environment, str):
            raise ValueError("runtimeEnvironment must be a string")

        runtime_environment = raw_runtime_environment.strip().upper()
        if runtime_environment not in self.VALID_ENVIRONMENTS:
            valid_environments = ", ".join(sorted(self.VALID_ENVIRONMENTS))
            raise ValueError(f"runtimeEnvironment must be one of {valid_environments}")

        return runtime_environment

    def _build_simulation_lambda(
        self,
        *,
        image_tag: str,
        runtime_environment: str,
    ) -> lambda_.DockerImageFunction:
        function_name = "pv-eem"
        simulation_repository = ecr.Repository.from_repository_name(
            self,
            "SimulationRepository",
            "pv-expected-energy/simulation",
        )
        simulation_log_group = logs.LogGroup(
            self,
            "SimulationFunctionLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            removal_policy=RemovalPolicy.DESTROY,
        )
        simulation_function = lambda_.DockerImageFunction(
            self,
            "SimulationFunction",
            function_name=function_name,
            architecture=lambda_.Architecture.ARM_64,
            memory_size=8196,
            timeout=Duration.seconds(900),
            environment={
                "ENVIRONMENT": runtime_environment,
                "PYTHONPATH": "/var/task/src",
            },
            log_group=simulation_log_group,
            code=lambda_.DockerImageCode.from_ecr(
                simulation_repository,
                tag_or_digest=image_tag,
                cmd=["main.lambda_handler"],
            ),
        )

        simulation_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=["*"],
            )
        )

        pv_systems_bucket = s3.Bucket.from_bucket_name(
            self,
            "PvSystemsBucket",
            "pv-systems",
        )
        pv_systems_bucket.grant_read(simulation_function)

        model_logs_bucket = s3.Bucket.from_bucket_name(
            self,
            "PvExpectedModelLogsBucket",
            "pv-expected-model-logs",
        )
        model_logs_bucket.grant_write(simulation_function)

        return simulation_function
