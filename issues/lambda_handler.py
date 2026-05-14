"""AWS Lambda entrypoint for the issues pipeline."""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
from dataclasses import asdict
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from issues.orchestrator.run_project import ProjectIssueRunSummary

LOGGER = logging.getLogger(__name__)
_DEFAULT_SECRET_NAME = "microservices/issues_pipeline"  # noqa: S105


def _load_issues_local_dotenv() -> None:
    """Load local environment variables when python-dotenv is installed."""
    try:
        dotenv = cast(Any, import_module("dotenv"))
    except ModuleNotFoundError:
        return
    dotenv.load_dotenv()


_load_issues_local_dotenv()


def configure_lambda_logging() -> None:
    """Configure stdout logging for CloudWatch Logs."""
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - %(levelname)s - %(process)d - %(threadName)s - %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def load_issues_pipeline_secret_into_env(*, secret_name: str, region: str) -> None:
    """Load a JSON secret into environment variables.

    Args:
        secret_name: Name of the AWS Secrets Manager secret.
        region: AWS region where the secret is stored.
    """
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString")
        if not secret_string:
            LOGGER.warning("Secret %s has no SecretString", secret_name)
            return
        data = json.loads(secret_string)
        if not isinstance(data, dict):
            LOGGER.warning("Secret %s is not a JSON object", secret_name)
            return
        for key, value in data.items():
            os.environ.setdefault(str(key), str(value))
        LOGGER.info("Successfully loaded secret %s", secret_name)
    except ClientError as exc:
        LOGGER.warning(
            "Error loading secret %s: %s. Continuing without loading secrets.",
            secret_name,
            exc,
        )
    except Exception as exc:
        LOGGER.warning(
            "Error loading secret %s: %s. Continuing without loading secrets.",
            secret_name,
            exc,
        )


def _load_issues_pipeline_secrets() -> None:
    """Load secrets before imports that read ``core.settings``."""
    region = os.getenv("AWS_REGION", "us-east-2")
    secret_name = os.getenv("ISSUES_PIPELINE_SECRET_NAME", _DEFAULT_SECRET_NAME)
    load_issues_pipeline_secret_into_env(secret_name=secret_name, region=region)


_load_issues_pipeline_secrets()


def lambda_handler(
    event: dict[str, Any] | None,
    context: Any,  # noqa: ANN401, ARG001
) -> dict[str, Any]:
    """Run the issues pipeline from an AWS Lambda invocation.

    Args:
        event: EventBridge or manual invocation payload.
        context: AWS Lambda context object.

    Returns:
        API Gateway-style response with a JSON body summary.
    """
    configure_lambda_logging()
    payload = event or {}
    run_time = parse_run_time(value=payload.get("run_time") or payload.get("time"))
    project_ids = parse_project_ids(value=payload.get("project_ids"))
    issue_category_ids = parse_issue_category_ids(
        value=payload.get("issue_category_ids")
    )
    start = parse_backfill_date(value=payload.get("start"), field_name="start")
    end = parse_backfill_date(value=payload.get("end"), field_name="end")
    validate_backfill_arguments(
        project_ids=project_ids,
        issue_category_ids=issue_category_ids,
        start=start,
        end=end,
    )

    LOGGER.info("Starting issues Lambda pipeline")
    try:
        from issues.orchestrator.run_issues import (  # noqa: PLC0415
            discover_project_ids,
            run_issues_for_projects,
            run_local_midnight_backfill_for_projects,
        )

        if is_eventbridge_scheduled_event(payload=payload):
            summaries = cast(Any, run_local_midnight_backfill_for_projects)(
                project_ids=project_ids,
                run_time=run_time,
            )
            requested_project_ids = [summary.project_id for summary in summaries]
        else:
            requested_project_ids = project_ids or discover_project_ids()
            summaries = cast(Any, run_issues_for_projects)(
                project_ids=requested_project_ids,
                run_time=run_time,
                issue_category_ids=issue_category_ids,
                start=start,
                end=end,
            )
        response_body = build_response_body(
            requested_project_ids=requested_project_ids,
            summaries=summaries,
        )
        LOGGER.info(
            "Issues Lambda pipeline completed project_count=%d failure_count=%d",
            response_body["project_count"],
            response_body["failure_count"],
        )
        return {
            "statusCode": 200,
            "body": json.dumps(response_body),
        }
    except Exception as exc:
        LOGGER.exception("Issues Lambda pipeline failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }


def is_eventbridge_scheduled_event(*, payload: dict[str, Any]) -> bool:
    """Return whether the payload is an EventBridge scheduled invocation.

    Args:
        payload: Lambda event payload.
    """
    return (
        payload.get("source") == "aws.events"
        and payload.get("detail-type") == "Scheduled Event"
    )


def parse_project_ids(*, value: object) -> list[str] | None:
    """Parse optional project ids from a Lambda event payload.

    Args:
        value: Value from the event's `project_ids` key.

    Returns:
        Project ids when supplied, otherwise None.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        msg = "project_ids must be a list of strings"
        raise ValueError(msg)
    project_ids = [str(project_id) for project_id in value if str(project_id)]
    return project_ids or None


def parse_run_time(*, value: object) -> datetime.datetime | None:
    """Parse optional ISO-8601 run time from a Lambda event payload.

    Args:
        value: Value from the event's `run_time` key.

    Returns:
        Timezone-aware datetime when supplied, otherwise None.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "run_time must be an ISO-8601 string"
        raise ValueError(msg)
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.UTC)
    return parsed.astimezone(datetime.UTC)


