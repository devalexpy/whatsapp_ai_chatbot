from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class User(Document):
    email: str
    name: str
    picture: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
