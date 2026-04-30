"""Lambda handler: data connection outage detection and notifications."""

import asyncio
import json
import logging
import os
from importlib import import_module
from typing import Any, cast
from uuid import UUID

import boto3
from botocore.exceptions import ClientError


def _load_data_connection_outage_local_dotenv() -> None:
    """Load local environment variables when python-dotenv is installed."""
    try:
        dotenv = cast(Any, import_module("dotenv"))
    except ModuleNotFoundError:
        return
    dotenv.load_dotenv()


_load_data_connection_outage_local_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Secrets Manager secret id (not a credential).
_DEFAULT_SM_SECRET_ID = "microservices/data_connection_outage_notification"  # noqa: S105


def load_data_connection_outage_secret_into_env(
    *, secret_name: str, region: str
) -> None:
    """Load a JSON secret into environment variables.

    Args:
        secret_name: Name of the AWS Secrets Manager secret.
        region: AWS region where the secret is stored.
    """
    try:
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        secret_str = resp.get("SecretString")
        if not secret_str:
            logger.warning("Secret %s has no SecretString", secret_name)
            return
        data = json.loads(secret_str)
        for key, value in data.items():
            os.environ.setdefault(key, str(value))
        logger.info("Successfully loaded secret %s", secret_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            logger.warning(
                "Secret %s not found in Secrets Manager. "
                "Continuing without loading secrets.",
                secret_name,
            )
        else:
            logger.warning(
                "Error loading secret %s: %s. Continuing without loading secrets.",
                secret_name,
                e,
            )
    except Exception as e:
        logger.warning(
            "Error loading secret %s: %s. Continuing without loading secrets.",
            secret_name,
            e,
        )


def _load_data_connection_outage_secrets() -> None:
    """Load secrets before any ``core`` import (``DATABASE_URL`` at import time)."""
    try:
        region = os.getenv("AWS_REGION", "us-east-2")
        secret_name = os.getenv(
            "DATA_CONNECTION_OUTAGE_SECRET_NAME",
            _DEFAULT_SM_SECRET_ID,
        )
        load_data_connection_outage_secret_into_env(
            secret_name=secret_name, region=region
        )
    except Exception as e:
        logger.warning("Error loading secrets at startup: %s", e)


_load_data_connection_outage_secrets()


async def _run_data_connection_outage_notifications() -> dict:
    """Run outage scan, update notifications, and notify recipients."""
    # Imports after Secrets Manager hydration (``core.settings`` reads env at import).
    from core.crud.admin.notifications import (  # noqa: PLC0415
        create_notification,
        create_notification_state,
        get_most_recent_notifications,
        update_notifications_is_active,
    )
    from core.crud.operational.projects import get_project  # noqa: PLC0415
    from core.database import async_engine, with_db_async  # noqa: PLC0415
    from core.db_query import OutputType  # noqa: PLC0415
    from core.domain.notifications.data_connection_outage import (  # noqa: PLC0415
        get_data_connection_outage_project_ids,
    )
    from core.utils.notifications import (  # noqa: PLC0415
        determine_notification_recipients,
        send_notification_emails_with_rate_limit,
    )
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

    from core import enumerations, models  # noqa: PLC0415

    notification_type = enumerations.NotificationType.DATA_CONNECTION_OUTAGE
    notification_severity = enumerations.NotificationSeverity.CRITICAL

    async def project_name_long_for_delivery(
        *,
        project_id: UUID,
        data: dict[str, Any],
    ) -> str:
        """Resolve display name from payload or operational.projects."""
        raw = data.get("project_name_long")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        project_model = await get_project(project_id=project_id).get_async(
            schema="operational", output_type=OutputType.SQLALCHEMY
        )
        if project_model is None:
            logger.warning(
                "Project not found for project_id=%s; using fallback label",
                project_id,
            )
            return "Unknown project"
        return str(project_model.name_long)

    async def deliver_data_connection_outage(
        *,
        db: AsyncSession,
        notification_id: int,
        project_id: UUID,
        project_name_long: str,
    ) -> None:
        """Email + in-app states using ``determine_notification_recipients``."""

        def get_email_kwargs_func(
            *,
            user_id: str,  # noqa: ARG001
            user_email: str,
            user_name: str,  # noqa: ARG001
        ) -> dict:
            """Build email kwargs for a data connection outage notification."""
            subject = f"Data Connection Outage - {project_name_long}"
            return {
                "FromEmailAddress": "alerts@proximal.energy",
                "Destination": {"ToAddresses": [user_email]},
                "Content": {
                    "Simple": {
                        "Subject": {"Data": subject},
                        "Body": {"Html": {"Data": subject}},
                    },
                },
            }

        (
            users_to_notify_in_app,
            users_to_notify_email,
        ) = await determine_notification_recipients(
            db=db,
            project_id=str(project_id),
            notification_type_id=notification_type,
            severity=notification_severity,
        )
        logger.info(
            "deliver notification_id=%s project_id=%s in_app=%s email=%s",
            notification_id,
            project_id,
            len(users_to_notify_in_app),
            len(users_to_notify_email),
        )

        if users_to_notify_email:
            await send_notification_emails_with_rate_limit(
                db=db,
                user_ids=users_to_notify_email,
                get_email_kwargs_func=get_email_kwargs_func,
                notification_id=notification_id,
                summary=dict(),
            )

        for user_id in users_to_notify_in_app:
            await create_notification_state(
                db=db,
                notification_id=notification_id,
                user_id=user_id,
                channel=enumerations.NotificationChannel.IN_APP,
            )

    async def active_outage_notifications_with_no_states(
        *,
        db: AsyncSession,
    ) -> list[models.Notification]:
        """Active DATA_CONNECTION_OUTAGE rows that have no notification_states."""
        stmt = (
            select(models.Notification)
            .outerjoin(
                models.NotificationState,
                models.Notification.notification_id
                == models.NotificationState.notification_id,
            )
            .where(models.NotificationState.notification_id.is_(None))
            .where(models.Notification.notification_type_id == notification_type.value)
            .where(models.Notification.is_active.is_(True))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    data_connection_outage_info = await get_data_connection_outage_project_ids()

    project_ids_with_outage = data_connection_outage_info[True]
    project_ids_without_outage = data_connection_outage_info[False]

    logger.info("project_ids_with_outage: %s", project_ids_with_outage)
    logger.info("project_ids_without_outage: %s", project_ids_without_outage)

    active_notifications = await get_most_recent_notifications(
        project_ids=list(set(project_ids_with_outage + project_ids_without_outage)),
        notification_type_ids=[notification_type.value],
        is_active=True,
    ).get_async(output_type=OutputType.PANDAS)

    notification_ids_to_mark_as_inactive = active_notifications.loc[
        active_notifications["project_id"].isin(project_ids_without_outage),
        "notification_id",
    ].to_list()
    if notification_ids_to_mark_as_inactive:
        query = update_notifications_is_active(
            notification_ids=notification_ids_to_mark_as_inactive,
            is_active=False,
        )
        await query.execute_async()

    project_ids_to_create_notification = set(project_ids_with_outage) - set(
        active_notifications["project_id"].unique()
    )

    created_count = 0
    async with with_db_async(schema=None) as db:
        for project_id in project_ids_to_create_notification:
            data_payload: dict[str, Any] = {}
            project_name_long = await project_name_long_for_delivery(
                project_id=project_id,
                data=data_payload,
            )
            data_payload["project_name_long"] = project_name_long

            notification = await create_notification(
                db=db,
                project_id=project_id,
                notification_type_id=notification_type,
                data=data_payload,
                severity=notification_severity,
            )
            logger.info("Created notification for project %s", project_id)
            created_count += 1

            await deliver_data_connection_outage(
                db=db,
                notification_id=notification.notification_id,
                project_id=project_id,
                project_name_long=project_name_long,
            )

    backfilled_count = 0
    async with with_db_async(schema=None) as db:
        orphans = await active_outage_notifications_with_no_states(db=db)
        if orphans:
            logger.info(
                "Backfilling %s outage notification(s) with no states",
                len(orphans),
            )
        for notification in orphans:
            project_name_long = await project_name_long_for_delivery(
                project_id=notification.project_id,
                data=notification.data or {},
            )
            await deliver_data_connection_outage(
                db=db,
                notification_id=notification.notification_id,
                project_id=notification.project_id,
                project_name_long=project_name_long,
            )
            backfilled_count += 1

    try:
        await async_engine.dispose()
    except Exception as exc:
        logger.warning("async_engine.dispose failed: %s", exc)

    return {
        "deactivated_notification_ids": len(notification_ids_to_mark_as_inactive),
        "notifications_created": created_count,
        "notifications_backfilled": backfilled_count,
    }


def lambda_handler(
    event,  # noqa: ARG001
    context,  # noqa: ARG001
):  # no-star-syntax
    """AWS Lambda entrypoint for data connection outage notifications.

    Args:
        event: Lambda event (unused for scheduled runs).
        context: Lambda context.

    Returns:
        Status code and JSON body with a short summary on success.

    Raises:
        Exception: Propagates so the invocation is marked failed (retries, metrics).
    """
    logger.info("LAMBDA_HANDLER_START: data connection outage notifications")

    try:
        summary = asyncio.run(_run_data_connection_outage_notifications())
        return {
            "statusCode": 200,
            "body": json.dumps(summary),
        }
    except Exception:
        logger.exception("Error in data connection outage lambda")
        raise


if __name__ == "__main__":
    result = asyncio.run(_run_data_connection_outage_notifications())
    logger.info(json.dumps(result, indent=2))
