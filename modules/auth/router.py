from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from starlette.responses import RedirectResponse

from config import settings
from modules.auth.context import AuthContext
from modules.auth.jwt import create_tokens, decode_token
from modules.auth.schemas import Token
from modules.users import service as user_service

# Global OAuth instance
oauth = OAuth()

# Authentication context
auth_context = AuthContext(oauth)

# Authentication router
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/providers")
async def list_providers() -> dict[str, list[str]]:
    """List available authentication providers."""
    return {"providers": auth_context.available_providers}


@auth_router.get("/{provider}/login")
async def login(request: Request, provider: str) -> RedirectResponse:
    """
    Start the OAuth authentication flow.

    Args:
        request: FastAPI request object.
        provider: Provider name (e.g., "google").

    Returns:
        Redirect to the OAuth provider for authorization.
    """
    return await auth_context.login(request, provider_name=provider)


@auth_router.get("/{provider}/callback")
async def callback(request: Request, provider: str) -> Token:
    """
    OAuth provider callback after authorization.

    Args:
        request: Request with the authorization code.
        provider: Provider name sending the callback.

    Returns:
        JWT tokens for authentication.
    """
    user_info = await auth_context.callback(request, provider_name=provider)

    # Find or create user using the user service
    user, _ = await user_service.get_or_create(
        email=user_info["email"],
        name=user_info["name"],
        picture=user_info.get("picture", ""),
    )

    # Generate tokens
    tokens = create_tokens(str(user.id))
    return Token(**tokens)


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str) -> Token:
    """
    Refresh access token using a valid refresh token.

    Args:
        refresh_token: Valid JWT refresh token.

    Returns:
        New JWT tokens.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    payload = decode_token(refresh_token)

    if not payload or payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists using the user service
    user = await user_service.get_by_id(payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    tokens = create_tokens(str(user.id))
    return Token(**tokens)


def setup_auth(app: Any) -> None:
    """
    Configure the FastAPI application with OAuth authentication.

    Args:
        app: FastAPI instance.

    Usage:
        from fastapi import FastAPI
        from modules.auth.router import auth_router, setup_auth

        app = FastAPI()
        setup_auth(app)
        app.include_router(auth_router)
    """
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
    )
