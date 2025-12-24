from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    exp: int  # Expiration timestamp
    type: str  # "access" or "refresh"
