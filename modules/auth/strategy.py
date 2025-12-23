from abc import ABC, abstractmethod
from typing import Any

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import RedirectResponse


class AuthStrategy(ABC):
    """
    Base interface for OAuth authentication strategies.

    Implements the Strategy pattern allowing to swap
    different authentication providers transparently.
    """

    def __init__(self, oauth: OAuth) -> None:
        self.oauth = oauth
        self._configure()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name of the authentication provider."""
        ...

    @abstractmethod
    def _configure(self) -> None:
        """Configure the OAuth client for this provider."""
        ...

    @abstractmethod
    async def get_authorization_url(self, request: Request) -> RedirectResponse:
        """
        Generate the authorization URL and redirect the user to the provider.

        Args:
            request: Starlette/FastAPI request object.

        Returns:
            RedirectResponse to the OAuth provider.
        """
        ...

    @abstractmethod
    async def handle_callback(self, request: Request) -> dict[str, Any]:
        """
        Process the OAuth provider callback after authorization.

        Args:
            request: Starlette/FastAPI request with the authorization code.

        Returns:
            Dictionary with the authenticated user information.
        """
        ...

    @abstractmethod
    def get_user_info(self, token: dict[str, Any]) -> dict[str, Any]:
        """
        Extract and normalize user information from the token.

        Args:
            token: OAuth token containing user information.

        Returns:
            Normalized dictionary with user data.
        """
        ...
