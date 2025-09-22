from typing import Any, Literal

import jwt
import sentry_sdk
from clerk_backend_api import Clerk
from clerk_backend_api.models import ClerkErrors
from fastapi import Depends, Header, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app import settings
from app.dependencies import get_async_db
from app.interfaces import UserAuthed
from core.models import User, UserProject

# API key authentication using a header
# https://fastapi.tiangolo.com/reference/security/#fastapi.security.APIKeyHeader
header_scheme = APIKeyHeader(
    name="x-api-key",
    scheme_name="API Key",
    description="Enter your API key to use the interactive documentation.",
    auto_error=False,
)


async def get_user(
    *,
    api_key: str = Depends(header_scheme),
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_async_db),
) -> UserAuthed:
    """Get the user from the database using the API key or JWT token."""
    jwt_token = _get_jwt_token(authorization=authorization)

    # If no API key or JWT token is provided, raise an error
    if not api_key and not jwt_token:
        raise HTTPException(status_code=401, detail="No API key or JWT token provided")

    # Try to authenticate using either the API key or the JWT token
    # NOTE: At this point, we know at least one of the two is provided
    try:
        # API key
        if api_key:
            return await _get_api_user(db=db, api_key=api_key)

        # JWT token
        elif jwt_token:
            return await _get_jwt_user(db=db, jwt_token=jwt_token)

        # Although this else block should never be reached
        # (assuming the if/elif above are exhaustive), we include it to
        # eliminate the possibility of a bug
        else:
            raise HTTPException(status_code=401, detail="Invalid API key or JWT token")

    # If an HTTPException is raised, simply re-raise it
    except HTTPException as e:
        raise e

    # If an unexpected error occurs, log the error and raise an HTTPException
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=401,
            detail="Unable to authenticate. Try again later.",
        )


async def _get_api_user(*, db: AsyncSession, api_key: str) -> UserAuthed:
    # Query the database for a user with the given API key
    query = select(User).filter(User.api_key == api_key)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # If a user with the given API key is not found, raise an error
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Get the user from Clerk and retrieve their public metadata
    clerk_secret_key = _get_clerk_secret_key()
    try:
        with Clerk(bearer_auth=clerk_secret_key) as clerk:
            clerk_user = clerk.users.get(user_id=user.user_id)
            if clerk_user is None:
                raise HTTPException(status_code=401, detail="Unable to find user")
            public_metadata = clerk_user.public_metadata
    except ClerkErrors:
        raise HTTPException(status_code=401, detail="Unable to find user")

    return await _generate_user_data(
        db=db,
        user=user,
        public_metadata=public_metadata,  # pyright: ignore
        authentication_method="api-key",
    )


async def _get_jwt_user(*, db: AsyncSession, jwt_token: str) -> UserAuthed:
    clerk_url_jwks = _get_clerk_url_jwks()

    # Verify and decode the JWT
    jwt_client = jwt.PyJWKClient(clerk_url_jwks)
    signing_key = jwt_client.get_signing_key_from_jwt(jwt_token).key
    payload = jwt.decode(jwt_token, signing_key, algorithms=["RS256"])

    # Get the Clerk user ID from the JWT
    user_id = payload.get("sub")

    # Query the database for a user with the given Clerk user ID
    query = select(User).filter(User.user_id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Unable to find user")

    # Get the public metadata from the JWT
    public_metadata = payload.get("user", {}).get("public_metadata", {})

    return await _generate_user_data(
        db=db,
        user=user,
        public_metadata=public_metadata,
        authentication_method="jwt",
    )


async def _generate_user_data(
    *,
    db: AsyncSession,
    user: User,
    public_metadata: dict[str, Any],
    authentication_method: Literal["api-key", "jwt"],
) -> UserAuthed:
    # Get the user projects from the database
    query = select(UserProject).filter(UserProject.user_id == user.user_id)
    result = await db.execute(query)
    user_projects = result.scalars().all()
    operational_project_ids = [p.operational_project_id for p in user_projects]

    return UserAuthed(
        user_id=user.user_id,
        company_id=user.company_id,
        public_metadata=public_metadata,
        operational_project_ids=operational_project_ids,
        user_type_id=user.user_type_id,
        authentication_method=authentication_method,
    )


def _get_jwt_token(*, authorization: str) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    else:
        return None


def _get_clerk_secret_key() -> str:
    # Get the Clerk application based on the environment
    clerk_application = _get_clerk_application()

    # Get the Clerk secret key based on the application
    clerk_secret_key = (
        settings.CLERK_SECRET_KEY
        if clerk_application == "production"
        else settings.CLERK_SECRET_KEY_DEVELOPMENT
    )

    # If the Clerk secret key is not found, raise an error
    if not clerk_secret_key:
        raise HTTPException(status_code=500, detail="Authentication secret not found")

    return clerk_secret_key


def _get_clerk_url_jwks() -> str:
    # Get the Clerk application based on the environment
    clerk_application = _get_clerk_application()

    # Get the Clerk URL JWKS based on the application
    clerk_url_jwks = (
        settings.URL_JWKS
        if clerk_application == "production"
        else settings.URL_JWKS_DEVELOPMENT
    )

    # If the Clerk URL JWKS is not found, raise an error
    if not clerk_url_jwks:
        raise HTTPException(status_code=500, detail="Authentication secret not found")

    return clerk_url_jwks


def _get_clerk_application() -> Literal["development", "production"]:
    environment = settings.ENVIRONMENT
    if environment in ["development", "staging"]:
        return "development"
    elif environment == "production":
        return "production"
    else:
        raise HTTPException(status_code=500, detail="Invalid environment")
