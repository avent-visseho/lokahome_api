"""
Agent/Demarcheur API endpoints.
"""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import ActiveUser, DbSession, RequireAgent, RequireLandlord
from app.core.exceptions import NotFoundException
from app.models.agent import MandateStatus, VisitStatus
from app.schemas.agent import (
    AgentCommissionResponse,
    AgentCommissionSummary,
    AgentDashboardResponse,
    AgentMandateCreate,
    AgentMandateListResponse,
    AgentMandateResponse,
    AgentProfileCreate,
    AgentProfileListResponse,
    AgentProfileResponse,
    AgentProfileUpdate,
    AgentShareLinkResponse,
    PropertyVisitCreate,
    PropertyVisitListResponse,
    PropertyVisitResponse,
    PropertyVisitUpdate,
)
from app.schemas.base import PaginatedResponse
from app.services.agent import AgentService

router = APIRouter(prefix="/agents", tags=["Agents/Demarcheurs"])


# --- Helper ---

async def _get_agent_or_404(service: AgentService, user_id: UUID):
    """Get agent profile for current user or raise 404."""
    agent = await service.get_agent_by_user(user_id)
    if not agent:
        raise NotFoundException("Profil agent")
    return agent


# --- Agent Profile ---


@router.post("/profile", response_model=AgentProfileResponse)
async def create_agent_profile(
    data: AgentProfileCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Create an agent/demarcheur profile."""
    service = AgentService(session)
    agent = await service.create_agent_profile(
        current_user, data.model_dump(exclude_unset=True)
    )
    await session.commit()
    return agent


@router.get("/profile/me", response_model=AgentProfileResponse)
async def get_my_agent_profile(
    current_user: ActiveUser,
    session: DbSession,
):
    """Get current user's agent profile."""
    service = AgentService(session)
    return await _get_agent_or_404(service, current_user.id)


@router.patch("/profile/{agent_id}", response_model=AgentProfileResponse)
async def update_agent_profile(
    agent_id: UUID,
    data: AgentProfileUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Update agent profile."""
    service = AgentService(session)
    agent = await service.update_agent_profile(
        agent_id, current_user, data.model_dump(exclude_unset=True)
    )
    await session.commit()
    return agent


@router.get("/search", response_model=PaginatedResponse[AgentProfileListResponse])
async def search_agents(
    session: DbSession,
    city: str | None = None,
    specialization: str | None = None,
    is_available: bool | None = True,
    is_verified: bool | None = None,
    min_rating: float | None = None,
    sort_by: str = "rating",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Search agents/demarcheurs."""
    service = AgentService(session)
    skip = (page - 1) * page_size
    agents, total = await service.search_agents(
        city=city,
        specialization=specialization,
        is_available=is_available,
        is_verified=is_verified,
        min_rating=Decimal(str(min_rating)) if min_rating else None,
        skip=skip,
        limit=page_size,
        sort_by=sort_by,
    )
    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=agents, total=total, page=page, page_size=page_size, pages=pages
    )


# --- Mandates ---


@router.post(
    "/mandates",
    response_model=AgentMandateResponse,
    dependencies=[RequireLandlord],
)
async def create_mandate(
    data: AgentMandateCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Create a mandate for an agent (landlord only)."""
    service = AgentService(session)
    mandate = await service.create_mandate(
        current_user, data.model_dump(exclude_unset=True)
    )
    await session.commit()
    return mandate


@router.get(
    "/mandates/my-mandates",
    response_model=list[AgentMandateListResponse],
    dependencies=[RequireAgent],
)
async def get_my_mandates(
    current_user: ActiveUser,
    session: DbSession,
    status: MandateStatus | None = None,
):
    """Get my mandates (as agent)."""
    service = AgentService(session)
    agent = await service.get_agent_by_user(current_user.id)
    if not agent:
        return []
    return await service.get_agent_mandates(agent.id, status=status)


@router.get(
    "/mandates/given",
    response_model=list[AgentMandateListResponse],
    dependencies=[RequireLandlord],
)
async def get_given_mandates(
    current_user: ActiveUser,
    session: DbSession,
    status: MandateStatus | None = None,
):
    """Get mandates I gave to agents (as landlord)."""
    service = AgentService(session)
    return await service.get_landlord_mandates(current_user.id, status=status)


@router.post("/mandates/{mandate_id}/accept", response_model=AgentMandateResponse)
async def accept_mandate(
    mandate_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Accept a mandate (as agent)."""
    service = AgentService(session)
    mandate = await service.accept_mandate(mandate_id, current_user)
    await session.commit()
    return mandate


@router.post("/mandates/{mandate_id}/revoke", response_model=AgentMandateResponse)
async def revoke_mandate(
    mandate_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Revoke a mandate (as landlord or admin)."""
    service = AgentService(session)
    mandate = await service.revoke_mandate(mandate_id, current_user)
    await session.commit()
    return mandate


@router.get("/mandates/{mandate_id}", response_model=AgentMandateResponse)
async def get_mandate_detail(
    mandate_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Get mandate detail."""
    service = AgentService(session)
    return await service.get_mandate(mandate_id)


# --- Visits ---


@router.post(
    "/visits",
    response_model=PropertyVisitResponse,
    dependencies=[RequireAgent],
)
async def schedule_visit(
    data: PropertyVisitCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Schedule a property visit (agent only)."""
    service = AgentService(session)
    agent = await _get_agent_or_404(service, current_user.id)
    visit = await service.schedule_visit(agent, data.model_dump())
    await session.commit()
    return visit


@router.get(
    "/visits/my-visits",
    response_model=list[PropertyVisitListResponse],
    dependencies=[RequireAgent],
)
async def get_my_visits(
    current_user: ActiveUser,
    session: DbSession,
    status: VisitStatus | None = None,
):
    """Get my visits (as agent)."""
    service = AgentService(session)
    agent = await service.get_agent_by_user(current_user.id)
    if not agent:
        return []
    return await service.get_agent_visits(agent.id, status=status)


@router.post(
    "/visits/{visit_id}/complete",
    response_model=PropertyVisitResponse,
    dependencies=[RequireAgent],
)
async def complete_visit(
    visit_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    data: PropertyVisitUpdate | None = None,
):
    """Mark visit as completed."""
    service = AgentService(session)
    visit = await service.complete_visit(
        visit_id, current_user, data.model_dump(exclude_unset=True) if data else None
    )
    await session.commit()
    return visit


@router.post("/visits/{visit_id}/cancel", response_model=PropertyVisitResponse)
async def cancel_visit(
    visit_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Cancel a scheduled visit."""
    service = AgentService(session)
    visit = await service.cancel_visit(visit_id, current_user)
    await session.commit()
    return visit


@router.get("/visits/{visit_id}", response_model=PropertyVisitResponse)
async def get_visit_detail(
    visit_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Get visit detail."""
    service = AgentService(session)
    return await service.get_visit(visit_id)


# --- Dashboard & Commissions ---


@router.get(
    "/dashboard",
    response_model=AgentDashboardResponse,
    dependencies=[RequireAgent],
)
async def get_agent_dashboard(
    current_user: ActiveUser,
    session: DbSession,
):
    """Get agent dashboard data."""
    service = AgentService(session)
    agent = await _get_agent_or_404(service, current_user.id)
    return await service.get_dashboard(agent)


@router.get(
    "/commissions",
    response_model=list[AgentCommissionResponse],
    dependencies=[RequireAgent],
)
async def get_commissions(
    current_user: ActiveUser,
    session: DbSession,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Get commission history."""
    service = AgentService(session)
    agent = await service.get_agent_by_user(current_user.id)
    if not agent:
        return []
    skip = (page - 1) * page_size
    return await service.get_commissions(agent, status=status, skip=skip, limit=page_size)


@router.get(
    "/commissions/summary",
    response_model=AgentCommissionSummary,
    dependencies=[RequireAgent],
)
async def get_commission_summary(
    current_user: ActiveUser,
    session: DbSession,
):
    """Get commission summary."""
    service = AgentService(session)
    agent = await _get_agent_or_404(service, current_user.id)
    return await service.get_commission_summary(agent)


# --- Share Link ---


@router.get(
    "/share/{property_id}",
    response_model=AgentShareLinkResponse,
    dependencies=[RequireAgent],
)
async def generate_share_link(
    property_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Generate a WhatsApp share link for a property."""
    service = AgentService(session)
    agent = await _get_agent_or_404(service, current_user.id)
    return await service.generate_share_link(agent, property_id)


# --- Agent Detail (MUST be last — catches /{agent_id}) ---


@router.get("/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_detail(
    agent_id: UUID,
    session: DbSession,
):
    """Get agent detail."""
    service = AgentService(session)
    return await service.get_agent(agent_id)
