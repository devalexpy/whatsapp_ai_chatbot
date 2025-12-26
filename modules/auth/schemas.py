"""Authentication schemas for API validation and documentation."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT authentication token response."""

    access_token: str = Field(
        description="JWT access token to authenticate requests",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTIiLCJleHAiOjE3MDM2MTA4MDAsInR5cGUiOiJhY2Nlc3MifQ.abc123"
        ],
    )
    refresh_token: str = Field(
        description="Refresh token to obtain new tokens when access_token expires",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTIiLCJleHAiOjE3MDM2OTcyMDAsInR5cGUiOiJyZWZyZXNoIn0.xyz789"
        ],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str = Field(description="User ID (subject)")
    exp: int = Field(description="Unix expiration timestamp")
    type: str = Field(description="Token type: 'access' or 'refresh'")
