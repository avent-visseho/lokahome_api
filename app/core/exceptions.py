"""
Custom exceptions for the LOKAHOME API.
"""

from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for API errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


# Authentication Exceptions
class InvalidCredentialsException(BaseAPIException):
    """Raised when credentials are invalid."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(BaseAPIException):
    """Raised when token has expired."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(BaseAPIException):
    """Raised when token is invalid."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientPermissionsException(BaseAPIException):
    """Raised when user lacks required permissions."""

    def __init__(self, detail: str = "Permissions insuffisantes"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# Resource Exceptions
class NotFoundException(BaseAPIException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Ressource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} non trouvé(e)",
        )


class AlreadyExistsException(BaseAPIException):
    """Raised when a resource already exists."""

    def __init__(self, resource: str = "Ressource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} existe déjà",
        )


# Validation Exceptions
class ValidationException(BaseAPIException):
    """Raised when validation fails."""

    def __init__(self, detail: str = "Erreur de validation"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


# Business Logic Exceptions
class BusinessLogicException(BaseAPIException):
    """Raised when business logic constraints are violated."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class PropertyNotAvailableException(BusinessLogicException):
    """Raised when property is not available for booking."""

    def __init__(self):
        super().__init__(detail="Ce bien n'est pas disponible pour cette période")


class BookingAlreadyExistsException(BusinessLogicException):
    """Raised when a booking already exists for the period."""

    def __init__(self):
        super().__init__(detail="Une réservation existe déjà pour cette période")


class PaymentFailedException(BusinessLogicException):
    """Raised when payment processing fails."""

    def __init__(self, detail: str = "Le paiement a échoué"):
        super().__init__(detail=detail)


# Rate Limiting
class RateLimitExceededException(BaseAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes. Veuillez réessayer plus tard.",
        )


# File Upload Exceptions
class FileTooLargeException(BaseAPIException):
    """Raised when uploaded file is too large."""

    def __init__(self, max_size_mb: int = 10):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Taille maximale: {max_size_mb}MB",
        )


class InvalidFileTypeException(BaseAPIException):
    """Raised when file type is not allowed."""

    def __init__(self, allowed_types: list[str] | None = None):
        types = ", ".join(allowed_types or ["image/jpeg", "image/png"])
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Type de fichier non autorisé. Types acceptés: {types}",
        )
