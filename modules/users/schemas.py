"""User schemas for API validation and documentation."""

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class UserResponse(BaseModel):
    """User information response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "email": "user@example.com",
                "name": "John Doe",
                "picture": "https://lh3.googleusercontent.com/a/ACg8...",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )

    id: PydanticObjectId = Field(description="Unique user ID")
    email: str = Field(description="User email address")
    name: str = Field(description="User full name")
    picture: str = Field(description="Profile picture URL (from Google)")
    created_at: datetime = Field(description="Account creation date")
    updated_at: datetime = Field(description="Last update date")

    @field_serializer("id")
    def serialize_id(self, value: PydanticObjectId) -> str:
        return str(value)
