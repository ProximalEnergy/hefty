from sqlalchemy.orm import Session, selectinload

from core import models
from core.model_list import ModelList


def get_project_cmms_devices(
    *,
    project_db: Session,
    cmms_integration_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    return_query: bool = False,
) -> ModelList[models.CMMSDevice]:
    """Get the CMMS devices for a project

        Parameters:
        -----------
        project_db: Session
            The database session for the project
        cmms_integration_ids: Optional[list[int]]
            The list of CMMS integration IDs to filter by
        device_ids: Optional[list[int]]
            The list of device IDs to filter by
        Returns:
        --------
        List[models.CMMSDevice]
            The list of CMMS devices for the project

    Args:
        project_db: Project-scoped SQLAlchemy session for CMMS queries.
        cmms_integration_ids: Optional list of integration IDs to filter on.
        device_ids: Optional list of device IDs to narrow the CMMS devices.
        return_query: When True, return the query instead of executing it.
    """
    query = project_db.query(models.CMMSDevice).options(
        selectinload(models.CMMSDevice.device),
    )

    if cmms_integration_ids:
        query = query.where(
            models.CMMSDevice.cmms_integration_id.in_(cmms_integration_ids),
        )

    if device_ids:
        query = query.where(
            models.CMMSDevice.device_id.in_(device_ids),
        )

    return ModelList(query=query, return_query=return_query)
