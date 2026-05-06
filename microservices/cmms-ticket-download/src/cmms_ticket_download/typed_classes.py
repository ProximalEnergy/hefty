from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

import httpx
from pydantic import BaseModel


class CMMSTicketDownloadProvider(StrEnum):
    """Supported CMMS ticket download providers."""

    JIRA = "jira"
    MAXIMO = "maximo"
    QE_SOLAR = "qe_solar"


class CMMSTicketDownloadTicket(BaseModel):
    """Normalized ticket payload produced by CMMS provider adapters."""

    cmms_integration_id: int
    source_id: int  # machine readable identifier
    key: str  # human readable identifier
    source_created_at: datetime | None = (
        None  # the date and time the ticket was created
    )
    due_date: datetime | None = None
    summary: str | None = None
    summary_long: str | None = None
    status: str | None = None
    status_change_at: datetime | None = None
    priority: str | None = None
    reporter: str | None = None
    assigned_to: str | None = None
    location: str | None = None
    cmms_device_id: str | None = None  # according to the CMMS provider
    cmms_device_name: str | None = None  # according to the CMMS provider
    link: str | None = None  # the link to the ticket on the CMMS provider's platform
    json_raw: dict | None = None


class CMMSTicketDownloadEvent(BaseModel):
    """Event payload for direct CMMS ticket download runs."""

    cmms_provider: str
    base_url: str
    start: datetime
    end: datetime
    project_name: str


class CMMSSessionProtocol(Protocol):
    """Session interface implemented by CMMS provider adapters."""

    def __init__(
        self, *, base_url: str, aws_secret_username: str, aws_secret_key: str
    ): ...

    def get_raw_tickets(
        self,
        *,
        client: httpx.Client,
        project_name: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[Any, Any]]:
        """Fetch raw ticket payloads from the provider.

        Args:
            client: HTTP client used for provider requests.
            project_name: Provider project name to filter tickets by.
            start: Optional start date for ticket extraction.
            end: Optional end date for ticket extraction.
        """
        ...


class ConvertToCMMSTicketProtocol(Protocol):
    """Callable interface for converting provider tickets to normalized tickets."""

    def __call__(
        self, *, raw_ticket: dict[Any, Any], cmms_integration_id: int, base_url: str
    ) -> CMMSTicketDownloadTicket:
        """Convert one provider ticket to the normalized CMMS ticket model.

        Args:
            raw_ticket: Provider ticket payload.
            cmms_integration_id: CMMS integration ID for the ticket.
            base_url: Provider base URL used to build ticket links.
        """
        ...
