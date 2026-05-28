"""
Contract endpoints for digital rental agreement management.
"""
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.api.deps import ActiveUser, DbSession
from app.core.exceptions import NotFoundException
from app.models.contract import ContractStatus
from app.schemas.base import MessageResponse
from app.schemas.contract import (
    ContractDetailResponse,
    ContractListResponse,
    ContractResponse,
    ContractSignRequest,
    ContractVerifyCodeRequest,
)
from app.services.contract import ContractService

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get(
    "/my-contracts",
    response_model=list[ContractListResponse],
    summary="Mes contrats",
)
async def get_my_contracts(
    current_user: ActiveUser,
    session: DbSession,
    status: ContractStatus | None = None,
):
    """Récupérer tous mes contrats (bailleur ou locataire)."""
    service = ContractService(session)
    return await service.get_user_contracts(current_user, status=status)


@router.get(
    "/pending",
    response_model=list[ContractListResponse],
    summary="Contrats en attente de signature",
)
async def get_pending_contracts(
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les contrats en attente de ma signature."""
    service = ContractService(session)
    return await service.get_pending_contracts(current_user)


@router.get(
    "/booking/{booking_id}",
    response_model=ContractDetailResponse,
    summary="Contrat d'une réservation",
)
async def get_contract_by_booking(
    booking_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer le contrat associé à une réservation."""
    service = ContractService(session)
    return await service.get_contract_by_booking(booking_id, current_user)


@router.get(
    "/{contract_id}",
    response_model=ContractDetailResponse,
    summary="Détail d'un contrat",
)
async def get_contract(
    contract_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les détails d'un contrat."""
    service = ContractService(session)
    return await service.get_contract(contract_id, current_user)


@router.get(
    "/{contract_id}/download",
    summary="Télécharger le PDF brouillon",
)
async def download_draft(
    contract_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Télécharger le PDF du contrat (brouillon)."""
    service = ContractService(session)
    contract = await service.get_contract(contract_id, current_user)

    if not contract.draft_url:
        raise NotFoundException("PDF du contrat")

    # Convert URL path to file path
    file_path = contract.draft_url.lstrip("/")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"{contract.reference}_draft.pdf",
    )


@router.get(
    "/{contract_id}/download-signed",
    summary="Télécharger le PDF signé",
)
async def download_signed(
    contract_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Télécharger le PDF du contrat signé."""
    service = ContractService(session)
    contract = await service.get_contract(contract_id, current_user)

    if not contract.signed_url:
        raise NotFoundException("PDF signé du contrat")

    file_path = contract.signed_url.lstrip("/")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"{contract.reference}_signed.pdf",
    )


@router.post(
    "/{contract_id}/request-code",
    response_model=MessageResponse,
    summary="Demander un code OTP",
)
async def request_verification_code(
    contract_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    request: Request,
):
    """Demander un code de vérification par SMS ou email pour signer."""
    service = ContractService(session)
    ip = request.client.host if request.client else "unknown"
    result = await service.request_verification_code(contract_id, current_user, ip)
    return MessageResponse(message=result["message"])


@router.post(
    "/{contract_id}/verify-code",
    response_model=MessageResponse,
    summary="Vérifier le code OTP",
)
async def verify_code(
    contract_id: UUID,
    data: ContractVerifyCodeRequest,
    current_user: ActiveUser,
    session: DbSession,
):
    """Vérifier le code OTP reçu par SMS ou email."""
    service = ContractService(session)
    await service.verify_code(contract_id, current_user, data.code)
    return MessageResponse(message="Code vérifié avec succès")


@router.post(
    "/{contract_id}/sign",
    response_model=ContractResponse,
    summary="Signer le contrat",
)
async def sign_contract(
    contract_id: UUID,
    data: ContractSignRequest,
    current_user: ActiveUser,
    session: DbSession,
    request: Request,
):
    """
    Signer le contrat avec une signature numérique.

    Le bailleur signe en premier, puis le locataire.
    Les deux parties doivent avoir vérifié leur code OTP avant de signer.
    """
    service = ContractService(session)
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return await service.sign_contract(
        contract_id, current_user, data.signature_data, ip, user_agent
    )
