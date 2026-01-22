"""
Authentication service for user login, registration, and token management.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
)
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import TokenResponse, UserRegister


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, data: UserRegister) -> User:
        """
        Register a new user.

        Args:
            data: Registration data

        Returns:
            Created user

        Raises:
            AlreadyExistsException: If email or phone already exists
        """
        # Check if email exists
        if await self.user_repo.email_exists(data.email):
            raise AlreadyExistsException("Un compte avec cet email existe déjà")

        # Check if phone exists
        if data.phone and await self.user_repo.phone_exists(data.phone):
            raise AlreadyExistsException(
                "Un compte avec ce numéro de téléphone existe déjà"
            )

        # Create user
        user_data = data.model_dump(exclude={"password"})
        user_data["hashed_password"] = get_password_hash(data.password)

        user = await self.user_repo.create(user_data)

        return user

    async def authenticate(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Authenticated user

        Raises:
            InvalidCredentialsException: If credentials are invalid
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise InvalidCredentialsException()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException()

        # Update last login
        await self.user_repo.update_last_login(user)

        return user

    def create_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for user.

        Args:
            user: User to create tokens for

        Returns:
            Token response with access and refresh tokens
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token response

        Raises:
            InvalidTokenException: If refresh token is invalid
        """
        payload = decode_token(refresh_token)

        if not payload:
            raise InvalidTokenException()

        if payload.get("type") != "refresh":
            raise InvalidTokenException()

        user_id = payload.get("sub")
        user = await self.user_repo.get(user_id)

        if not user or not user.is_active:
            raise InvalidTokenException()

        return self.create_tokens(user)

    async def verify_email_token(self, token: str) -> User:
        """
        Verify email verification token.

        Args:
            token: Email verification token

        Returns:
            Verified user

        Raises:
            InvalidTokenException: If token is invalid
        """
        payload = decode_token(token)

        if not payload:
            raise InvalidTokenException()

        if payload.get("type") != "verification":
            raise InvalidTokenException()

        email = payload.get("sub")
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise InvalidTokenException()

        await self.user_repo.verify_email(user)

        return user

    async def request_password_reset(self, email: str) -> str | None:
        """
        Request password reset token.

        Args:
            email: User email

        Returns:
            Reset token if user exists, None otherwise
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal if email exists
            return None

        return create_password_reset_token(email)

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user password with token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            Updated user

        Raises:
            InvalidTokenException: If token is invalid
        """
        payload = decode_token(token)

        if not payload:
            raise InvalidTokenException()

        if payload.get("type") != "reset":
            raise InvalidTokenException()

        email = payload.get("sub")
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise InvalidTokenException()

        hashed_password = get_password_hash(new_password)
        user = await self.user_repo.update(user, {"hashed_password": hashed_password})

        return user

    def create_verification_token(self, email: str) -> str:
        """Create email verification token."""
        return create_verification_token(email)
