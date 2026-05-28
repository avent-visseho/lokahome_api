"""
Authentication endpoints for user login, registration, and token management.
"""
from typing import Annotated

import uuid as uuid_mod
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import HTMLResponse
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
from app.core.config import settings
from app.services.auth import AuthService
from app.services.user import UserService
from app.tasks.email import (
    get_password_reset_email,
    get_welcome_email,
    send_email_sync,
)

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
    background_tasks: BackgroundTasks,
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

    verification_token = auth_service.create_verification_token(user.email)
    verification_url = f"{settings.BASE_API_URL}/api/v1/auth/verify-email/{verification_token}"
    subject, html, text = get_welcome_email(user.first_name, verification_url)
    background_tasks.add_task(send_email_sync, user.email, subject, html, text)

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
    background_tasks: BackgroundTasks,
):
    """
    Envoyer un email de réinitialisation de mot de passe.

    Pour des raisons de sécurité, retourne toujours un succès
    même si l'email n'existe pas.
    """
    auth_service = AuthService(session)
    token = await auth_service.request_password_reset(data.email)

    if token:
        user_service = UserService(session)
        user = await user_service.get_user_by_email(data.email)
        user_name = user.first_name if user else data.email
        reset_url = f"{settings.FRONTEND_URL}/password-reset?token={token}"
        subject, html, text = get_password_reset_email(user_name, reset_url)
        background_tasks.add_task(send_email_sync, data.email, subject, html, text)

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


@router.get(
    "/verify-email/{token}",
    response_class=HTMLResponse,
    summary="Vérifier l'adresse email (lien depuis l'email)",
)
async def verify_email_get(
    token: str,
    session: DbSession,
):
    """
    Vérifier l'adresse email quand l'utilisateur clique le lien dans l'email.
    Retourne une page HTML de confirmation.
    """
    try:
        auth_service = AuthService(session)
        await auth_service.verify_email_token(token)
        return HTMLResponse(content=_verification_page(
            success=True,
            title="Email vérifié !",
            message="Votre adresse email a été vérifiée avec succès. Vous pouvez maintenant vous connecter dans l'application.",
        ))
    except Exception:
        return HTMLResponse(content=_verification_page(
            success=False,
            title="Lien invalide",
            message="Ce lien de vérification est invalide ou a expiré. Veuillez demander un nouveau lien depuis l'application.",
        ), status_code=400)


@router.post(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Vérifier l'adresse email (API)",
)
async def verify_email_post(
    token: str,
    session: DbSession,
):
    """
    Vérifier l'adresse email via API (usage programmatique).
    """
    auth_service = AuthService(session)
    await auth_service.verify_email_token(token)

    return MessageResponse(message="Email vérifié avec succès")


def _verification_page(success: bool, title: str, message: str) -> str:
    """Generate HTML verification result page."""
    color = "#16a34a" if success else "#dc2626"
    icon = "&#10004;" if success else "&#10008;"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - {settings.APP_NAME}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f0f4f8; display: flex; align-items: center; justify-content: center;
               min-height: 100vh; padding: 20px; }}
        .card {{ background: white; border-radius: 16px; padding: 48px 32px; max-width: 420px;
                 width: 100%; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
        .icon {{ width: 80px; height: 80px; border-radius: 50%; background: {color};
                 color: white; font-size: 40px; display: flex; align-items: center;
                 justify-content: center; margin: 0 auto 24px; }}
        h1 {{ color: #1e293b; font-size: 24px; margin-bottom: 12px; }}
        p {{ color: #64748b; font-size: 16px; line-height: 1.6; }}
        .app-name {{ color: #2563eb; font-weight: 600; margin-top: 32px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <p class="app-name">{settings.APP_NAME}</p>
    </div>
</body>
</html>"""


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Renvoyer l'email de vérification",
)
async def resend_verification_email(
    current_user: ActiveUser,
    session: DbSession,
    background_tasks: BackgroundTasks,
):
    """
    Renvoyer un email de vérification à l'utilisateur connecté.

    Génère un nouveau token de vérification et l'envoie par email.
    Pour des raisons de sécurité, retourne toujours un succès.
    """
    if current_user.email_verified_at is not None:
        return MessageResponse(message="Email déjà vérifié")

    auth_service = AuthService(session)
    token = auth_service.create_verification_token(current_user.email)
    verification_url = f"{settings.BASE_API_URL}/api/v1/auth/verify-email/{token}"
    subject, html, text = get_welcome_email(current_user.first_name, verification_url)
    background_tasks.add_task(send_email_sync, current_user.email, subject, html, text)

    return MessageResponse(message="Email de vérification envoyé")


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
    session: DbSession,
):
    """
    Déconnecter l'utilisateur.

    Note: Les tokens JWT sont stateless. Cette route est principalement
    pour la conformité et peut être utilisée pour invalider les tokens
    côté client ou dans un système de blacklist Redis.
    """
    # Clear FCM token so this device stops receiving push notifications
    user_service = UserService(session)
    await user_service.clear_fcm_token(current_user)

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


AVATAR_UPLOAD_DIR = Path(__file__).parent.parent.parent.parent.parent / "static" / "images" / "avatars"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/avatar",
    response_model=UserResponse,
    summary="Uploader un avatar",
)
async def upload_avatar(
    current_user: ActiveUser,
    session: DbSession,
    file: UploadFile = File(...),
):
    """
    Uploader ou remplacer l'avatar de l'utilisateur.

    - Formats acceptés : JPEG, PNG, WebP
    - Taille max : 5 Mo
    """
    from fastapi import HTTPException

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=400,
            detail="L'image ne doit pas dépasser 5 Mo.",
        )

    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Delete old avatar file if exists
    if current_user.avatar_url and current_user.avatar_url.startswith("/static/images/avatars/"):
        old_path = Path(__file__).parent.parent.parent.parent.parent / current_user.avatar_url.lstrip("/")
        if old_path.exists():
            old_path.unlink()

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    filename = f"{uuid_mod.uuid4().hex}{ext}"
    file_path = AVATAR_UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    avatar_url = f"/static/images/avatars/{filename}"
    user_service = UserService(session)
    updated = await user_service.update_avatar(current_user, avatar_url)
    return updated
