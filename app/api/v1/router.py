"""
API v1 router aggregating all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    bookings,
    messages,
    payments,
    properties,
    reviews,
    services,
)

api_router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(services.router)
api_router.include_router(messages.router)
api_router.include_router(reviews.router)
api_router.include_router(admin.router)
