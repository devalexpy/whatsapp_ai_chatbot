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
auth_router = APIRouter(prefix="/auth", tags=["🔐 Auth"])


@auth_router.get(
    "/providers",
    summary="List authentication providers",
    description="Gets the list of available OAuth providers for login.",
    response_description="List of available providers",
)
async def list_providers() -> dict[str, list[str]]:
    """List available authentication providers."""
    return {"providers": auth_context.available_providers}


@auth_router.get(
    "/{provider}/login",
    summary="Start OAuth flow",
    description="""
Starts the OAuth authentication flow with the specified provider.

**Flow:**
1. Frontend redirects user to this endpoint
2. Backend redirects to OAuth provider (e.g., Google)
3. After login, redirects to `redirect_uri` with tokens

**Parameters:**
- `provider`: Provider name (e.g., "google")
- `redirect_uri`: Frontend URL to receive tokens (optional, uses FRONTEND_URL by default)
""",
    response_description="Redirect to OAuth provider",
)
async def login(
    request: Request,
    provider: str,
    redirect_uri: str | None = None,
) -> RedirectResponse:
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


@auth_router.get(
    "/{provider}/callback",
    summary="OAuth Callback",
    description="""
Callback that receives the authorization code from the OAuth provider.

**⚠️ Do not call directly.** This endpoint is automatically called
by the OAuth provider after the user authorizes the application.

After processing the callback, redirects to frontend with JWT tokens.
""",
    response_description="Redirect to frontend with tokens",
)
async def callback(request: Request, provider: str) -> RedirectResponse:
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


@auth_router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh tokens",
    description="""
Generates new access tokens using a valid refresh token.

**Usage:**
```json
{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
```

**Response:** New `access_token` and `refresh_token`.

Use this endpoint when the `access_token` expires (typically 15-30 min).
""",
    response_description="New JWT tokens",
    responses={
        401: {
            "description": "Invalid or expired refresh token",
            "content": {
                "application/json": {"example": {"detail": "Invalid refresh token"}}
            },
        },
    },
)
async def refresh_token(refresh_token: str) -> Token:
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
