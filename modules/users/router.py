from fastapi import APIRouter

from modules.users.dependencies import CurrentUser
from modules.users.schemas import UserResponse

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
async def get_user(current_user: CurrentUser) -> UserResponse:
    """
    Get current authenticated user.

    Args:
        current_user: The authenticated user.

    Returns:
        The authenticated user.
    """
    return current_user