def parse_issue_category_ids(*, value: object) -> list[int] | None:
    """Parse optional issue category ids from a Lambda event payload.

    Args:
        value: Value from the event's `issue_category_ids` key.

    Returns:
        Issue category ids when supplied, otherwise None.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        msg = "issue_category_ids must be a list of integers"
        raise ValueError(msg)

    issue_category_ids: list[int] = []
    for raw_category_id in value:
        if raw_category_id in (None, ""):
            continue
        try:
            issue_category_ids.append(int(raw_category_id))
        except (TypeError, ValueError) as exc:
            msg = "issue_category_ids must contain only integers"
            raise ValueError(msg) from exc
    return issue_category_ids or None


def parse_backfill_date(
    *,
    value: object,
    field_name: str,
) -> datetime.date | None:
    """Parse an optional backfill boundary date from a Lambda event payload.

    Args:
        value: Value from the event's `start` or `end` key.
        field_name: Name of the payload field for error messages.

    Returns:
        Parsed date when supplied, otherwise None.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{field_name} must be an ISO-8601 date string"
        raise ValueError(msg)
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        msg = f"{field_name} must be an ISO-8601 date string"
        raise ValueError(msg) from exc


def validate_backfill_arguments(
    *,
    project_ids: list[str] | None,
    issue_category_ids: list[int] | None,
    start: datetime.date | None,
    end: datetime.date | None,
) -> None:
    """Validate backfill argument combinations.

    Args:
        project_ids: Parsed project ids or None.
        issue_category_ids: Parsed issue category ids or None.
        start: Optional start date.
        end: Optional end date.
    """
    backfill_scope_supplied = bool(project_ids or issue_category_ids)
    if backfill_scope_supplied and (start is None or end is None):
        msg = "start and end are required when passing backfill scope arguments"
        raise ValueError(msg)
    if (start is None) != (end is None):
        msg = "start and end must be provided together"
        raise ValueError(msg)
    if start is not None and end is not None and start > end:
        msg = "start must be less than or equal to end"
        raise ValueError(msg)


def build_response_body(
    *,
    requested_project_ids: list[str],
    summaries: list[ProjectIssueRunSummary],
) -> dict[str, Any]:
    """Build a JSON-serializable Lambda response body.

    Args:
        requested_project_ids: Projects attempted by the orchestrator.
        summaries: Successful per-project run summaries.

    Returns:
        JSON-ready aggregate and per-project run metrics.
    """
    active_projects = [summary for summary in summaries if summary.active_count > 0]
    return {
        "project_count": len(requested_project_ids),
        "successful_project_count": len(summaries),
        "failure_count": len(requested_project_ids) - len(summaries),
        "active_project_count": len(active_projects),
        "raw_candidate_count": sum(
            summary.raw_candidate_count for summary in summaries
        ),
        "final_candidate_count": sum(
            summary.final_candidate_count for summary in summaries
        ),
        "opened_count": sum(summary.opened_count for summary in summaries),
        "matched_count": sum(summary.matched_count for summary in summaries),
        "resolved_count": sum(summary.resolved_count for summary in summaries),
        "active_count": sum(summary.active_count for summary in summaries),
        "projects": [
            serialize_project_summary(summary=summary) for summary in summaries
        ],
    }


def serialize_project_summary(
    *,
    summary: ProjectIssueRunSummary,
) -> dict[str, Any]:
    """Serialize a project run summary for JSON output.

    Args:
        summary: Per-project run summary.

    Returns:
        JSON-ready summary dictionary.
    """
    payload = asdict(summary)
    payload["run_time"] = summary.run_time.isoformat()
    return payload
