"""
Database initialization utilities.
Includes super admin creation on startup.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole


async def create_superadmin(session: AsyncSession) -> User | None:
    """
    Create the super admin user if it doesn't exist.

    The super admin credentials are loaded from environment variables:
    - SUPERADMIN_EMAIL
    - SUPERADMIN_PASSWORD
    - SUPERADMIN_FIRST_NAME
    - SUPERADMIN_LAST_NAME

    Returns:
        The created or existing super admin user, or None if creation failed.
    """
    # Check if super admin already exists
    result = await session.execute(
        select(User).where(User.email == settings.SUPERADMIN_EMAIL)
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        print(f"Super admin already exists: {settings.SUPERADMIN_EMAIL}")
        return existing_admin

    # Create super admin
    superadmin = User(
        email=settings.SUPERADMIN_EMAIL,
        hashed_password=get_password_hash(settings.SUPERADMIN_PASSWORD),
        first_name=settings.SUPERADMIN_FIRST_NAME,
        last_name=settings.SUPERADMIN_LAST_NAME,
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )

    session.add(superadmin)
    await session.commit()
    await session.refresh(superadmin)

    print(f"Super admin created successfully: {settings.SUPERADMIN_EMAIL}")
    return superadmin


async def init_superadmin() -> None:
    """
    Initialize the super admin user.
    Called during application startup.
    """
    from app.core.database import async_session_maker

    async with async_session_maker() as session:
        try:
            await create_superadmin(session)
        except Exception as e:
            print(f"Error creating super admin: {e}")
            await session.rollback()


# --- Test users for development ---

TEST_USERS = [
    {
        "email": "tenant@test.com",
        "password": "Test@2024!",
        "first_name": "Kofi",
        "last_name": "Locataire",
        "role": UserRole.TENANT,
    },
    {
        "email": "landlord@test.com",
        "password": "Test@2024!",
        "first_name": "Adama",
        "last_name": "Proprietaire",
        "role": UserRole.LANDLORD,
    },
    {
        "email": "provider@test.com",
        "password": "Test@2024!",
        "first_name": "Sena",
        "last_name": "Prestataire",
        "role": UserRole.PROVIDER,
    },
]


async def create_test_users(session: AsyncSession) -> None:
    """
    Create test users for development if they don't exist.
    """
    for user_data in TEST_USERS:
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Test user already exists: {user_data['email']}")
            continue

        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            role=user_data["role"],
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        print(f"Test user created: {user_data['email']} ({user_data['role'].value})")


async def init_test_users() -> None:
    """
    Initialize test users for development.
    Called during application startup in debug mode.
    """
    from app.core.database import async_session_maker

    async with async_session_maker() as session:
        try:
            await create_test_users(session)
        except Exception as e:
            print(f"Error creating test users: {e}")
            await session.rollback()
            await session.rollback()
