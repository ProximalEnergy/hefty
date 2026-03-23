"""Local runner: data connection outage project IDs and notification creation."""

import asyncio
import logging

from core.crud.admin.notifications import (
    create_notification,
    get_most_recent_notifications,
    update_notifications_is_active,
)
from core.database import async_engine, with_db_async
from core.db_query import OutputType
from core.domain.notifications.data_connection_outage import (
    get_data_connection_outage_project_ids,
)
from core.utils.notifications import (
    determine_notification_recipients,
    send_notification_emails_with_rate_limit,
)

from core import enumerations

NOTIFICATION_TYPE = enumerations.NotificationType.DATA_CONNECTION_OUTAGE
NOTIFICATION_SEVERITY = enumerations.NotificationSeverity.CRITICAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_email_kwargs_func(
    *,
    user_id: str,  # noqa: ARG001
    user_email: str,
    user_name: str,  # noqa: ARG001
) -> dict:
    """Build email kwargs for a data connection outage notification.

    Args:
        user_id: Recipient user id (unused for static body).
        user_email: Recipient email address.
        user_name: Recipient display name (unused for static body).
    """
    return {
        "FromEmailAddress": "alerts@proximal.energy",
        "Destination": {"ToAddresses": [user_email]},
        "Content": {
            "Simple": {
                "Subject": {"Data": "Data Connection Outage"},
                "Body": {"Html": {"Data": "Data Connection Outage"}},
            },
        },
    }


async def main() -> None:
    """Main function to run the data connection outage notifications lambda."""
    # Step 1 - Determine which projects are currently experiencing a data connection
    # outage.
    # Returned data structure: {True: [...], False: [...]} where True = connection
    # outage.
    data_connection_outage_info = await get_data_connection_outage_project_ids()

    project_ids_with_outage = data_connection_outage_info[True]
    project_ids_without_outage = data_connection_outage_info[False]

    logging.info(f"project_ids_with_outage: {project_ids_with_outage}")
    logging.info(f"project_ids_without_outage: {project_ids_without_outage}")

    # Step 2 - Determine which projects already have an active outage notification
    active_notifications = await get_most_recent_notifications(
        project_ids=list(set(project_ids_with_outage + project_ids_without_outage)),
        notification_type_ids=[NOTIFICATION_TYPE.value],
        is_active=True,
    ).get_async(output_type=OutputType.PANDAS)

    # Step 3 - If necessary, mark projects that have an active outage notification but
    # are now healthy as inactive.
    # Polars cannot use ``is_in`` with Python ``uuid.UUID`` lists (nested object
    # types); compare via string.
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

    # Step 4 - If necessary, create notifications for outage projects that have no
    # active row yet.
    project_ids_to_create_notification = set(project_ids_with_outage) - set(
        active_notifications["project_id"].unique()
    )

    async with with_db_async(schema=None) as db:
        for project_id in project_ids_to_create_notification:
            notification = await create_notification(
                db=db,
                project_id=project_id,
                notification_type_id=NOTIFICATION_TYPE,
                data=dict(),
                severity=NOTIFICATION_SEVERITY,
            )
            logger.info("Created notification for project %s", project_id)

            recipients = await determine_notification_recipients(
                db=db,
                project_id=str(project_id),
                notification_type_id=NOTIFICATION_TYPE,
                severity=NOTIFICATION_SEVERITY,
            )
            logger.info(
                "recipients project_id=%s in_app=%s email=%s",
                project_id,
                len(recipients[0]),
                len(recipients[1]),
            )

            user_ids = recipients[1]

            await send_notification_emails_with_rate_limit(
                db=db,
                user_ids=user_ids,
                get_email_kwargs_func=get_email_kwargs_func,
                notification_id=notification.notification_id,
                summary=dict(),
            )

    try:
        await async_engine.dispose()
    except Exception as exc:
        logger.warning("async_engine.dispose failed: %s", exc)


if __name__ == "__main__":
    asyncio.run(main())
