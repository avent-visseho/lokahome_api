"""
Authentication endpoints for user login, registration, and token management.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import ActiveUser, DbSession
from app.schemas.base import MessageResponse
from app.schemas.user import (
    ChangePassword,
    FcmTokenUpdate,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau compte",
)
async def register(
    data: UserRegister,
    session: DbSession,
):
    """
    Créer un nouveau compte utilisateur.

    - **email**: Adresse email unique
    - **password**: Mot de passe (min. 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre)
    - **first_name**: Prénom
    - **last_name**: Nom de famille
    - **phone**: Numéro de téléphone (optionnel)
    - **role**: Rôle (tenant, landlord, provider)
    """
    auth_service = AuthService(session)
    user = await auth_service.register(data)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion utilisateur",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DbSession,
):
    """
    Authentifier un utilisateur et obtenir des tokens JWT.

    Utilise le format OAuth2 avec username (email) et password.
    """
    auth_service = AuthService(session)
    user = await auth_service.authenticate(form_data.username, form_data.password)
    return auth_service.create_tokens(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rafraîchir le token d'accès",
)
async def refresh_token(
    data: RefreshTokenRequest,
    session: DbSession,
):
    """
    Obtenir un nouveau token d'accès avec le refresh token.
    """
    auth_service = AuthService(session)
    return await auth_service.refresh_access_token(data.refresh_token)


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    summary="Demander une réinitialisation de mot de passe",
)
async def request_password_reset(
    data: PasswordResetRequest,
    session: DbSession,
):
    """
    Envoyer un email de réinitialisation de mot de passe.

    Pour des raisons de sécurité, retourne toujours un succès
    même si l'email n'existe pas.
    """
    auth_service = AuthService(session)
    await auth_service.request_password_reset(data.email)

    # TODO: Send email with token
    # In production, send email asynchronously via Celery

    return MessageResponse(
        message="Si cet email existe, un lien de réinitialisation a été envoyé"
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirmer la réinitialisation de mot de passe",
)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    session: DbSession,
):
    """
    Réinitialiser le mot de passe avec le token reçu par email.
    """
    auth_service = AuthService(session)
    await auth_service.reset_password(data.token, data.new_password)

    return MessageResponse(message="Mot de passe réinitialisé avec succès")


@router.post(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Vérifier l'adresse email",
)
async def verify_email(
    token: str,
    session: DbSession,
):
    """
    Vérifier l'adresse email avec le token reçu.
    """
    auth_service = AuthService(session)
    await auth_service.verify_email_token(token)

    return MessageResponse(message="Email vérifié avec succès")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtenir le profil de l'utilisateur connecté",
)
async def get_current_user_profile(
    current_user: ActiveUser,
):
    """
    Récupérer les informations de l'utilisateur actuellement connecté.
    """
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Déconnexion",
)
async def logout(
    current_user: ActiveUser,
):
    """
    Déconnecter l'utilisateur.

    Note: Les tokens JWT sont stateless. Cette route est principalement
    pour la conformité et peut être utilisée pour invalider les tokens
    côté client ou dans un système de blacklist Redis.
    """
    # TODO: Add token to Redis blacklist if needed
    return MessageResponse(message="Déconnexion réussie")


@router.post(
    "/fcm-token",
    response_model=MessageResponse,
    summary="Enregistrer le token FCM",
)
async def update_fcm_token(
    data: FcmTokenUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Enregistrer ou mettre à jour le token FCM pour les notifications push.
    """
    user_service = UserService(session)
    await user_service.update_fcm_token(current_user, data.fcm_token)
    return MessageResponse(message="Token FCM mis à jour")


@router.patch(
    "/profile",
    response_model=UserResponse,
    summary="Mettre à jour le profil",
)
async def update_profile(
    data: UserUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Mettre à jour le profil de l'utilisateur connecté.

    - **first_name**: Prénom
    - **last_name**: Nom de famille
    - **phone**: Numéro de téléphone
    - **bio**: Biographie
    """
    user_service = UserService(session)
    updated = await user_service.update_profile(current_user, data)
    return updated


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Changer le mot de passe",
)
async def change_password(
    data: ChangePassword,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Changer le mot de passe de l'utilisateur connecté.

    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe (min. 8 caractères)
    """
    user_service = UserService(session)
    await user_service.change_password(current_user, data)
    return MessageResponse(message="Mot de passe modifié avec succès")
