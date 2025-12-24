from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, field_serializer


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    email: str
    name: str
    picture: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("id")
    def serialize_id(self, value: PydanticObjectId) -> str:
        return str(value)
