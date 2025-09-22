from abc import ABC, abstractmethod
from collections.abc import Generator
from datetime import datetime
from itertools import chain

import requests
from pydantic import BaseModel

from app import interfaces
from app.utils import ensure_200


class CMMSTicket(BaseModel):
    cmms_provider: str
    id: int  # machine readable identifier
    key: str  # human readable identifier
    created_at: datetime | None = None  # the date and time the ticket was created
    due_date: str | None = None
    summary: str | None = None
    summary_long: str | None = None
    status: str | None = None
    status_change_at: str | None = None
    priority: str | None = None
    reporter: str | None = None
    assigned_to: str | None = None
    location: str | None = None
    cmms_device_id: str | None = None  # according to the CMMS provider
    cmms_device_name: str | None = None  # according to the CMMS provider
    proximal_device: interfaces.Device | None = (
        None  # the device object associated with the ticket
    )
    link: str | None = None  # the link to the ticket on the CMMS provider's platform


def skip_empty_lists(
    *,
    generator: Generator[list, None, None],
) -> Generator[list, None, None]:
    """Skip empty lists from a generator.

    Args:
        generator (Generator[list, None, None]): Generator of lists

    Returns:
        Generator[list, None, None]: Generator that yields non-empty lists
    """
    for lst in generator:
        if len(lst) > 0:
            yield lst


##
# The Abstract CMMS Session class defined the standard for how each CMMS provider api interface should be implemented.
# The cmms-tickets endpoint expects to be able to use the abstract methods in this class
# for any given CMMS provider, including
#     1) authentication by AWS Secrets username and api key
#     2) convert raw extenal json format to proximal CMMSTicket pydantic model
#     3) ability to generate tickets, filtering by project name, start date, end date, and device ids (last one to be implemented still).
#
# The generate_tickets method creates a generator in case tickets want to be fetched in batches in the frontend.
# However, this is not fully utilized in the current implementation.
#
# This class makes use of the requests.Session object to store header and authentication information for all requests called by the session.
#


class CMMSSession(ABC):
    """Abstract base class defining the interface for CMMS provider API interactions.

    This class establishes the standard interface that all CMMS provider implementations
    must follow. It handles authentication, ticket retrieval, and data normalization
    across different CMMS systems.

    Attributes:
        _base_url (str): Base URL for the CMMS provider's API
        _session (requests.Session): HTTP session for making API requests
    """

    def __init__(
        self,
        *,
        base_url: str,
        session: requests.Session | None = None,
    ):
        """Initialize a new CMMS session.

        Args:
            base_url (str): Base URL for the CMMS provider's API
            session (Optional[requests.Session]): Existing requests session to use
        """
        self._base_url = base_url  # todo better definition of base_url
        self._session = session or requests.Session()

    @property
    def base_url(self) -> str:
        """Get the base URL for the CMMS provider's API.

        Returns:
            str: The base URL
        """
        return self._base_url

    @property
    def session(self) -> requests.Session:
        """Get the HTTP session used for API requests.

        Returns:
            requests.Session: The current HTTP session
        """
        return self._session

    @abstractmethod
    def authenticate(
        self,
        *,
        username: str,
        api_key: str,
    ):
        """Authenticate with the CMMS provider's API.

        Updates the session headers and/or authentication based on credentials
        from AWS Secrets Manager.

        Args:
            username (str): Username for API authentication
            api_key (str): API key for authentication
        """

    @abstractmethod
    def to_cmms_ticket(
        self,
        *,
        raw_ticket: dict,
    ) -> CMMSTicket:
        """Convert raw CMMS API response to a standardized CMMSTicket.

        Args:
            raw_ticket (dict): Raw ticket data from the CMMS provider's API

        Returns:
            CMMSTicket: Normalized ticket object
        """

    @abstractmethod
    def _generate_tickets_raw(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[dict], None, None]:
        """Generate raw tickets from the CMMS API.

        Creates a generator that yields batches of raw tickets from the CMMS API,
        filtered by the provided parameters.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List]): Filter tickets for these device IDs

        Yields:
            List[dict]: Batches of raw ticket data from the CMMS API
        """

    def generate_tickets_raw(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[dict], None, None]:
        """Generate raw tickets from the CMMS API.

        This method is a wrapper around the _generate_tickets_raw method that skips empty lists.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List]): Filter tickets for these device IDs

        Yields:
            List[dict]: Batches of raw ticket data from the CMMS API
        """
        return skip_empty_lists(
            generator=self._generate_tickets_raw(
                project_name=project_name,
                start=start,
                end=end,
                device_ids=device_ids,
            ),
        )

    def get(
        self,
        *,
        url: str,
        **kwargs,
    ):
        """Make a GET request to the CMMS API.

        Args:
            url (str): URL to request
            **kwargs: Additional arguments to pass to requests.get

        Returns:
            dict: JSON response from the API
        """
        return ensure_200(response=self.session.get(url=url, **kwargs)).json()

    def generate_tickets(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[CMMSTicket], None, None]:
        """Generate standardized CMMSTicket objects.

        Converts raw tickets from the CMMS API into standardized CMMSTicket objects by applying the to_cmms_ticket method to each raw ticket.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List]): Filter tickets for these device IDs

        Yields:
            List[CMMSTicket]: Batches of standardized ticket objects
        """
        for raw_tickets in self.generate_tickets_raw(
            project_name=project_name,
            start=start,
            end=end,
            device_ids=device_ids,
        ):
            yield [
                self.to_cmms_ticket(raw_ticket=raw_ticket) for raw_ticket in raw_tickets
            ]

    def get_all_tickets_raw(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> list[dict]:
        """Get all raw tickets from the CMMS API.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[list]): Filter tickets for these device IDs

        Returns:
            List[dict]: All raw ticket data from the CMMS API
        """
        return list(
            chain(
                *self.generate_tickets_raw(
                    project_name=project_name,
                    start=start,
                    end=end,
                    device_ids=device_ids,
                ),
            ),
        )

    def get_all_tickets(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> list[CMMSTicket]:
        """Get all standardized CMMSTicket objects. Applies the `to_cmms_ticket` method to each raw ticket.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[list]): Filter tickets for these device IDs

        Returns:
            List[CMMSTicket]: All standardized ticket objects
        """
        return list(
            chain(
                *self.generate_tickets(
                    project_name=project_name,
                    start=start,
                    end=end,
                    device_ids=device_ids,
                ),
            ),
        )
