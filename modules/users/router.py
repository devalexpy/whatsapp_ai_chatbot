"""Users router."""

from fastapi import APIRouter

from modules.users.dependencies import CurrentUser
from modules.users.schemas import UserResponse

users_router = APIRouter(
    prefix="/users",
    tags=["👤 Users"],
    responses={
        401: {
            "description": "Unauthorized - Invalid or expired token",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
    },
)


@users_router.get(
    "",
    response_model=UserResponse,
    summary="Get current user",
    description="""
Gets the currently authenticated user's information.

**Requires:** Valid JWT token in `Authorization: Bearer <token>` header

**Returns:**
- `id`: Unique user ID
- `email`: Email address
- `name`: Full name
- `picture`: Profile picture URL (from Google)
- `created_at`, `updated_at`: Timestamps
""",
    response_description="Authenticated user information",
)
async def get_user(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user."""
    return current_user
