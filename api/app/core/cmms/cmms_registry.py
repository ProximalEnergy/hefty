from app.core.cmms.cmms import CMMSSession
from app.core.cmms.jira import JiraSession
from app.core.cmms.maximo import MaximoSession
from app.core.cmms.qe_solar import QESolarSession

CMMS_SESSION_MAP: dict[str, type[CMMSSession]] = {
    "jira": JiraSession,
    "qe_solar": QESolarSession,
    "maximo": MaximoSession,
}
