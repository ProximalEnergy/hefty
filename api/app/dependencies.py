import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

import httpx
import jwt
import sqlalchemy as sa
from core.dependencies import get_db
from core.dependencies import get_project_name_short as core_get_project_name_short
from core.dependencies import (
    get_project_name_short_async as core_get_project_name_short_async,
)
from core.dependencies import with_db as _with_db
from core.dependencies import with_db_async as _with_async_db
from core.enumerations import UserTypeEnum
from fastapi import Depends, Header, HTTPException, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces, settings
from app.integrations.token_manager import TokenManager, get_tps_token_manager
from core import models


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async db."""
    async with _with_async_db(schema=None) as db:
        yield db


# Use core's cached version directly
get_project_name_short = core_get_project_name_short


def get_project_db(*, project_id: UUID = Path(...)):
    """Get project db.

    Args:
        project_id: TODO: describe.
    """
    project_name_short = get_project_name_short(project_id=project_id)

    with _with_db(schema=project_name_short) as project_db:
        yield project_db


def get_project_api(*, project_id: UUID, db: Session = Depends(get_db)):
    """Get project api.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
    """
    project_model = core.crud.operational.projects.get_project(
        db=db, project_id=project_id, deep=True
    ).model()
    if not project_model:
        raise HTTPException(status_code=404, detail="Project not found")
    return interfaces.Project.model_validate(project_model)


async def get_ercot_db_async() -> AsyncGenerator[AsyncSession, None]:
    """Get ercot db async."""
    async with _with_async_db(schema="ercot") as ercot_db:
        yield ercot_db


def is_prod_origin(*, request: Request):
    """Return whether is prod origin.

    Args:
        request: TODO: describe.
    """
    origin = request.headers.get("origin")
    if not origin:
        return False
    else:
        return "app.proximal.energy" in str(origin)


def is_prod_api(*, request: Request):
    """Return whether is prod api.

    Args:
        request: TODO: describe.
    """
    host = request.headers.get("host")
    return "api.proximal.energy" in str(host)


# --- ASYNC ---
# Use core's cached version directly
get_project_name_short_async = core_get_project_name_short_async


async def get_project_db_async(*, project_id: UUID = Path(...)):
    """Get project db async.

    Args:
        project_id: TODO: describe.
    """
    project_name_short = await get_project_name_short_async(project_id=project_id)

    async with _with_async_db(schema=project_name_short) as project_db:
        yield project_db


async def create_user_data_from_user_async(
    db: AsyncSession,
    *,
    user: models.User,
    public_metadata: dict,
) -> interfaces.UserData:
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        public_metadata: TODO: describe.
    """
    result = await db.execute(
        sa.select(models.UserProject).filter(models.UserProject.user_id == user.user_id)
    )
    user_projects = result.scalars().all()
    operational_project_ids = [p.operational_project_id for p in user_projects]

    return interfaces.UserData(
        user_id=user.user_id,
        company_id=user.company_id,
        public_metadata=public_metadata,
        api_key=user.api_key,
        operational_project_ids=operational_project_ids,
        user_type_id=user.user_type_id,
    )


async def get_user_data_from_api_key_async(
    db: AsyncSession,
    *,
    x_api_key: str,
    api_prod: bool,
) -> interfaces.UserData | None:
    """todo

    Args:
        db: TODO: describe.
        x_api_key: TODO: describe.
        api_prod: TODO: describe.
    """
    if x_api_key:
        result = await db.execute(
            sa.select(models.User).filter(models.User.api_key == x_api_key)
        )
        user = result.scalars().first()
        if user:
            if api_prod:
                clerk_secret = settings.CLERK_SECRET_KEY
            else:
                clerk_secret = settings.CLERK_SECRET_KEY_DEVELOPMENT

            # Query the Clerk API to get the user's public metadata.
            # NOTE: Every once in a while the Clerk API errors out.
            # This is a simple retry mechanism in an effort to reduce
            # the number of errors.
            async with httpx.AsyncClient() as client:
                last_exception: Exception | None = None
                for _ in range(3):
                    try:
                        clerk_response = await client.get(
                            f"https://api.clerk.com/v1/users/{user.user_id}",
                            headers={"Authorization": f"Bearer {clerk_secret}"},
                            timeout=5,
                        )
                        clerk_response.raise_for_status()
                        # If the request is successful, break out of the loop.
                        break
                    except Exception as e:
                        # Keep track of the last exception in case all retries fail.
                        last_exception = e
                        # Wait briefly before retrying.
                        await asyncio.sleep(1)
                else:
                    # All retries failed, raise the last exception.
                    if last_exception is not None:
                        raise last_exception
                    else:
                        raise Exception("Unknown error during API key validation")

            public_metadata = clerk_response.json().get("public_metadata", {})

            return await create_user_data_from_user_async(
                db=db,
                user=user,
                public_metadata=public_metadata,
            )

    return None


