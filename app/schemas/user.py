"""
User schemas for validation and serialization.
"""
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema


# --- Authentication Schemas ---
class UserLogin(BaseSchema):
    """Login request schema."""

    email: EmailStr
    password: str = Field(min_length=8)


class UserRegister(BaseSchema):
    """Registration request schema."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{8,15}$")
    role: UserRole = UserRole.TENANT

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class TokenResponse(BaseSchema):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseSchema):
    """Refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseSchema):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation."""

    token: str
    new_password: str = Field(min_length=8)


class ChangePassword(BaseSchema):
    """Change password request."""

    current_password: str
    new_password: str = Field(min_length=8)


# --- User Profile Schemas ---
class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserCreate(UserBase):
    """User creation schema (internal use)."""

    password: str
    role: UserRole = UserRole.TENANT


class UserUpdate(BaseSchema):
    """User update schema."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{8,15}$")
    bio: str | None = None
    notification_preferences: dict | None = None


class UserResponse(UserBase, IDSchema, TimestampSchema):
    """User response schema (public)."""

    role: UserRole
    is_active: bool
    is_verified: bool
    email_verified_at: datetime | None = None
    phone_verified_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserProfileResponse(UserResponse):
    """Detailed user profile response."""

    identity_verified_at: datetime | None = None
    notification_preferences: dict | None = None
    last_login_at: datetime | None = None


class UserPublicProfile(BaseSchema):
    """Public user profile (limited info)."""

    id: UUID
    first_name: str
    last_name: str | None = None
    avatar_url: str | None = None
    is_verified: bool
    created_at: datetime

    @property
    def display_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name


# --- Admin Schemas ---
class AdminUserUpdate(BaseSchema):
    """Admin user update schema."""

    role: UserRole | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    is_superuser: bool | None = None


class UserListResponse(BaseSchema):
    """User list item for admin."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
