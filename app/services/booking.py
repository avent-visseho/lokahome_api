"""
Booking service for reservation management operations.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookingAlreadyExistsException,
    BusinessLogicException,
    InsufficientPermissionsException,
    NotFoundException,
    PropertyNotAvailableException,
)
from app.models.booking import Booking, BookingStatus
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.repositories.booking import BookingRepository
from app.repositories.property import PropertyRepository
from app.schemas.booking import (
    AvailabilityResponse,
    BookingCreate,
    BookingPriceCalculation,
    BookingUpdate,
)


class BookingService:
    """Service for booking operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.booking_repo = BookingRepository(session)
        self.property_repo = PropertyRepository(session)

    async def get_booking(self, booking_id: UUID) -> Booking:
        """Get booking by ID."""
        booking = await self.booking_repo.get_with_details(booking_id)
        if not booking:
            raise NotFoundException("Réservation")
        return booking

    async def get_booking_by_reference(self, reference: str) -> Booking:
        """Get booking by reference code."""
        booking = await self.booking_repo.get_by_reference(reference)
        if not booking:
            raise NotFoundException("Réservation")
        return booking

    def calculate_price(
        self,
        property_obj: Property,
        check_in: date,
        check_out: date,
    ) -> BookingPriceCalculation:
        """Calculate booking price breakdown."""
        nights = (check_out - check_in).days

        # Convert price based on rental period to daily rate
        price_per_night = property_obj.price
        if property_obj.rental_period.value == "monthly":
            price_per_night = property_obj.price / Decimal("30")
        elif property_obj.rental_period.value == "weekly":
            price_per_night = property_obj.price / Decimal("7")
        elif property_obj.rental_period.value == "yearly":
            price_per_night = property_obj.price / Decimal("365")

        base_price = price_per_night * nights
        service_fee = base_price * Decimal("0.05")  # 5% service fee
        deposit = property_obj.deposit

        total = base_price + service_fee
        if deposit:
            total += deposit

        return BookingPriceCalculation(
            nights=nights,
            price_per_night=price_per_night.quantize(Decimal("0.01")),
            base_price=base_price.quantize(Decimal("0.01")),
            service_fee=service_fee.quantize(Decimal("0.01")),
            deposit=deposit,
            total_amount=total.quantize(Decimal("0.01")),
            currency=property_obj.currency,
        )

    async def check_availability(
        self,
        property_id: UUID,
        check_in: date,
        check_out: date,
    ) -> AvailabilityResponse:
        """Check property availability for dates."""
        property_obj = await self.property_repo.get_with_details(property_id)
        if not property_obj:
            raise NotFoundException("Bien immobilier")

        if property_obj.status != PropertyStatus.ACTIVE:
            raise PropertyNotAvailableException()

        if not property_obj.is_available:
            raise PropertyNotAvailableException()

        # Check for conflicting bookings
        is_available = await self.booking_repo.check_availability(
            property_id, check_in, check_out
        )

        price_calc = self.calculate_price(property_obj, check_in, check_out)

        return AvailabilityResponse(
            is_available=is_available,
            property_id=property_id,
            check_in=check_in,
            check_out=check_out,
            price_per_period=property_obj.price,
            total_price=price_calc.base_price,
            service_fee=price_calc.service_fee,
            deposit=price_calc.deposit,
            total_amount=price_calc.total_amount,
            currency=property_obj.currency,
        )

    async def create_booking(
        self, tenant: User, data: BookingCreate
    ) -> Booking:
        """
        Create a new booking.

        Args:
            tenant: User making the booking
            data: Booking data

        Returns:
            Created booking

        Raises:
            PropertyNotAvailableException: If property not available
            BookingAlreadyExistsException: If dates conflict
        """
        # Validate dates
        if data.check_in < date.today():
            raise BusinessLogicException(
                "La date d'arrivée ne peut pas être dans le passé"
            )

        # Get property
        property_obj = await self.property_repo.get_with_details(data.property_id)
        if not property_obj:
            raise NotFoundException("Bien immobilier")

        if property_obj.status != PropertyStatus.ACTIVE:
            raise PropertyNotAvailableException()

        if not property_obj.is_available:
            raise PropertyNotAvailableException()

        # Cannot book own property
        if property_obj.owner_id == tenant.id:
            raise BusinessLogicException(
                "Vous ne pouvez pas réserver votre propre bien"
            )

        # Check minimum stay
        if property_obj.minimum_stay:
            stay_duration = (data.check_out - data.check_in).days
            if stay_duration < property_obj.minimum_stay:
                raise BusinessLogicException(
                    f"La durée minimale de séjour est de {property_obj.minimum_stay} jours"
                )

        # Check guests count
        if property_obj.max_occupants and data.guests_count > property_obj.max_occupants:
            raise BusinessLogicException(
                f"Nombre maximum d'occupants: {property_obj.max_occupants}"
            )

        # Check availability
        is_available = await self.booking_repo.check_availability(
            data.property_id, data.check_in, data.check_out
        )
        if not is_available:
            raise BookingAlreadyExistsException()

        # Calculate price
        price_calc = self.calculate_price(property_obj, data.check_in, data.check_out)

        # Create booking
        booking_data = {
            "property_id": data.property_id,
            "tenant_id": tenant.id,
            "check_in": data.check_in,
            "check_out": data.check_out,
            "guests_count": data.guests_count,
            "tenant_notes": data.tenant_notes,
            "base_price": price_calc.base_price,
            "service_fee": price_calc.service_fee,
            "deposit_amount": price_calc.deposit,
            "total_amount": price_calc.total_amount,
            "currency": property_obj.currency,
            "status": BookingStatus.PENDING,
        }

        return await self.booking_repo.create(booking_data)

    async def update_booking(
        self,
        booking_id: UUID,
        user: User,
        data: BookingUpdate,
    ) -> Booking:
        """Update a booking (dates, notes)."""
        booking = await self.get_booking(booking_id)

        # Only tenant can update their booking
        if booking.tenant_id != user.id:
            raise InsufficientPermissionsException()

        # Can only update pending bookings
        if booking.status != BookingStatus.PENDING:
            raise BusinessLogicException(
                "Vous ne pouvez modifier qu'une réservation en attente"
            )

        update_data = data.model_dump(exclude_unset=True)

        # If dates changed, recalculate price and check availability
        if "check_in" in update_data or "check_out" in update_data:
            new_check_in = update_data.get("check_in", booking.check_in)
            new_check_out = update_data.get("check_out", booking.check_out)

            # Check availability (excluding current booking)
            is_available = await self.booking_repo.check_availability(
                booking.property_id,
                new_check_in,
                new_check_out,
                exclude_booking_id=booking_id,
            )
            if not is_available:
                raise BookingAlreadyExistsException()

            # Recalculate price
            property_obj = await self.property_repo.get(booking.property_id)
            price_calc = self.calculate_price(property_obj, new_check_in, new_check_out)

            update_data.update({
                "base_price": price_calc.base_price,
                "service_fee": price_calc.service_fee,
                "total_amount": price_calc.total_amount,
            })

        return await self.booking_repo.update(booking, update_data)

    async def approve_booking(
        self, booking_id: UUID, landlord: User, notes: str | None = None
    ) -> Booking:
        """Approve a booking (landlord)."""
        booking = await self.get_booking(booking_id)

        # Verify landlord owns the property
        property_obj = await self.property_repo.get(booking.property_id)
        if property_obj.owner_id != landlord.id and landlord.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if booking.status != BookingStatus.PENDING:
            raise BusinessLogicException("Cette réservation n'est plus en attente")

        update_data = {"status": BookingStatus.APPROVED}
        if notes:
            update_data["landlord_notes"] = notes

        return await self.booking_repo.update(booking, update_data)

    async def reject_booking(
        self,
        booking_id: UUID,
        landlord: User,
        reason: str | None = None,
    ) -> Booking:
        """Reject a booking (landlord)."""
        booking = await self.get_booking(booking_id)

        # Verify landlord owns the property
        property_obj = await self.property_repo.get(booking.property_id)
        if property_obj.owner_id != landlord.id and landlord.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if booking.status != BookingStatus.PENDING:
            raise BusinessLogicException("Cette réservation n'est plus en attente")

        update_data = {
            "status": BookingStatus.REJECTED,
            "landlord_notes": reason,
        }

        return await self.booking_repo.update(booking, update_data)

    async def cancel_booking(
        self,
        booking_id: UUID,
        user: User,
        reason: str,
    ) -> Booking:
        """Cancel a booking."""
        booking = await self.get_booking(booking_id)

        # Determine who is cancelling
        property_obj = await self.property_repo.get(booking.property_id)
        is_tenant = booking.tenant_id == user.id
        is_landlord = property_obj.owner_id == user.id
        is_admin = user.role == UserRole.ADMIN

        if not (is_tenant or is_landlord or is_admin):
            raise InsufficientPermissionsException()

        # Cannot cancel completed bookings
        if booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise BusinessLogicException("Cette réservation ne peut plus être annulée")

        cancelled_by = "tenant" if is_tenant else "landlord"
        if is_admin and not is_landlord:
            cancelled_by = "admin"

        update_data = {
            "status": BookingStatus.CANCELLED,
            "cancelled_at": date.today(),
            "cancelled_by": cancelled_by,
            "cancellation_reason": reason,
        }

        return await self.booking_repo.update(booking, update_data)

    async def confirm_booking(self, booking_id: UUID) -> Booking:
        """Confirm booking after payment."""
        booking = await self.get_booking(booking_id)

        if booking.status != BookingStatus.APPROVED:
            raise BusinessLogicException(
                "La réservation doit être approuvée avant confirmation"
            )

        return await self.booking_repo.update(
            booking, {"status": BookingStatus.CONFIRMED}
        )

    async def get_tenant_bookings(
        self,
        tenant_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for a tenant."""
        return await self.booking_repo.get_by_tenant(
            tenant_id, status=status, skip=skip, limit=limit
        )

    async def get_landlord_bookings(
        self,
        owner_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for all properties owned by a landlord."""
        return await self.booking_repo.get_by_landlord(
            owner_id, status=status, skip=skip, limit=limit
        )

    async def get_property_bookings(
        self,
        property_id: UUID,
        *,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for a property."""
        return await self.booking_repo.get_by_property(
            property_id, status=status, skip=skip, limit=limit
        )
