from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from core import models


def get_recursive_parents(*, db: Session, device_id: int):
    recursive_cte = (
        select(
            models.Device.device_id.label("device_id"),
            models.Device.parent_device_id.label("parent_device_id"),
        )
        .where(models.Device.device_id == device_id)
        .cte(name="RecursiveParents", recursive=True)
    )

    parent_alias = aliased(models.Device)

    recursive_cte = recursive_cte.union_all(
        select(
            parent_alias.device_id.label("device_id"),
            parent_alias.parent_device_id.label("parent_device_id"),
        ).where(parent_alias.device_id == recursive_cte.c.parent_device_id),
    )

    parent_devices = (
        db.query(models.Device)
        .join(  # Join the device table rows with rows in our CTE
            recursive_cte,
            models.Device.device_id == recursive_cte.c.device_id,
        )
        .all()
    )

    return parent_devices
