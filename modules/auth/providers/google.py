from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse

from config import settings
from modules.auth.strategy import AuthStrategy


class GoogleAuthStrategy(AuthStrategy):
    """
    Authentication strategy for Google OAuth 2.0.

    Implements the Google authorization flow using OpenID Connect
    to obtain user profile information.
    """

    @property
    def provider_name(self) -> str:
        return "google"

    def _configure(self) -> None:
        """Configure the Google OAuth client with OpenID Connect."""
        self.oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email profile",
            },
        )

    async def get_authorization_url(self, request: Request) -> RedirectResponse:
        """
        Redirect the user to Google's authorization page.

        Args:
            request: FastAPI request object.

        Returns:
            Redirect to Google's login page.
        """
        redirect_uri = settings.google_redirect_uri
        return await self.oauth.google.authorize_redirect(request, redirect_uri)

    async def handle_callback(self, request: Request) -> dict[str, Any]:
        """
        Process the callback from Google after authorization.

        Args:
            request: Request with the authorization code.

        Returns:
            Authenticated user information.
        """
        token = await self.oauth.google.authorize_access_token(request)
        return self.get_user_info(token)

    def get_user_info(self, token: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user information from the Google token.

        The token includes userinfo directly when using OpenID Connect.

        Args:
            token: OAuth token with OpenID Connect claims.

        Returns:
            Normalized dictionary with user information.
        """
        userinfo = token.get("userinfo", {})

        return {
            "provider": self.provider_name,
            "id": userinfo.get("sub"),
            "email": userinfo.get("email"),
            "email_verified": userinfo.get("email_verified", False),
            "name": userinfo.get("name"),
            "given_name": userinfo.get("given_name"),
            "family_name": userinfo.get("family_name"),
            "picture": userinfo.get("picture"),
            "locale": userinfo.get("locale"),
        }
