"""
User service for profile management operations.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyExistsException,
    InvalidCredentialsException,
    NotFoundException,
)
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.user import ChangePassword, UserUpdate


class UserService:
    """Service for user profile operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_user(self, user_id: UUID) -> User:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundException("Utilisateur")
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        return await self.user_repo.get_by_email(email)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """
        Update user profile.

        Args:
            user: User to update
            data: Update data

        Returns:
            Updated user

        Raises:
            AlreadyExistsException: If phone already taken
        """
        update_data = data.model_dump(exclude_unset=True)

        # Check if phone is being changed and already exists
        if "phone" in update_data and update_data["phone"]:
            if update_data["phone"] != user.phone:
                if await self.user_repo.phone_exists(update_data["phone"]):
                    raise AlreadyExistsException(
                        "Ce numéro de téléphone est déjà utilisé"
                    )

        return await self.user_repo.update(user, update_data)

    async def change_password(
        self, user: User, data: ChangePassword
    ) -> User:
        """
        Change user password.

        Args:
            user: User to update
            data: Password change data

        Returns:
            Updated user

        Raises:
            InvalidCredentialsException: If current password is wrong
        """
        if not verify_password(data.current_password, user.hashed_password):
            raise InvalidCredentialsException()

        hashed_password = get_password_hash(data.new_password)
        return await self.user_repo.update(user, {"hashed_password": hashed_password})

    async def update_avatar(self, user: User, avatar_url: str) -> User:
        """Update user avatar URL."""
        return await self.user_repo.update(user, {"avatar_url": avatar_url})

    async def update_fcm_token(self, user: User, fcm_token: str) -> User:
        """Update user FCM token for push notifications."""
        return await self.user_repo.update_fcm_token(user, fcm_token)

    async def list_users(
        self,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """
        List users with filtering (admin).

        Returns:
            Tuple of (users list, total count)
        """
        filters = {}
        if role:
            filters["role"] = role
        if is_active is not None:
            filters["is_active"] = is_active

        users = await self.user_repo.get_multi(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by="created_at",
            order_desc=True,
        )

        total = await self.user_repo.count(filters=filters)

        return users, total

    async def search_users(
        self, query: str, *, skip: int = 0, limit: int = 20
    ) -> list[User]:
        """Search users by name or email."""
        return await self.user_repo.search_users(query, skip=skip, limit=limit)

    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate a user account (admin)."""
        user = await self.get_user(user_id)
        return await self.user_repo.update(user, {"is_active": False})

    async def activate_user(self, user_id: UUID) -> User:
        """Activate a user account (admin)."""
        user = await self.get_user(user_id)
        return await self.user_repo.update(user, {"is_active": True})

    async def change_role(self, user_id: UUID, new_role: UserRole) -> User:
        """Change user role (admin)."""
        user = await self.get_user(user_id)
        return await self.user_repo.update(user, {"role": new_role})