async def get_user_data_from_jwt_async(
    db: AsyncSession,
    *,
    authorization: str,
    origin_prod: bool,
) -> interfaces.UserData | None:
    """todo

    Args:
        db: TODO: describe.
        authorization: TODO: describe.
        origin_prod: TODO: describe.
    """
    if authorization and authorization.startswith("Bearer"):
        token = authorization[7:]

        if origin_prod:
            uri = settings.URL_JWKS
        else:
            uri = settings.URL_JWKS_DEVELOPMENT

        client = jwt.PyJWKClient(uri)  # type: ignore
        signing_key = client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(token, signing_key, algorithms=["RS256"])
        user_id = payload.get("sub")

        public_metadata = payload.get("user", {}).get("public_metadata", {})

        result = await db.execute(
            sa.select(models.User).filter(models.User.user_id == user_id)
        )
        user = result.scalars().first()
        if user:
            return await create_user_data_from_user_async(
                db=db,
                user=user,
                public_metadata=public_metadata,
            )

    return None


async def get_jwt_user_data_async(
    db: AsyncSession = Depends(get_async_db),
    *,
    authorization: str = Header(None),
    origin_prod: bool = Depends(is_prod_origin),
) -> interfaces.UserData:
    """todo

    Args:
        db: TODO: describe.
        authorization: TODO: describe.
        origin_prod: TODO: describe.
    """
    user_data = await get_user_data_from_jwt_async(
        db=db,
        authorization=authorization,
        origin_prod=origin_prod,
    )

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user_data


async def get_api_user_data_async(
    db: AsyncSession = Depends(get_async_db),
    *,
    x_api_key: str = Header(None),
    api_prod: bool = Depends(is_prod_api),
) -> interfaces.UserData:
    """todo

    Args:
        db: TODO: describe.
        x_api_key: TODO: describe.
        api_prod: TODO: describe.
    """
    user_data = await get_user_data_from_api_key_async(
        db=db,
        x_api_key=x_api_key,
        api_prod=api_prod,
    )

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user_data


async def get_user_data_async(
    db: AsyncSession = Depends(get_async_db),
    *,
    api_prod: bool = Depends(is_prod_api),
    origin_prod: bool = Depends(is_prod_origin),
    authorization: str = Header(None),
    x_api_key: str = Header(None),
) -> interfaces.UserData:
    """todo

    Args:
        db: TODO: describe.
        api_prod: TODO: describe.
        origin_prod: TODO: describe.
        authorization: TODO: describe.
        x_api_key: TODO: describe.
    """

    user_data = await get_user_data_from_api_key_async(
        db=db,
        x_api_key=x_api_key,
        api_prod=api_prod,
    )
    if not user_data:
        try:
            user_data = await get_user_data_from_jwt_async(
                db=db,
                authorization=authorization,
                origin_prod=origin_prod,
            )
        except Exception:
            user_data = await get_user_data_from_jwt_async(
                db=db,
                authorization=authorization,
                origin_prod=(not origin_prod),
            )

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user_data


def check_project_access_async(
    *,
    user_data: interfaces.UserData = Depends(get_user_data_async),
    project_id: UUID = Path(...),
):
    """Handle check project access async.

    Args:
        user_data: TODO: describe.
        project_id: TODO: describe.
    """
    if project_id not in user_data.operational_project_ids:
        raise HTTPException(status_code=403, detail="Forbidden")


def check_project_access_from_query_async(
    *,
    user_data: interfaces.UserData = Depends(get_user_data_async),
    project_id: UUID,
):
    """Handle check project access async from query param.

    Args:
        user_data: TODO: describe.
        project_id: TODO: describe.
    """
    if project_id not in user_data.operational_project_ids:
        raise HTTPException(status_code=403, detail="Forbidden")


def get_is_admin_async(
    *, user_data: interfaces.UserData = Depends(get_user_data_async)
) -> bool:
    """Check if the user is an admin (or superadmin) in the database.

    Args:
        user_data (interfaces.UserData, optional): UserData object.
        Defaults to Depends(get_user_data_async).

    Returns:
        bool: True if the user is an admin, False otherwise
    """
    return user_data.user_type_id in [UserTypeEnum.SUPERADMIN, UserTypeEnum.ADMIN]


def requires_admin_async(*, is_admin: bool = Depends(get_is_admin_async)) -> None:
    """Raise a 403 error if the user is not an admin (or superadmin).

    Args:
        is_admin (bool, optional): Whether the user is an admin.
        Defaults to Depends(get_is_admin_async).

    Raises:
        HTTPException: 403 error if the user is not an admin (or superadmin)
    """
    if not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


def get_is_superadmin_async(
    *,
    user_data: interfaces.UserData = Depends(get_user_data_async),
) -> bool:
    """Check if the user is a superadmin in the database.

    Args:
        user_data (interfaces.UserData, optional): UserData object.
        Defaults to Depends(get_user_data_async).

    Returns:
        bool: True if the user is a superadmin, False otherwise
    """
    return user_data.user_type_id == UserTypeEnum.SUPERADMIN


def requires_superadmin_async(
    *, is_superadmin: bool = Depends(get_is_superadmin_async)
) -> None:
    """Raise a 403 error if the user is not a superadmin.

    Args:
        is_superadmin (bool, optional): Whether the user is a superadmin.
        Defaults to Depends(get_is_superadmin_async).

    Raises:
        HTTPException: 403 error if the user is not a superadmin
    """
    if not is_superadmin:
        raise HTTPException(status_code=403, detail="Forbidden")


## TOKEN MANAGERS ##
def tps_token_mgr_async() -> TokenManager:
    """Handle tps token mgr async."""
    return get_tps_token_manager()
