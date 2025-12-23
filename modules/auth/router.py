from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from config import settings
from modules.auth.context import AuthContext

# Global OAuth instance
oauth = OAuth()

# Authentication context
auth_context = AuthContext(oauth)

# Authentication router
auth_router = APIRouter(prefix="/auth", tags=["auth"])


def get_session_middleware() -> SessionMiddleware:
    """
    Return the session middleware required for OAuth.

    Must be added to the FastAPI application:
        app.add_middleware(SessionMiddleware, secret_key=...)
    """
    return SessionMiddleware


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
async def callback(request: Request, provider: str) -> dict[str, Any]:
    """
    OAuth provider callback after authorization.

    Args:
        request: Request with the authorization code.
        provider: Provider name sending the callback.

    Returns:
        Authenticated user information.

    Note:
        In production, you should:
        - Create/update the user in the database
        - Generate a JWT or session
        - Redirect to the frontend with the token
    """
    user_info = await auth_context.callback(request, provider_name=provider)
    return {
        "message": "Authentication successful",
        "user": user_info,
    }


def setup_auth(app: Any) -> None:
    """
    Configure the FastAPI application with OAuth authentication.

    Args:
        app: FastAPI instance.

    Usage:
        from fastapi import FastAPI
        from modules.auth import auth_router, setup_auth

        app = FastAPI()
        setup_auth(app)
        app.include_router(auth_router)
    """
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
    )
