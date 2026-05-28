"""
Contract repository for data access operations.
"""
import random
import string
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.contract import Contract, ContractStatus
from app.models.property import Property
from app.repositories.base import BaseRepository


class ContractRepository(BaseRepository[Contract]):
    """Repository for Contract model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Contract, session)

    def _generate_reference(self) -> str:
        """Generate unique contract reference."""
        chars = string.ascii_uppercase + string.digits
        return "CTR" + "".join(random.choices(chars, k=8))

    async def create(self, data: dict) -> Contract:
        """Create contract with generated reference."""
        while True:
            reference = self._generate_reference()
            exists = await self.exists_by_field("reference", reference)
            if not exists:
                break
        data["reference"] = reference
        return await super().create(data)

    def _booking_eager_options(self):
        """Common eager loading options for booking details."""
        return [
            selectinload(Contract.booking)
            .selectinload(Booking.booked_property)
            .selectinload(Property.images),
            selectinload(Contract.booking)
            .selectinload(Booking.booked_property)
            .selectinload(Property.owner),
            selectinload(Contract.booking).selectinload(Booking.tenant),
        ]

    async def get_by_booking(self, booking_id: UUID) -> Contract | None:
        """Get contract by booking ID with eager loading."""
        result = await self.session.execute(
            select(Contract)
            .options(*self._booking_eager_options())
            .where(Contract.booking_id == booking_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> Contract | None:
        """Get contract by reference code."""
        result = await self.session.execute(
            select(Contract)
            .options(*self._booking_eager_options())
            .where(Contract.reference == reference)
        )
        return result.scalar_one_or_none()

    async def get_with_details(self, contract_id: UUID) -> Contract | None:
        """Get contract with full eager loading."""
        result = await self.session.execute(
            select(Contract)
            .options(*self._booking_eager_options())
            .where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_for_user(self, user_id: UUID) -> list[Contract]:
        """Get contracts pending signature from this user."""
        result = await self.session.execute(
            select(Contract)
            .join(Booking)
            .options(*self._booking_eager_options())
            .where(
                or_(
                    and_(
                        Contract.status == ContractStatus.PENDING_LANDLORD,
                        Booking.booked_property.has(owner_id=user_id),
                    ),
                    and_(
                        Contract.status == ContractStatus.PENDING_TENANT,
                        Booking.tenant_id == user_id,
                    ),
                )
            )
            .order_by(Contract.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_contracts(
        self,
        user_id: UUID,
        *,
        status: ContractStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Contract]:
        """Get all contracts where user is landlord or tenant."""
        query = (
            select(Contract)
            .join(Booking)
            .join(Property, Booking.property_id == Property.id)
            .options(*self._booking_eager_options())
            .where(
                or_(
                    Property.owner_id == user_id,
                    Booking.tenant_id == user_id,
                )
            )
        )

        if status:
            query = query.where(Contract.status == status)

        query = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired_contracts(self) -> list[Contract]:
        """Get contracts that have expired without full signature."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Contract).where(
                and_(
                    Contract.expires_at < now,
                    Contract.status.in_([
                        ContractStatus.PENDING_LANDLORD,
                        ContractStatus.PENDING_TENANT,
                    ]),
                )
            )
        )
        return list(result.scalars().all())
