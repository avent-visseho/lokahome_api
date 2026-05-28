"""
Agent/Demarcheur service for profile management, mandates, visits, and commissions.
"""
import random
import string
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AlreadyExistsException,
    BusinessLogicException,
    InsufficientPermissionsException,
    NotFoundException,
)
from app.models.agent import (
    AgentMandate,
    AgentProfile,
    MandateStatus,
    MandateType,
    PropertyVisit,
    VisitStatus,
)
from app.models.booking import Booking
from app.models.property import Property
from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


# --- Repositories ---

class AgentProfileRepository(BaseRepository[AgentProfile]):
    """Repository for AgentProfile operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgentProfile, session)

    async def get_by_user(self, user_id: UUID) -> AgentProfile | None:
        """Get agent profile by user ID with user eagerly loaded."""
        result = await self.session.execute(
            select(AgentProfile)
            .options(selectinload(AgentProfile.user))
            .where(AgentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_with_user(self, agent_id: UUID) -> AgentProfile | None:
        """Get agent profile by ID with user eagerly loaded."""
        result = await self.session.execute(
            select(AgentProfile)
            .options(selectinload(AgentProfile.user))
            .where(AgentProfile.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, agent_code: str) -> AgentProfile | None:
        """Get agent by unique agent code."""
        result = await self.session.execute(
            select(AgentProfile)
            .options(selectinload(AgentProfile.user))
            .where(AgentProfile.agent_code == agent_code)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        city: str | None = None,
        specialization: str | None = None,
        is_available: bool | None = True,
        is_verified: bool | None = None,
        min_rating: Decimal | None = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "rating",
        sort_desc: bool = True,
    ) -> list[AgentProfile]:
        """Search agents with filters."""
        query = select(AgentProfile).options(selectinload(AgentProfile.user))

        if city:
            query = query.where(AgentProfile.service_areas.contains([city]))

        if specialization:
            query = query.where(AgentProfile.specializations.contains([specialization]))

        if is_available is not None:
            query = query.where(AgentProfile.is_available == is_available)

        if is_verified is not None:
            query = query.where(AgentProfile.is_verified == is_verified)

        if min_rating is not None:
            query = query.where(AgentProfile.rating >= min_rating)

        if sort_by == "rating":
            column = AgentProfile.rating
            query = query.order_by(
                column.desc().nullslast() if sort_desc else column.asc().nullsfirst()
            )
        elif sort_by == "completed_deals":
            query = query.order_by(
                AgentProfile.completed_deals.desc()
                if sort_desc
                else AgentProfile.completed_deals.asc()
            )

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_search(
        self,
        *,
        city: str | None = None,
        specialization: str | None = None,
        is_available: bool | None = True,
        is_verified: bool | None = None,
        min_rating: Decimal | None = None,
    ) -> int:
        """Count agents matching search criteria."""
        query = select(func.count()).select_from(AgentProfile)

        if city:
            query = query.where(AgentProfile.service_areas.contains([city]))
        if specialization:
            query = query.where(AgentProfile.specializations.contains([specialization]))
        if is_available is not None:
            query = query.where(AgentProfile.is_available == is_available)
        if is_verified is not None:
            query = query.where(AgentProfile.is_verified == is_verified)
        if min_rating is not None:
            query = query.where(AgentProfile.rating >= min_rating)

        result = await self.session.execute(query)
        return result.scalar_one()


class AgentMandateRepository(BaseRepository[AgentMandate]):
    """Repository for AgentMandate operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgentMandate, session)

    async def get_with_details(self, mandate_id: UUID) -> AgentMandate | None:
        """Get mandate with agent and landlord eagerly loaded."""
        result = await self.session.execute(
            select(AgentMandate)
            .options(
                selectinload(AgentMandate.agent).selectinload(AgentProfile.user),
                selectinload(AgentMandate.landlord),
            )
            .where(AgentMandate.id == mandate_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: UUID,
        *,
        status: MandateStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentMandate]:
        """Get mandates for an agent."""
        query = select(AgentMandate).where(AgentMandate.agent_id == agent_id)

        if status:
            query = query.where(AgentMandate.status == status)

        query = query.order_by(AgentMandate.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_landlord(
        self,
        landlord_id: UUID,
        *,
        status: MandateStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentMandate]:
        """Get mandates given by a landlord."""
        query = (
            select(AgentMandate)
            .options(
                selectinload(AgentMandate.agent).selectinload(AgentProfile.user),
            )
            .where(AgentMandate.landlord_id == landlord_id)
        )

        if status:
            query = query.where(AgentMandate.status == status)

        query = query.order_by(AgentMandate.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_mandate(
        self, agent_id: UUID, property_id: UUID
    ) -> AgentMandate | None:
        """Get active mandate for agent+property."""
        result = await self.session.execute(
            select(AgentMandate).where(
                and_(
                    AgentMandate.agent_id == agent_id,
                    AgentMandate.status == MandateStatus.ACTIVE,
                    (
                        (AgentMandate.property_id == property_id)
                        | (AgentMandate.mandate_type == MandateType.GLOBAL)
                    ),
                )
            )
        )
        return result.scalar_one_or_none()

    async def has_exclusive_mandate(self, property_id: UUID) -> bool:
        """Check if property already has an exclusive mandate."""
        result = await self.session.execute(
            select(func.count())
            .select_from(AgentMandate)
            .where(
                and_(
                    AgentMandate.property_id == property_id,
                    AgentMandate.mandate_type == MandateType.EXCLUSIVE,
                    AgentMandate.status == MandateStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one() > 0


class PropertyVisitRepository(BaseRepository[PropertyVisit]):
    """Repository for PropertyVisit operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(PropertyVisit, session)

    async def get_with_details(self, visit_id: UUID) -> PropertyVisit | None:
        """Get visit with visitor eagerly loaded."""
        result = await self.session.execute(
            select(PropertyVisit)
            .options(selectinload(PropertyVisit.visitor))
            .where(PropertyVisit.id == visit_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: UUID,
        *,
        status: VisitStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PropertyVisit]:
        """Get visits organized by an agent."""
        query = (
            select(PropertyVisit)
            .options(selectinload(PropertyVisit.visitor))
            .where(PropertyVisit.agent_id == agent_id)
        )

        if status:
            query = query.where(PropertyVisit.status == status)

        query = query.order_by(PropertyVisit.scheduled_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_agent_month(self, agent_id: UUID) -> int:
        """Count visits this month for an agent."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(func.count())
            .select_from(PropertyVisit)
            .where(
                and_(
                    PropertyVisit.agent_id == agent_id,
                    extract("year", PropertyVisit.scheduled_at) == now.year,
                    extract("month", PropertyVisit.scheduled_at) == now.month,
                )
            )
        )
        return result.scalar_one()


# --- Service ---

class AgentService:
    """Service for agent/demarcheur operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_repo = AgentProfileRepository(session)
        self.mandate_repo = AgentMandateRepository(session)
        self.visit_repo = PropertyVisitRepository(session)

    # --- Agent Code Generation ---
    def _generate_agent_code(self) -> str:
        """Generate unique agent code (ex: AGT-XXXX-NNN)."""
        chars = string.ascii_uppercase
        digits = string.digits
        prefix = "AGT"
        letters = "".join(random.choices(chars, k=4))
        numbers = "".join(random.choices(digits, k=3))
        return f"{prefix}-{letters}-{numbers}"

    # --- Profile Management ---
    async def get_agent(self, agent_id: UUID) -> AgentProfile:
        """Get agent by ID."""
        agent = await self.profile_repo.get_with_user(agent_id)
        if not agent:
            raise NotFoundException("Profil agent")
        return agent

    async def get_agent_by_user(self, user_id: UUID) -> AgentProfile | None:
        """Get agent profile by user ID."""
        return await self.profile_repo.get_by_user(user_id)

    async def get_agent_by_code(self, agent_code: str) -> AgentProfile | None:
        """Get agent by code."""
        return await self.profile_repo.get_by_code(agent_code)

    async def create_agent_profile(
        self, user: User, data: dict
    ) -> AgentProfile:
        """Create an agent profile."""
        existing = await self.profile_repo.get_by_user(user.id)
        if existing:
            raise AlreadyExistsException("Profil agent")

        # Generate unique agent code
        while True:
            agent_code = self._generate_agent_code()
            existing_code = await self.profile_repo.get_by_code(agent_code)
            if not existing_code:
                break

        # Update user role if needed
        if user.role == UserRole.TENANT:
            user.role = UserRole.AGENT
            await self.session.flush()

        agent_data = {
            **data,
            "user_id": user.id,
            "agent_code": agent_code,
        }

        await self.profile_repo.create(agent_data)
        return await self.profile_repo.get_by_user(user.id)  # type: ignore[return-value]

    async def update_agent_profile(
        self, agent_id: UUID, user: User, data: dict
    ) -> AgentProfile:
        """Update agent profile."""
        agent = await self.get_agent(agent_id)

        if agent.user_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        await self.profile_repo.update(agent, data)
        return await self.profile_repo.get_by_user(agent.user_id)  # type: ignore[return-value]

    async def search_agents(
        self,
        *,
        city: str | None = None,
        specialization: str | None = None,
        is_available: bool | None = True,
        is_verified: bool | None = None,
        min_rating: Decimal | None = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "rating",
        sort_desc: bool = True,
    ) -> tuple[list[AgentProfile], int]:
        """Search agents with count."""
        agents = await self.profile_repo.search(
            city=city,
            specialization=specialization,
            is_available=is_available,
            is_verified=is_verified,
            min_rating=min_rating,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        total = await self.profile_repo.count_search(
            city=city,
            specialization=specialization,
            is_available=is_available,
            is_verified=is_verified,
            min_rating=min_rating,
        )
        return agents, total

    # --- Mandate Management ---
    async def get_mandate(self, mandate_id: UUID) -> AgentMandate:
        """Get mandate by ID."""
        mandate = await self.mandate_repo.get_with_details(mandate_id)
        if not mandate:
            raise NotFoundException("Mandat")
        return mandate

    async def create_mandate(
        self, landlord: User, data: dict
    ) -> AgentMandate:
        """Create a mandate (by landlord)."""
        agent_id = data["agent_id"]
        property_id = data.get("property_id")
        mandate_type = data.get("mandate_type", MandateType.NON_EXCLUSIVE)

        # Verify agent exists
        agent = await self.profile_repo.get(agent_id)
        if not agent:
            raise NotFoundException("Agent")

        # If property specified, verify ownership
        if property_id:
            result = await self.session.execute(
                select(Property).where(Property.id == property_id)
            )
            prop = result.scalar_one_or_none()
            if not prop:
                raise NotFoundException("Propriete")
            if prop.owner_id != landlord.id and landlord.role != UserRole.ADMIN:
                raise InsufficientPermissionsException()

            # Check exclusive mandate conflict
            if mandate_type == MandateType.EXCLUSIVE:
                if await self.mandate_repo.has_exclusive_mandate(property_id):
                    raise BusinessLogicException(
                        "Cette propriete a deja un mandat exclusif actif"
                    )

        mandate_data = {
            **data,
            "landlord_id": landlord.id,
            "status": MandateStatus.PENDING,
        }

        mandate = await self.mandate_repo.create(mandate_data)
        return await self.mandate_repo.get_with_details(mandate.id)  # type: ignore[return-value]

    async def accept_mandate(
        self, mandate_id: UUID, user: User
    ) -> AgentMandate:
        """Accept a mandate (by agent)."""
        mandate = await self.get_mandate(mandate_id)

        # Verify the agent owns this mandate
        agent = await self.profile_repo.get_by_user(user.id)
        if not agent or agent.id != mandate.agent_id:
            raise InsufficientPermissionsException()

        if mandate.status != MandateStatus.PENDING:
            raise BusinessLogicException("Ce mandat n'est plus en attente")

        now = datetime.now(timezone.utc)
        await self.mandate_repo.update(
            mandate,
            {
                "status": MandateStatus.ACTIVE,
                "started_at": now,
            },
        )
        return await self.mandate_repo.get_with_details(mandate_id)  # type: ignore[return-value]

    async def revoke_mandate(
        self, mandate_id: UUID, user: User
    ) -> AgentMandate:
        """Revoke a mandate (by landlord or admin)."""
        mandate = await self.get_mandate(mandate_id)

        if mandate.landlord_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if mandate.status not in [MandateStatus.PENDING, MandateStatus.ACTIVE]:
            raise BusinessLogicException("Ce mandat ne peut plus etre revoque")

        await self.mandate_repo.update(mandate, {"status": MandateStatus.REVOKED})
        return await self.mandate_repo.get_with_details(mandate_id)  # type: ignore[return-value]

    async def get_agent_mandates(
        self,
        agent_id: UUID,
        *,
        status: MandateStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentMandate]:
        """Get mandates for an agent."""
        return await self.mandate_repo.get_by_agent(
            agent_id, status=status, skip=skip, limit=limit
        )

    async def get_landlord_mandates(
        self,
        landlord_id: UUID,
        *,
        status: MandateStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentMandate]:
        """Get mandates given by a landlord."""
        return await self.mandate_repo.get_by_landlord(
            landlord_id, status=status, skip=skip, limit=limit
        )

    # --- Visit Management ---
    async def get_visit(self, visit_id: UUID) -> PropertyVisit:
        """Get visit by ID."""
        visit = await self.visit_repo.get_with_details(visit_id)
        if not visit:
            raise NotFoundException("Visite")
        return visit

    async def schedule_visit(
        self, agent: AgentProfile, data: dict
    ) -> PropertyVisit:
        """Schedule a property visit."""
        property_id = data["property_id"]

        # Verify agent has mandate for this property
        mandate = await self.mandate_repo.get_active_mandate(agent.id, property_id)
        if not mandate:
            raise BusinessLogicException(
                "Vous n'avez pas de mandat actif pour cette propriete"
            )

        visit_data = {
            **data,
            "agent_id": agent.id,
            "status": VisitStatus.SCHEDULED,
        }

        visit = await self.visit_repo.create(visit_data)
        return await self.visit_repo.get_with_details(visit.id)  # type: ignore[return-value]

    async def complete_visit(
        self, visit_id: UUID, user: User, data: dict | None = None
    ) -> PropertyVisit:
        """Mark visit as completed."""
        visit = await self.get_visit(visit_id)

        agent = await self.profile_repo.get_by_user(user.id)
        if not agent or agent.id != visit.agent_id:
            raise InsufficientPermissionsException()

        if visit.status != VisitStatus.SCHEDULED:
            raise BusinessLogicException("Cette visite n'est pas planifiee")

        update_data: dict = {"status": VisitStatus.COMPLETED}
        if data:
            if "agent_notes" in data:
                update_data["agent_notes"] = data["agent_notes"]
            if "visitor_feedback" in data:
                update_data["visitor_feedback"] = data["visitor_feedback"]

        await self.visit_repo.update(visit, update_data)
        return await self.visit_repo.get_with_details(visit_id)  # type: ignore[return-value]

    async def cancel_visit(
        self, visit_id: UUID, user: User
    ) -> PropertyVisit:
        """Cancel a scheduled visit."""
        visit = await self.get_visit(visit_id)

        agent = await self.profile_repo.get_by_user(user.id)
        is_agent = agent and agent.id == visit.agent_id
        is_visitor = visit.visitor_id == user.id

        if not is_agent and not is_visitor and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if visit.status != VisitStatus.SCHEDULED:
            raise BusinessLogicException("Seules les visites planifiees peuvent etre annulees")

        await self.visit_repo.update(visit, {"status": VisitStatus.CANCELLED})
        return await self.visit_repo.get_with_details(visit_id)  # type: ignore[return-value]

    async def get_agent_visits(
        self,
        agent_id: UUID,
        *,
        status: VisitStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PropertyVisit]:
        """Get visits for an agent."""
        return await self.visit_repo.get_by_agent(
            agent_id, status=status, skip=skip, limit=limit
        )

    # --- Dashboard ---
    async def get_dashboard(self, agent: AgentProfile) -> dict:
        """Get agent dashboard data."""
        # Mandate counts
        active_mandates = await self.mandate_repo.count(
            filters={"agent_id": agent.id, "status": MandateStatus.ACTIVE}
        )
        total_mandates = await self.mandate_repo.count(
            filters={"agent_id": agent.id}
        )

        # Count unique properties from active mandates
        props_result = await self.session.execute(
            select(func.count(func.distinct(AgentMandate.property_id))).where(
                and_(
                    AgentMandate.agent_id == agent.id,
                    AgentMandate.status == MandateStatus.ACTIVE,
                    AgentMandate.property_id.isnot(None),
                )
            )
        )
        total_properties = props_result.scalar_one()

        # Visit stats
        visits_this_month = await self.visit_repo.count_by_agent_month(agent.id)
        completed_visits = await self.visit_repo.count(
            filters={"agent_id": agent.id, "status": VisitStatus.COMPLETED}
        )

        # Commission stats from bookings
        commission_result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (Booking.agent_commission_status == "pending", Booking.agent_commission_amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("pending"),
                func.coalesce(
                    func.sum(
                        case(
                            (Booking.agent_commission_status == "paid", Booking.agent_commission_amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("paid"),
            ).where(Booking.agent_id == agent.id)
        )
        row = commission_result.one()
        pending_commissions = row.pending
        paid_commissions = row.paid

        return {
            "total_mandates": total_mandates,
            "active_mandates": active_mandates,
            "total_properties": total_properties,
            "visits_this_month": visits_this_month,
            "completed_visits": completed_visits,
            "total_deals": agent.completed_deals,
            "pending_commissions": pending_commissions,
            "paid_commissions": paid_commissions,
            "total_commissions": pending_commissions + paid_commissions,
            "rating": agent.rating,
            "currency": "XOF",
        }

    # --- Commission ---
    async def get_commissions(
        self,
        agent: AgentProfile,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Get agent's commission history from bookings."""
        query = (
            select(Booking)
            .options(
                selectinload(Booking.booked_property),
                selectinload(Booking.tenant),
            )
            .where(
                and_(
                    Booking.agent_id == agent.id,
                    Booking.agent_commission_amount.isnot(None),
                )
            )
        )

        if status:
            query = query.where(Booking.agent_commission_status == status)

        query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        bookings = list(result.scalars().all())

        commissions = []
        for b in bookings:
            commissions.append({
                "booking_id": b.id,
                "booking_reference": b.reference,
                "property_title": b.booked_property.title if b.booked_property else "N/A",
                "tenant_name": b.tenant.full_name if b.tenant else "N/A",
                "commission_rate": b.agent_commission_rate or Decimal("0"),
                "commission_amount": b.agent_commission_amount or Decimal("0"),
                "status": b.agent_commission_status or "pending",
                "created_at": b.created_at,
                "paid_at": b.agent_commission_paid_at,
            })

        return commissions

    async def get_commission_summary(self, agent: AgentProfile) -> dict:
        """Get commission summary."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(Booking.agent_commission_amount), Decimal("0")).label("total"),
                func.coalesce(
                    func.sum(case(
                        (Booking.agent_commission_status == "pending", Booking.agent_commission_amount),
                        else_=Decimal("0"),
                    )),
                    Decimal("0"),
                ).label("pending"),
                func.coalesce(
                    func.sum(case(
                        (Booking.agent_commission_status == "paid", Booking.agent_commission_amount),
                        else_=Decimal("0"),
                    )),
                    Decimal("0"),
                ).label("paid"),
                func.coalesce(
                    func.sum(case(
                        (Booking.agent_commission_status == "disputed", Booking.agent_commission_amount),
                        else_=Decimal("0"),
                    )),
                    Decimal("0"),
                ).label("disputed"),
                func.count(Booking.id).label("deals_count"),
            ).where(
                and_(
                    Booking.agent_id == agent.id,
                    Booking.agent_commission_amount.isnot(None),
                )
            )
        )
        row = result.one()
        return {
            "total_earned": row.total,
            "pending": row.pending,
            "paid": row.paid,
            "disputed": row.disputed,
            "deals_count": row.deals_count,
            "currency": "XOF",
        }

    # --- Share Link ---
    async def generate_share_link(
        self, agent: AgentProfile, property_id: UUID, base_url: str = "https://fifaloge.com"
    ) -> dict:
        """Generate a share link for WhatsApp."""
        # Verify agent has mandate
        mandate = await self.mandate_repo.get_active_mandate(agent.id, property_id)
        if not mandate:
            raise BusinessLogicException(
                "Vous n'avez pas de mandat actif pour cette propriete"
            )

        share_url = f"{base_url}/p/{property_id}?agent={agent.agent_code}"
        whatsapp_text = f"Decouvrez cette propriete sur FIFALOGE: {share_url}"
        whatsapp_url = f"https://wa.me/?text={whatsapp_text}"

        return {
            "property_id": property_id,
            "agent_code": agent.agent_code,
            "share_url": share_url,
            "whatsapp_url": whatsapp_url,
        }

    # --- Track Referral ---
    async def track_referral(self, agent_code: str, booking: Booking) -> Booking:
        """Associate an agent with a booking via agent code."""
        agent = await self.profile_repo.get_by_code(agent_code)
        if not agent:
            return booking

        # Get commission rate from mandate or agent default
        mandate = await self.mandate_repo.get_active_mandate(
            agent.id, booking.property_id
        )
        commission_rate = (
            mandate.commission_rate
            if mandate and mandate.commission_rate
            else agent.commission_rate
        )

        # Calculate commission: rate% of one month's rent (base_price)
        commission_amount = (booking.base_price * commission_rate) / Decimal("100")

        booking.agent_id = agent.id
        booking.agent_commission_rate = commission_rate
        booking.agent_commission_amount = commission_amount
        booking.agent_commission_status = "pending"

        await self.session.flush()
        await self.session.refresh(booking)
        return booking
