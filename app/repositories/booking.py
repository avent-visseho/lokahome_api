"""
Booking repository for data access operations.
"""
import random
import string
from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus
from app.models.property import Property
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    """Repository for Booking model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Booking, session)

    def _generate_reference(self) -> str:
        """Generate unique booking reference."""
        chars = string.ascii_uppercase + string.digits
        return "BK" + "".join(random.choices(chars, k=8))

    async def create(self, data: dict) -> Booking:
        """Create booking with generated reference."""
        # Generate unique reference
        while True:
            reference = self._generate_reference()
            exists = await self.session.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.reference == reference)
            )
            if exists.scalar_one() == 0:
                break

        data["reference"] = reference
        return await super().create(data)

    async def get_with_details(self, booking_id: UUID) -> Booking | None:
        """Get booking with property and tenant loaded."""
        result = await self.session.execute(
            select(Booking)
            .options(
                selectinload(Booking.booked_property).selectinload(Property.images),
                selectinload(Booking.booked_property).selectinload(Property.owner),
                selectinload(Booking.tenant),
                selectinload(Booking.payments),
            )
            .where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> Booking | None:
        """Get booking by reference code."""
        result = await self.session.execute(
            select(Booking)
            .options(
                selectinload(Booking.booked_property).selectinload(Property.images),
                selectinload(Booking.booked_property).selectinload(Property.owner),
                selectinload(Booking.tenant),
            )
            .where(Booking.reference == reference)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        tenant_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings by tenant."""
        query = (
            select(Booking)
            .options(
                selectinload(Booking.booked_property).selectinload(Property.images),
                selectinload(Booking.booked_property).selectinload(Property.owner),
                selectinload(Booking.tenant),
            )
            .where(Booking.tenant_id == tenant_id)
        )

        if status:
            query = query.where(Booking.status == status)

        query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_property(
        self,
        property_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for a property."""
        query = (
            select(Booking)
            .options(
                selectinload(Booking.booked_property).selectinload(Property.images),
                selectinload(Booking.booked_property).selectinload(Property.owner),
                selectinload(Booking.tenant),
            )
            .where(Booking.property_id == property_id)
        )

        if status:
            query = query.where(Booking.status == status)

        query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_landlord(
        self,
        owner_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for all properties owned by a landlord."""
        query = (
            select(Booking)
            .join(Property)
            .options(
                selectinload(Booking.booked_property).selectinload(Property.images),
                selectinload(Booking.booked_property).selectinload(Property.owner),
                selectinload(Booking.tenant),
            )
            .where(Property.owner_id == owner_id)
        )

        if status:
            query = query.where(Booking.status == status)

        query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def check_availability(
        self,
        property_id: UUID,
        check_in: date,
        check_out: date,
        exclude_booking_id: UUID | None = None,
    ) -> bool:
        """Check if property is available for given dates."""
        # Statuses that block availability
        blocking_statuses = [
            BookingStatus.PENDING,
            BookingStatus.APPROVED,
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
        ]

        query = (
            select(func.count())
            .select_from(Booking)
            .where(
                and_(
                    Booking.property_id == property_id,
                    Booking.status.in_(blocking_statuses),
                    # Overlapping date check
                    or_(
                        and_(
                            Booking.check_in <= check_in,
                            Booking.check_out > check_in,
                        ),
                        and_(
                            Booking.check_in < check_out,
                            Booking.check_out >= check_out,
                        ),
                        and_(
                            Booking.check_in >= check_in,
                            Booking.check_out <= check_out,
                        ),
                    ),
                )
            )
        )

        if exclude_booking_id:
            query = query.where(Booking.id != exclude_booking_id)

        result = await self.session.execute(query)
        conflicting_count = result.scalar_one()

        return conflicting_count == 0

    async def get_overlapping_bookings(
        self,
        property_id: UUID,
        check_in: date,
        check_out: date,
    ) -> list[Booking]:
        """Get bookings that overlap with given dates."""
        blocking_statuses = [
            BookingStatus.PENDING,
            BookingStatus.APPROVED,
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
        ]

        result = await self.session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.property_id == property_id,
                    Booking.status.in_(blocking_statuses),
                    or_(
                        and_(
                            Booking.check_in <= check_in,
                            Booking.check_out > check_in,
                        ),
                        and_(
                            Booking.check_in < check_out,
                            Booking.check_out >= check_out,
                        ),
                        and_(
                            Booking.check_in >= check_in,
                            Booking.check_out <= check_out,
                        ),
                    ),
                )
            )
            .order_by(Booking.check_in)
        )
        return list(result.scalars().all())

    async def get_active_bookings_for_property(
        self, property_id: UUID
    ) -> list[Booking]:
        """Get all active bookings for a property."""
        active_statuses = [
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
        ]

        result = await self.session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.property_id == property_id,
                    Booking.status.in_(active_statuses),
                )
            )
            .order_by(Booking.check_in)
        )
        return list(result.scalars().all())

    async def count_by_status(
        self,
        status: BookingStatus,
        *,
        tenant_id: UUID | None = None,
        property_id: UUID | None = None,
    ) -> int:
        """Count bookings by status."""
        query = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.status == status)
        )

        if tenant_id:
            query = query.where(Booking.tenant_id == tenant_id)
        if property_id:
            query = query.where(Booking.property_id == property_id)

        result = await self.session.execute(query)
        return result.scalar_one()
