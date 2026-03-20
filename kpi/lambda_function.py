# Initialize Sentry even before imports

import os

import sentry_sdk
import sentry_sdk.integrations.aws_lambda as sentry_aws_lambda
from dotenv import load_dotenv
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

load_dotenv()
# SDK uses this constant (ms before timeout to fire warning). Default 1500; use 30s.
sentry_aws_lambda.TIMEOUT_WARNING_BUFFER = 30_000
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

# now do all of the imports

import datetime
from uuid import UUID

import kpi_pipeline.config as config
from core.crud.operational.projects import get_project
from core.enumerations import KPIType, OutputType
from kpi_pipeline.base.models import ContextModel
from kpi_pipeline.infra.dataset_builder import create_dataset
from kpi_pipeline.infra.device_manager import DeviceTree
from kpi_pipeline.infra.observer import SentryObserver
from kpi_pipeline.services.client import action_from_list
from pydantic import BaseModel


class Event(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    project_id: UUID
    kpi_type_ids: list[int]


observer = SentryObserver()


def lambda_handler(event, context):
    sentry_sdk.set_context("lambda_payload", event)
    event = Event(**event)

    project = get_project(project_id=event.project_id).get(
        schema="operational",
        output_type=OutputType.SQLALCHEMY,
    )
    if project is None:
        raise ValueError(f"Project not found for project id: {event.project_id}")

    output_kpis: list[str] = []
    for kpi_type_id in event.kpi_type_ids:
        if kpi_type_id in KPIType:
            output_kpis.append(KPIType(kpi_type_id).name)
            continue
        sentry_sdk.capture_message(
            f"Ignoring unknown KPI type id in lambda payload: {kpi_type_id}",
            level="warning",
        )

    # use the project-specific validation if it exists, otherwise use the base validation
    validation = (
        config.validate_per_project[project.name_short]
        if project.name_short in config.validate_per_project
        else config.validate_per_project["base"]
    )

    calculation = (
        config.calculate_per_project[project.name_short]
        if project.name_short in config.calculate_per_project
        else config.calculate_per_project["base"]
    )

    aggregate = (
        config.aggregate_per_project[project.name_short]
        if project.name_short in config.aggregate_per_project
        else config.aggregate_per_project["base"]
    )

    kpi_pipeline = action_from_list(
        [
            config.Download.export(),
            validation.export(),
            calculation.export(),
            aggregate.export(),
            config.kpi_upload_action,
        ]
    )

    pipeline = kpi_pipeline.trim(outputs=output_kpis)

    device_tree = DeviceTree.from_project(project=project)

    context = ContextModel(
        project=project,
        start_date=event.start_date,
        end_date=event.end_date,
        device_tree=device_tree,
    )

    dataset = create_dataset(context=context)

    with observer.with_project(project_name_short=project.name_short):
        pipeline(dataset=dataset, context=context, observer=observer)

    return {"statusCode": 200, "body": "Success"}
