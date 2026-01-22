"""
User repository for data access operations.
"""
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        """Get user by phone number."""
        result = await self.session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_phone(self, identifier: str) -> User | None:
        """Get user by email or phone number."""
        result = await self.session.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == identifier.lower(),
                    User.phone == identifier,
                )
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one() > 0

    async def phone_exists(self, phone: str) -> bool:
        """Check if phone is already registered."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.phone == phone)
        )
        return result.scalar_one() > 0

    async def get_users_by_role(
        self,
        role: UserRole,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[User]:
        """Get users by role with optional filters."""
        query = select(User).where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_role(self, role: UserRole) -> int:
        """Count users by role."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.role == role)
        )
        return result.scalar_one()

    async def search_users(
        self,
        query_str: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Search users by name or email."""
        search_pattern = f"%{query_str}%"
        result = await self.session.execute(
            select(User)
            .where(
                or_(
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                )
            )
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_last_login(self, user: User) -> User:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def verify_email(self, user: User) -> User:
        """Mark user's email as verified."""
        user.email_verified_at = datetime.now(UTC)
        user.is_verified = True
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def verify_phone(self, user: User) -> User:
        """Mark user's phone as verified."""
        user.phone_verified_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_fcm_token(self, user: User, fcm_token: str) -> User:
        """Update user's FCM token for push notifications."""
        user.fcm_token = fcm_token
        await self.session.flush()
        await self.session.refresh(user)
        return user
