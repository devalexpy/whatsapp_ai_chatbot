from beanie import PydanticObjectId

from modules.users.models import User


async def get_by_id(user_id: str) -> User | None:
    """
    Get a user by ID.

    Args:
        user_id: The user's ID.

    Returns:
        User if found, None otherwise.
    """
    return await User.get(PydanticObjectId(user_id))


async def get_by_email(email: str) -> User | None:
    """
    Get a user by email.

    Args:
        email: The user's email address.

    Returns:
        User if found, None otherwise.
    """
    return await User.find_one(User.email == email)


async def create(email: str, name: str, picture: str = "") -> User:
    """
    Create a new user.

    Args:
        email: User's email address.
        name: User's display name.
        picture: User's profile picture URL.

    Returns:
        The created User.
    """
    user = User(email=email, name=name, picture=picture)
    await user.insert()
    return user


async def get_or_create(email: str, name: str, picture: str = "") -> tuple[User, bool]:
    """
    Get an existing user by email or create a new one.

    Args:
        email: User's email address.
        name: User's display name.
        picture: User's profile picture URL.

    Returns:
        Tuple of (User, created) where created is True if user was created.
    """
    user = await get_by_email(email)
    if user:
        return user, False

    user = await create(email=email, name=name, picture=picture)
    return user, True
