from cmms_ticket_download.concrete.jira import JiraSession, jira_ticket_to_cmms_ticket
from cmms_ticket_download.concrete.maximo import (
    MaximoSession,
    maximo_ticket_to_cmms_ticket,
)
from cmms_ticket_download.concrete.qe_solar import (
    QESolarSession,
    qe_solar_ticket_to_cmms_ticket,
)
from cmms_ticket_download.typed_classes import (
    CMMSSessionProtocol,
    CMMSTicketDownloadProvider,
    ConvertToCMMSTicketProtocol,
)

CMMS_SESSION_REGISTRY: dict[str, type[CMMSSessionProtocol]] = {
    CMMSTicketDownloadProvider.JIRA.value: JiraSession,
    CMMSTicketDownloadProvider.MAXIMO.value: MaximoSession,
    CMMSTicketDownloadProvider.QE_SOLAR.value: QESolarSession,
}

CMMS_TICKET_CONVERTER_REGISTRY: dict[str, ConvertToCMMSTicketProtocol] = {
    CMMSTicketDownloadProvider.JIRA.value: jira_ticket_to_cmms_ticket,
    CMMSTicketDownloadProvider.MAXIMO.value: maximo_ticket_to_cmms_ticket,
    CMMSTicketDownloadProvider.QE_SOLAR.value: qe_solar_ticket_to_cmms_ticket,
}
