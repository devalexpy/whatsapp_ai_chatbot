from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.auth.jwt import decode_token
from modules.users import service as user_service
from modules.users.models import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        token: JWT access token from Authorization header.

    Returns:
        The authenticated User.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    if payload.type != "access":
        raise credentials_exception

    user = await user_service.get_by_id(payload.sub)
    if not user:
        raise credentials_exception

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.

    Args:
        credentials: HTTP Bearer credentials from Authorization header.

    Returns:
        The authenticated User or None.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.type != "access":
        return None

    return await user_service.get_by_id(payload.sub)


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
