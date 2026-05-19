from typing import Any, Literal

import sentry_sdk
from clerk_backend_api import Clerk
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.security import authenticate_request_async
from clerk_backend_api.security.types import AuthenticateRequestOptions, AuthStatus
from core.models import User, UserProject
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app import settings
from app.dependencies import get_async_db
from app.interfaces import UserAuthed
from app.logger import get_logger

logger = get_logger(name=__name__)


async def get_user(
    *,
    request: Request,
    x_api_key: str = Header(None),
    db: AsyncSession = Depends(get_async_db),
) -> UserAuthed:
    """Get the user from the database using the API key or JWT token.

    Args:
        request: Incoming HTTP request containing the x-api-key header.
        x_api_key: API key from the x-api-key header, if provided.
        db: Database session used to look up the user.
    """
    jwt_token = _get_jwt_token(request=request)

    # If no API key or JWT token is provided, raise an error
    if not x_api_key and not jwt_token:
        raise HTTPException(status_code=401, detail="No API key or JWT token provided")

    # Try to authenticate using either the API key or the JWT token
    # NOTE: At this point, we know at least one of the two is provided
    try:
        # API key
        if x_api_key:
            return await _get_api_user(db=db, x_api_key=x_api_key)

        # JWT token
        elif jwt_token:
            return await _get_jwt_user(db=db, request=request)

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
        logger.error(
            "Authentication failed for %s: %s",
            request.url.path,
            type(e).__name__,
        )
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=401,
            detail="Unable to authenticate. Try again later.",
        )


async def _get_api_user(*, db: AsyncSession, x_api_key: str) -> UserAuthed:
    # Query the database for a user with the given API key
    """Look up and validate a user using an API key.

    Args:
        db: Database session used to look up the user.
        x_api_key: API key provided in the request headers.
    """
    query = select(User).where(User.api_key == x_api_key)
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


async def _get_jwt_user(
    *,
    db: AsyncSession,
    request: Request,
) -> UserAuthed:
    """Look up and validate a user using a JWT bearer token.

    Args:
        db: Database session used to look up the user.
        request: Incoming HTTP request used for Clerk request authentication.
    """
    clerk_secret_key = _get_clerk_secret_key()

    request_state = await authenticate_request_async(
        request,
        AuthenticateRequestOptions(secret_key=clerk_secret_key),
    )

    if request_state.status != AuthStatus.SIGNED_IN or request_state.payload is None:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {request_state.status.value}",
        )

    payload = request_state.payload

    # Get the Clerk user ID from the JWT
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

    # Query the database for a user with the given Clerk user ID
    query = select(User).where(User.user_id == user_id)
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
    """Generate a UserAuthed payload for the authenticated user.

    Args:
        db: Database session used to load user projects.
        user: User model retrieved from the database.
        public_metadata: Public metadata from the identity provider.
        authentication_method: Authentication source that was used.
    """
    query = select(UserProject).where(UserProject.user_id == user.user_id)
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


def _get_jwt_token(*, request: Request) -> str | None:
    """Extract a bearer token from the incoming request's Authorization header.

    Args:
        request: Incoming HTTP request containing the Authorization header.
    """
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.partition(" ")[2].strip()
    else:
        return None


def _get_clerk_secret_key() -> str:
    # Get the Clerk application based on the environment
    """Return the Clerk secret key for the active environment."""
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


def _get_clerk_application() -> Literal["development", "production"]:
    """Return the Clerk application name for the current environment."""
    environment = settings.ENVIRONMENT
    if environment in ["production", "demo"]:
        return "production"
    else:
        return "development"
