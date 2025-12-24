from typing import Any
from urllib.parse import urlencode, urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from starlette.responses import RedirectResponse

from config import settings
from modules.auth.context import AuthContext
from modules.auth.jwt import create_tokens, decode_token
from modules.auth.schemas import Token
from modules.users import service as user_service


def get_allowed_origins() -> list[str]:
    """Get list of allowed redirect origins."""
    return [
        origin.strip()
        for origin in settings.allowed_redirect_origins.split(",")
        if origin.strip()
    ]


def is_valid_redirect_uri(redirect_uri: str) -> bool:
    """Validate that redirect_uri is from an allowed origin."""
    if not redirect_uri:
        return False
    parsed = urlparse(redirect_uri)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin in get_allowed_origins()


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
async def login(
    request: Request,
    provider: str,
    redirect_uri: str | None = None,
) -> RedirectResponse:
    """
    Start the OAuth authentication flow.

    Args:
        request: FastAPI request object.
        provider: Provider name (e.g., "google").
        redirect_uri: Frontend URL to redirect after auth (must be in allowed origins).

    Returns:
        Redirect to the OAuth provider for authorization.
    """
    # Use provided redirect_uri or default to frontend_url
    final_redirect = redirect_uri or settings.frontend_url

    if not is_valid_redirect_uri(final_redirect):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid redirect_uri. Allowed origins: {get_allowed_origins()}",
        )

    # Store redirect_uri in session for callback
    request.session["redirect_uri"] = final_redirect

    return await auth_context.login(request, provider_name=provider)


@auth_router.get("/{provider}/callback")
async def callback(request: Request, provider: str) -> RedirectResponse:
    """
    OAuth provider callback after authorization.

    Args:
        request: Request with the authorization code.
        provider: Provider name sending the callback.

    Returns:
        Redirect to frontend with JWT tokens.
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

    # Get redirect_uri from session or use default
    redirect_uri = request.session.pop("redirect_uri", settings.frontend_url)

    # Redirect to frontend with tokens as query params
    query_params = urlencode(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }
    )

    return RedirectResponse(url=f"{redirect_uri}?{query_params}")


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
