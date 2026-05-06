from datetime import datetime
from typing import Self

import httpx

from cmms_ticket_download.cmms_registry import (
    CMMS_SESSION_REGISTRY,
    CMMS_TICKET_CONVERTER_REGISTRY,
)
from cmms_ticket_download.crud import bulk_upsert_cmms_tickets
from cmms_ticket_download.dbquery import get_cmms_integration_with_project
from cmms_ticket_download.typed_classes import (
    CMMSSessionProtocol,
)
from cmms_ticket_download.utils import get_cmms_ticket_download_secret
from core import models


class CMMSETL:
    """Coordinates ticket extraction and persistence for a CMMS integration."""

    def __init__(
        self, *, cmms_integration: models.CMMSIntegration, project: models.Project
    ):
        self.cmms_integration = cmms_integration
        self.project = project
        self._cmms_session: CMMSSessionProtocol | None = None

    @property
    def cmms_session(self) -> CMMSSessionProtocol:
        """Build and cache the configured CMMS provider session."""

        if self._cmms_session is None:
            base_url = self.cmms_integration.domain_name
            if base_url is None:
                raise ValueError("CMMS integration domain_name is required")

            secret = get_cmms_ticket_download_secret(
                secret_name=(
                    f"cmms_integrations/cmms_integration_id/"
                    f"{self.cmms_integration.cmms_integration_id}"
                ),
            )

            self._cmms_session = CMMS_SESSION_REGISTRY[
                self.cmms_integration.cmms_provider.name_short
            ](
                base_url=base_url,
                aws_secret_username=secret["username"],
                aws_secret_key=secret["api_key"],
            )
        return self._cmms_session

    @classmethod
    def from_cmms_integration_id(cls, *, cmms_integration_id: int) -> Self:
        """Create an ETL runner from a CMMS integration ID.

        Args:
            cmms_integration_id: CMMS integration ID to load.
        """

        cmms_integration, project = get_cmms_integration_with_project(
            cmms_integration_id=cmms_integration_id
        )
        return cls(cmms_integration=cmms_integration, project=project)

    def run_etl(self, *, start: datetime, end: datetime) -> int:
        """Fetch provider tickets and upsert them into the project database.

        Args:
            start: Start datetime for ticket extraction.
            end: End datetime for ticket extraction.
        """

        project_name = self.cmms_integration.project_name
        if project_name is None:
            raise ValueError("CMMS integration project_name is required")

        base_url = self.cmms_integration.domain_name
        if base_url is None:
            raise ValueError("CMMS integration domain_name is required")

        with httpx.Client(timeout=30.0) as client:
            raw_tickets = self.cmms_session.get_raw_tickets(
                client=client,
                project_name=project_name,
                start=start,
                end=end,
            )
        converter = CMMS_TICKET_CONVERTER_REGISTRY[
            self.cmms_integration.cmms_provider.name_short
        ]
        to_upload = [
            converter(
                raw_ticket=raw_ticket,
                cmms_integration_id=self.cmms_integration.cmms_integration_id,
                base_url=base_url,
            ).model_dump()
            for raw_ticket in raw_tickets
        ]
        project_schema = self.project.name_short
        if project_schema is None:
            raise ValueError("Project name_short is required")

        return bulk_upsert_cmms_tickets(
            schema=project_schema,
            tickets_data=to_upload,
        )


def run_cmms_ticket_download_etl_debug():
    """Run the CMMS ticket download ETL against a hard-coded integration."""

    cmms_etl = CMMSETL.from_cmms_integration_id(cmms_integration_id=19)
    return cmms_etl.run_etl(
        start=datetime(2025, 12, 30),
        end=datetime(2026, 2, 11),
    )


if __name__ == "__main__":
    # Get a database session
    run_cmms_ticket_download_etl_debug()
