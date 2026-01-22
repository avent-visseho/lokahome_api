"""
API dependencies for authentication and authorization.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import (
    InsufficientPermissionsException,
    InvalidTokenException,
)
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        InvalidTokenException: If token is invalid or user not found
    """
    payload = decode_token(token)

    if not payload:
        raise InvalidTokenException()

    if payload.get("type") != "access":
        raise InvalidTokenException()

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException()

    user_repo = UserRepository(session)
    user = await user_repo.get(UUID(user_id))

    if not user:
        raise InvalidTokenException()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    return current_user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current verified user."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre email",
        )
    return current_user


def require_roles(*roles: UserRole):
    """
    Dependency factory that requires specific user roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles(UserRole.ADMIN))])
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise InsufficientPermissionsException()
        return current_user

    return role_checker


# Role-specific dependencies
RequireTenant = Depends(require_roles(UserRole.TENANT, UserRole.LANDLORD, UserRole.ADMIN))
RequireLandlord = Depends(require_roles(UserRole.LANDLORD, UserRole.ADMIN))
RequireProvider = Depends(require_roles(UserRole.PROVIDER, UserRole.ADMIN))
RequireAdmin = Depends(require_roles(UserRole.ADMIN))


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
VerifiedUser = Annotated[User, Depends(get_current_verified_user)]
DbSession = Annotated[AsyncSession, Depends(get_async_session)]
