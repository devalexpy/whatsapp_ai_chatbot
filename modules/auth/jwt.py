from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import settings
from modules.auth.schemas import TokenPayload


def create_access_token(subject: str) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (usually user ID).

    Returns:
        Encoded JWT access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (usually user ID).

    Returns:
        Encoded JWT refresh token.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_tokens(subject: str) -> dict[str, str]:
    """
    Create both access and refresh tokens.

    Args:
        subject: The subject of the token (usually user ID).

    Returns:
        Dictionary with access_token, refresh_token, and token_type.
    """
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
    }


def decode_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode.

    Returns:
        TokenPayload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except JWTError:
        return None

