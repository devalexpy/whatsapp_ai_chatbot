from typing import Any

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import RedirectResponse

from modules.auth.providers.google import GoogleAuthStrategy
from modules.auth.strategy import AuthStrategy


class AuthContext:
    """
    Authentication context that manages OAuth strategies.

    Implements the Strategy pattern allowing to dynamically switch
    between different authentication providers.

    Usage:
        oauth = OAuth()
        auth_context = AuthContext(oauth)

        # Use Google by default
        auth_context.set_strategy("google")

        # Or switch to another provider
        auth_context.set_strategy("github")
    """

    def __init__(self, oauth: OAuth) -> None:
        self.oauth = oauth
        self._strategies: dict[str, AuthStrategy] = {}
        self._current_strategy: AuthStrategy | None = None

        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register default authentication strategies."""
        self.register_strategy(GoogleAuthStrategy(self.oauth))

    def register_strategy(self, strategy: AuthStrategy) -> None:
        """
        Register a new authentication strategy.

        Args:
            strategy: AuthStrategy instance to register.
        """
        self._strategies[strategy.provider_name] = strategy

    def set_strategy(self, provider_name: str) -> None:
        """
        Set the active strategy by provider name.

        Args:
            provider_name: Provider name (e.g., "google", "github").

        Raises:
            ValueError: If the provider is not registered.
        """
        if provider_name not in self._strategies:
            available = ", ".join(self._strategies.keys())
            raise ValueError(
                f"Provider '{provider_name}' not registered. "
                f"Available providers: {available}"
            )
        self._current_strategy = self._strategies[provider_name]

    def get_strategy(self, provider_name: str | None = None) -> AuthStrategy:
        """
        Get a strategy by name or the current strategy.

        Args:
            provider_name: Provider name (optional).

        Returns:
            The requested strategy or the current one.

        Raises:
            ValueError: If no strategy is set or the provider doesn't exist.
        """
        if provider_name:
            if provider_name not in self._strategies:
                available = ", ".join(self._strategies.keys())
                raise ValueError(
                    f"Provider '{provider_name}' not registered. "
                    f"Available providers: {available}"
                )
            return self._strategies[provider_name]

        if not self._current_strategy:
            raise ValueError("No authentication strategy set")

        return self._current_strategy

    @property
    def available_providers(self) -> list[str]:
        """List of available authentication providers."""
        return list(self._strategies.keys())

    async def login(
        self, request: Request, provider_name: str | None = None
    ) -> RedirectResponse:
        """
        Start the OAuth authentication flow.

        Args:
            request: FastAPI request object.
            provider_name: Provider to use (optional, uses current if not specified).

        Returns:
            Redirect to the OAuth provider.
        """
        strategy = self.get_strategy(provider_name)
        return await strategy.get_authorization_url(request)

    async def callback(
        self, request: Request, provider_name: str | None = None
    ) -> dict[str, Any]:
        """
        Process the OAuth provider callback.

        Args:
            request: Request with the authorization code.
            provider_name: Provider sending the callback.

        Returns:
            Authenticated user information.
        """
        strategy = self.get_strategy(provider_name)
        return await strategy.handle_callback(request)
