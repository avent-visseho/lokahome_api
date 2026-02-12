"""
Property endpoints for listing management.
"""
import uuid as uuid_mod
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import ActiveUser, DbSession, RequireAdmin, RequireLandlord
from app.models.property import PropertyStatus, PropertyType
from app.schemas.base import MessageResponse, PaginatedResponse
from app.schemas.property import (
    NearbyPropertiesRequest,
    PropertyCreate,
    PropertyDetailResponse,
    PropertyImageResponse,
    PropertyListResponse,
    PropertyResponse,
    PropertySearchParams,
    PropertyUpdate,
)
from app.services.property import PropertyService

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent.parent / "static" / "images" / "properties"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get(
    "",
    response_model=PaginatedResponse[PropertyListResponse],
    summary="Rechercher des propriétés",
)
async def search_properties(
    session: DbSession,
    query: str | None = None,
    city: str | None = None,
    neighborhood: str | None = None,
    property_type: PropertyType | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_bedrooms: int | None = None,
    max_bedrooms: int | None = None,
    pets_allowed: bool | None = None,
    is_available: bool = True,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    Rechercher des propriétés avec filtres.

    - **query**: Recherche textuelle (titre, description, adresse)
    - **city**: Filtrer par ville
    - **property_type**: Type de bien (apartment, house, studio, etc.)
    - **min_price / max_price**: Fourchette de prix
    - **min_bedrooms / max_bedrooms**: Nombre de chambres
    - **pets_allowed**: Animaux autorisés
    """
    property_service = PropertyService(session)

    params = PropertySearchParams(
        query=query,
        city=city,
        neighborhood=neighborhood,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        pets_allowed=pets_allowed,
        is_available=is_available,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    properties, total = await property_service.search_properties(params)

    return PaginatedResponse(
        items=properties,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/featured",
    response_model=list[PropertyListResponse],
    summary="Obtenir les propriétés en vedette",
)
async def get_featured_properties(
    session: DbSession,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Récupérer les propriétés mises en avant."""
    property_service = PropertyService(session)
    return await property_service.get_featured_properties(limit=limit)


@router.post(
    "/nearby",
    response_model=list[PropertyListResponse],
    summary="Rechercher des propriétés à proximité",
)
async def get_nearby_properties(
    data: NearbyPropertiesRequest,
    session: DbSession,
):
    """
    Trouver des propriétés dans un rayon autour d'une position.

    - **latitude / longitude**: Position centrale
    - **radius_km**: Rayon de recherche en km (max 50)
    """
    property_service = PropertyService(session)
    return await property_service.get_nearby_properties(
        latitude=data.latitude,
        longitude=data.longitude,
        radius_km=data.radius_km,
        limit=data.limit,
    )


@router.get(
    "/my-listings",
    response_model=list[PropertyResponse],
    summary="Mes annonces",
    dependencies=[RequireLandlord],
)
async def get_my_properties(
    current_user: ActiveUser,
    session: DbSession,
    status: PropertyStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer mes propres annonces immobilières."""
    property_service = PropertyService(session)
    return await property_service.get_user_properties(
        owner_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{property_id}",
    response_model=PropertyDetailResponse,
    summary="Détails d'une propriété",
)
async def get_property(
    property_id: UUID,
    session: DbSession,
):
    """Récupérer les détails complets d'une propriété."""
    property_service = PropertyService(session)
    property_obj = await property_service.get_property(property_id)

    # Increment view count (async, fire and forget)
    await property_service.increment_views(property_id)

    return property_obj


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une annonce",
    dependencies=[RequireLandlord],
)
async def create_property(
    data: PropertyCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer une nouvelle annonce immobilière.

    Requiert le rôle **landlord** ou **admin**.
    L'annonce sera en statut "pending" jusqu'à validation par un admin.
    """
    property_service = PropertyService(session)
    return await property_service.create_property(current_user, data)


@router.patch(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Modifier une annonce",
)
async def update_property(
    property_id: UUID,
    data: PropertyUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Modifier une annonce existante.

    Seul le propriétaire ou un admin peut modifier l'annonce.
    """
    property_service = PropertyService(session)
    return await property_service.update_property(property_id, current_user, data)


@router.delete(
    "/{property_id}",
    response_model=MessageResponse,
    summary="Supprimer une annonce",
)
async def delete_property(
    property_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Supprimer une annonce.

    Seul le propriétaire ou un admin peut supprimer l'annonce.
    """
    property_service = PropertyService(session)
    await property_service.delete_property(property_id, current_user)
    return MessageResponse(message="Annonce supprimée avec succès")


# Favorites
@router.post(
    "/{property_id}/favorite",
    response_model=MessageResponse,
    summary="Ajouter/Retirer des favoris",
)
async def toggle_favorite(
    property_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Ajouter ou retirer une propriété des favoris."""
    property_service = PropertyService(session)
    added = await property_service.toggle_favorite(current_user.id, property_id)

    message = "Ajouté aux favoris" if added else "Retiré des favoris"
    return MessageResponse(message=message)


@router.get(
    "/favorites/list",
    response_model=list[PropertyListResponse],
    summary="Mes favoris",
)
async def get_favorites(
    current_user: ActiveUser,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer mes propriétés favorites."""
    property_service = PropertyService(session)
    return await property_service.get_user_favorites(
        current_user.id, skip=skip, limit=limit
    )


# Admin endpoints
@router.post(
    "/{property_id}/approve",
    response_model=PropertyResponse,
    summary="Approuver une annonce (Admin)",
    dependencies=[RequireAdmin],
)
async def approve_property(
    property_id: UUID,
    session: DbSession,
):
    """Approuver et activer une annonce."""
    property_service = PropertyService(session)
    return await property_service.approve_property(property_id)


@router.post(
    "/{property_id}/reject",
    response_model=PropertyResponse,
    summary="Rejeter une annonce (Admin)",
    dependencies=[RequireAdmin],
)
async def reject_property(
    property_id: UUID,
    session: DbSession,
    reason: str | None = None,
):
    """Rejeter une annonce."""
    property_service = PropertyService(session)
    return await property_service.reject_property(property_id, reason)


@router.post(
    "/{property_id}/feature",
    response_model=PropertyResponse,
    summary="Mettre en vedette (Admin)",
    dependencies=[RequireAdmin],
)
async def feature_property(
    property_id: UUID,
    session: DbSession,
    featured: bool = True,
):
    """Mettre une annonce en vedette."""
    property_service = PropertyService(session)
    return await property_service.feature_property(property_id, featured)


# Image upload
@router.post(
    "/{property_id}/images",
    response_model=PropertyImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Uploader une image de propriété",
)
async def upload_property_image(
    property_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    caption: str | None = Form(None),
):
    """
    Uploader une image pour une propriété.

    - Formats acceptés : JPEG, PNG, WebP
    - Taille max : 10 Mo
    - La première image est automatiquement définie comme principale
    """
    from fastapi import HTTPException

    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.",
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="L'image ne doit pas dépasser 10 Mo.",
        )

    # Save to static directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    filename = f"{uuid_mod.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    # Create database record
    url = f"/static/images/properties/{filename}"
    property_service = PropertyService(session)
    image = await property_service.add_image(
        property_id=property_id,
        user=current_user,
        url=url,
        is_primary=is_primary,
        caption=caption,
    )

    return image


@router.delete(
    "/{property_id}/images/{image_id}",
    response_model=MessageResponse,
    summary="Supprimer une image de propriété",
)
async def delete_property_image(
    property_id: UUID,
    image_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Supprimer une image d'une propriété."""
    property_service = PropertyService(session)
    await property_service.delete_image(image_id, current_user)
    return MessageResponse(message="Image supprimée avec succès")
