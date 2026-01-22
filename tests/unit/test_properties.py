"""
Unit tests for property functionality.
"""
import pytest
from httpx import AsyncClient

from app.models.property import Property, PropertyStatus, PropertyType
from app.models.user import User


class TestPropertyEndpoints:
    """Tests for property endpoints."""

    @pytest.mark.asyncio
    async def test_search_properties_empty(self, client: AsyncClient):
        """Test searching properties when none exist."""
        response = await client.get("/api/v1/properties")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_property_as_landlord(
        self,
        client: AsyncClient,
        test_landlord: User,
        landlord_auth_headers: dict,
    ):
        """Test creating a property as a landlord."""
        property_data = {
            "title": "Beautiful Apartment in Cotonou",
            "description": "A beautiful 2-bedroom apartment in the heart of Cotonou.",
            "property_type": "apartment",
            "address": "123 Rue de la Paix",
            "city": "Cotonou",
            "price": 150000,
            "bedrooms": 2,
            "bathrooms": 1,
            "amenities": ["wifi", "parking"],
        }

        response = await client.post(
            "/api/v1/properties",
            json=property_data,
            headers=landlord_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == property_data["title"]
        assert data["city"] == property_data["city"]
        assert data["status"] == "pending"  # New properties need approval

    @pytest.mark.asyncio
    async def test_create_property_as_tenant_forbidden(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that tenants cannot create properties."""
        property_data = {
            "title": "My Property",
            "description": "A description that is long enough.",
            "property_type": "apartment",
            "address": "123 Street",
            "city": "Cotonou",
            "price": 100000,
        }

        response = await client.post(
            "/api/v1/properties",
            json=property_data,
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_property_unauthorized(self, client: AsyncClient):
        """Test creating a property without authentication."""
        property_data = {
            "title": "My Property",
            "description": "A description.",
            "property_type": "apartment",
            "address": "123 Street",
            "city": "Cotonou",
            "price": 100000,
        }

        response = await client.post("/api/v1/properties", json=property_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_featured_properties(self, client: AsyncClient):
        """Test getting featured properties."""
        response = await client.get("/api/v1/properties/featured")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_toggle_favorite(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_landlord: User,
        auth_headers: dict,
    ):
        """Test adding and removing property from favorites."""
        # First create a property as landlord
        property_obj = Property(
            owner_id=test_landlord.id,
            title="Test Property for Favorites",
            description="A test property for testing favorites functionality.",
            property_type=PropertyType.APARTMENT,
            address="456 Test Street",
            city="Cotonou",
            price=200000,
            status=PropertyStatus.ACTIVE,
        )
        db_session.add(property_obj)
        await db_session.commit()
        await db_session.refresh(property_obj)

        # Add to favorites
        response = await client.post(
            f"/api/v1/properties/{property_obj.id}/favorite",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "Ajouté aux favoris" in response.json()["message"]

        # Remove from favorites
        response = await client.post(
            f"/api/v1/properties/{property_obj.id}/favorite",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "Retiré des favoris" in response.json()["message"]
