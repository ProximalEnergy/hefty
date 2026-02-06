from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces

router = APIRouter(
    prefix="/contract-categories",
    tags=["contract_categories"],
)


@router.get("", response_model=list[interfaces.ContractCategory])
async def list_contract_categories(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    # Use raw SQL to avoid dependency on ORM model presence in installed core package
    """todo

    Args:
        db: Description for db.
    """
    query = sa.text(
        """
        SELECT contract_category_id, name_short, name_long
        FROM operational.contract_categories
        ORDER BY name_long
        """
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    return [
        interfaces.ContractCategory(
            contract_category_id=row["contract_category_id"],
            name_short=row["name_short"],
            name_long=row["name_long"],
        )
        for row in rows
    ]
