"""
Seed data for development/demo.
Creates realistic properties, images, bookings, provider profiles and service requests.
"""
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.property import Property, PropertyImage, PropertyStatus, PropertyType, RentalPeriod
from app.models.service import (
    ServiceCategory,
    ServiceProvider,
    ServiceRequest,
    ServiceRequestStatus,
)
from app.models.user import User


# Base path for locally stored property images
IMG_BASE = "/static/images/properties"

# --- Property seed data ---

SEED_PROPERTIES = [
    {
        "title": "Villa Cocotier",
        "description": "Magnifique villa avec jardin tropical dans le quartier résidentiel de Haie Vive. "
        "Espaces de vie généreux, cuisine équipée, terrasse couverte et parking privé. "
        "Idéal pour une famille, proche des commodités et des écoles internationales.",
        "property_type": PropertyType.VILLA,
        "address": "Lot 234, Rue des Cocotiers, Haie Vive",
        "city": "Cotonou",
        "neighborhood": "Haie Vive",
        "price": Decimal("350000"),
        "deposit": Decimal("700000"),
        "agency_fees": Decimal("350000"),
        "bedrooms": 4,
        "bathrooms": 3,
        "surface_area": 200,
        "floor": 0,
        "total_floors": 2,
        "year_built": 2019,
        "amenities": ["wifi", "parking", "garden", "security", "air_conditioning", "furnished"],
        "pets_allowed": True,
        "max_occupants": 8,
        "latitude": Decimal("6.3670"),
        "longitude": Decimal("2.3910"),
        "is_featured": True,
        "images": [
            {"url": f"{IMG_BASE}/villa_cocotier_1.jpg", "caption": "Façade principale"},
            {"url": f"{IMG_BASE}/villa_cocotier_2.jpg", "caption": "Salon spacieux"},
            {"url": f"{IMG_BASE}/villa_cocotier_3.jpg", "caption": "Jardin tropical"},
        ],
    },
    {
        "title": "Appartement Moderne Akpakpa",
        "description": "Bel appartement moderne de 2 chambres à Akpakpa. "
        "Récemment rénové avec finitions haut de gamme, cuisine américaine et balcon. "
        "Quartier calme et sécurisé, à proximité des transports.",
        "property_type": PropertyType.APARTMENT,
        "address": "Immeuble Les Palmiers, Akpakpa",
        "city": "Cotonou",
        "neighborhood": "Akpakpa",
        "price": Decimal("120000"),
        "deposit": Decimal("240000"),
        "agency_fees": Decimal("120000"),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface_area": 75,
        "floor": 3,
        "total_floors": 5,
        "year_built": 2021,
        "amenities": ["wifi", "parking", "security", "air_conditioning", "balcony"],
        "pets_allowed": False,
        "max_occupants": 4,
        "latitude": Decimal("6.3580"),
        "longitude": Decimal("2.4250"),
        "is_featured": True,
        "images": [
            {"url": f"{IMG_BASE}/appartement_moderne_1.jpg", "caption": "Salon lumineux"},
            {"url": f"{IMG_BASE}/appartement_moderne_2.jpg", "caption": "Cuisine moderne"},
        ],
    },
    {
        "title": "Studio Meublé Centre Ganhi",
        "description": "Studio entièrement meublé et équipé en plein centre-ville de Ganhi. "
        "Parfait pour un jeune professionnel ou étudiant. Accès facile à tout Cotonou.",
        "property_type": PropertyType.STUDIO,
        "address": "Avenue Steinmetz, Ganhi",
        "city": "Cotonou",
        "neighborhood": "Ganhi",
        "price": Decimal("65000"),
        "deposit": Decimal("130000"),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface_area": 35,
        "floor": 2,
        "total_floors": 4,
        "year_built": 2018,
        "amenities": ["wifi", "furnished", "air_conditioning"],
        "pets_allowed": False,
        "max_occupants": 2,
        "latitude": Decimal("6.3640"),
        "longitude": Decimal("2.4320"),
        "is_featured": True,
        "images": [
            {"url": f"{IMG_BASE}/studio_meuble_1.jpg", "caption": "Vue d'ensemble"},
            {"url": f"{IMG_BASE}/studio_meuble_2.jpg", "caption": "Espace cuisine"},
        ],
    },
    {
        "title": "Maison Familiale Calavi",
        "description": "Grande maison familiale à Abomey-Calavi avec 3 chambres, séjour double et cour clôturée. "
        "Quartier résidentiel paisible, idéal pour famille avec enfants. Proche université.",
        "property_type": PropertyType.HOUSE,
        "address": "Quartier Tokpa, Abomey-Calavi",
        "city": "Abomey-Calavi",
        "neighborhood": "Tokpa",
        "price": Decimal("180000"),
        "deposit": Decimal("360000"),
        "agency_fees": Decimal("180000"),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface_area": 120,
        "floor": 0,
        "total_floors": 1,
        "year_built": 2016,
        "amenities": ["parking", "garden", "security"],
        "pets_allowed": True,
        "max_occupants": 6,
        "latitude": Decimal("6.4530"),
        "longitude": Decimal("2.3480"),
        "is_featured": False,
        "images": [
            {"url": f"{IMG_BASE}/maison_familiale_1.jpg", "caption": "Vue extérieure"},
            {"url": f"{IMG_BASE}/maison_familiale_2.jpg", "caption": "Cour intérieure"},
            {"url": f"{IMG_BASE}/maison_familiale_3.jpg", "caption": "Chambre parentale"},
        ],
    },
    {
        "title": "Duplex Standing Porto-Novo",
        "description": "Superbe duplex dans un quartier résidentiel de Porto-Novo. "
        "Architecture moderne, double séjour, 3 chambres avec placards intégrés. "
        "Terrasse panoramique au dernier étage.",
        "property_type": PropertyType.DUPLEX,
        "address": "Boulevard Lagunaire, Porto-Novo",
        "city": "Porto-Novo",
        "neighborhood": "Ouando",
        "price": Decimal("250000"),
        "deposit": Decimal("500000"),
        "agency_fees": Decimal("250000"),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface_area": 150,
        "floor": 0,
        "total_floors": 2,
        "year_built": 2020,
        "amenities": ["wifi", "parking", "security", "air_conditioning", "balcony", "garage"],
        "pets_allowed": False,
        "max_occupants": 6,
        "latitude": Decimal("6.4970"),
        "longitude": Decimal("2.6040"),
        "is_featured": False,
        "images": [
            {"url": f"{IMG_BASE}/duplex_standing_1.jpg", "caption": "Façade moderne"},
            {"url": f"{IMG_BASE}/duplex_standing_2.jpg", "caption": "Escalier intérieur"},
        ],
    },
    {
        "title": "Bureau Open Space Cadjehoun",
        "description": "Espace de bureau moderne en open space dans le quartier d'affaires de Cadjehoun. "
        "Idéal pour startup ou PME. Climatisation centrale, fibre optique et parking visiteurs.",
        "property_type": PropertyType.OFFICE,
        "address": "Rue du Commerce, Cadjehoun",
        "city": "Cotonou",
        "neighborhood": "Cadjehoun",
        "price": Decimal("200000"),
        "deposit": Decimal("400000"),
        "agency_fees": Decimal("200000"),
        "bedrooms": 0,
        "bathrooms": 1,
        "surface_area": 80,
        "floor": 1,
        "total_floors": 3,
        "year_built": 2022,
        "amenities": ["wifi", "parking", "security", "air_conditioning"],
        "pets_allowed": False,
        "max_occupants": 15,
        "latitude": Decimal("6.3660"),
        "longitude": Decimal("2.4010"),
        "is_featured": False,
        "images": [
            {"url": f"{IMG_BASE}/bureau_openspace_1.jpg", "caption": "Espace de travail"},
            {"url": f"{IMG_BASE}/bureau_openspace_2.jpg", "caption": "Salle de réunion"},
        ],
    },
    {
        "title": "Chambre Étudiante Calavi",
        "description": "Chambre meublée pour étudiant à proximité de l'Université d'Abomey-Calavi. "
        "Lit, bureau, armoire inclus. Douche et toilettes individuelles. WiFi disponible.",
        "property_type": PropertyType.ROOM,
        "address": "Cité universitaire, Abomey-Calavi",
        "city": "Abomey-Calavi",
        "neighborhood": "Campus",
        "price": Decimal("25000"),
        "deposit": Decimal("25000"),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface_area": 15,
        "year_built": 2017,
        "amenities": ["wifi", "furnished"],
        "pets_allowed": False,
        "max_occupants": 1,
        "latitude": Decimal("6.4180"),
        "longitude": Decimal("2.3420"),
        "is_featured": False,
        "images": [
            {"url": f"{IMG_BASE}/chambre_etudiante_1.jpg", "caption": "Chambre meublée"},
            {"url": f"{IMG_BASE}/chambre_etudiante_2.jpg", "caption": "Bureau d'étude"},
        ],
    },
    {
        "title": "Villa Luxe Piscine Fidjrossè",
        "description": "Villa de luxe avec piscine privée à Fidjrossè, face à l'océan. "
        "5 chambres, 4 salles de bain, grand salon, salle à manger, cuisine professionnelle. "
        "Personnel de maison, gardien 24h/24. Le summum du confort à Cotonou.",
        "property_type": PropertyType.VILLA,
        "address": "Route de la Plage, Fidjrossè",
        "city": "Cotonou",
        "neighborhood": "Fidjrossè",
        "price": Decimal("500000"),
        "deposit": Decimal("1000000"),
        "agency_fees": Decimal("500000"),
        "bedrooms": 5,
        "bathrooms": 4,
        "surface_area": 350,
        "floor": 0,
        "total_floors": 2,
        "year_built": 2023,
        "amenities": [
            "wifi",
            "parking",
            "pool",
            "garden",
            "security",
            "air_conditioning",
            "furnished",
            "balcony",
            "garage",
            "laundry",
        ],
        "pets_allowed": True,
        "max_occupants": 12,
        "latitude": Decimal("6.3430"),
        "longitude": Decimal("2.3720"),
        "is_featured": False,
        "images": [
            {"url": f"{IMG_BASE}/villa_luxe_1.jpg", "caption": "Vue aérienne"},
            {"url": f"{IMG_BASE}/villa_luxe_2.jpg", "caption": "Piscine privée"},
            {"url": f"{IMG_BASE}/villa_luxe_3.jpg", "caption": "Suite parentale"},
        ],
    },
]


# --- Service requests seed data ---

SEED_SERVICE_REQUESTS = [
    {
        "category": ServiceCategory.PLUMBING,
        "title": "Fuite robinet cuisine",
        "description": "Le robinet de la cuisine fuit en permanence depuis 3 jours. "
        "L'eau coule même quand le robinet est fermé. Besoin d'un plombier rapidement.",
        "address": "123 Rue de la Paix, Akpakpa",
        "city": "Cotonou",
        "is_urgent": True,
        "budget_min": Decimal("15000"),
        "budget_max": Decimal("30000"),
        "reference": "SR-DEMO-001",
    },
    {
        "category": ServiceCategory.ELECTRICAL,
        "title": "Installation ventilateur plafond",
        "description": "Je souhaite installer 2 ventilateurs de plafond dans le salon et la chambre. "
        "Les ventilateurs sont déjà achetés, j'ai besoin d'un électricien pour le montage.",
        "address": "Quartier Tokpa, Abomey-Calavi",
        "city": "Abomey-Calavi",
        "is_urgent": False,
        "budget_min": Decimal("20000"),
        "budget_max": Decimal("50000"),
        "reference": "SR-DEMO-002",
    },
    {
        "category": ServiceCategory.CLEANING,
        "title": "Nettoyage post-déménagement",
        "description": "Nettoyage complet d'un appartement de 3 pièces après déménagement. "
        "Sols, murs, vitres, cuisine et salle de bain. Surface environ 75m².",
        "address": "Immeuble Horizon, Ganhi",
        "city": "Cotonou",
        "is_urgent": False,
        "budget_min": Decimal("10000"),
        "budget_max": Decimal("25000"),
        "reference": "SR-DEMO-003",
    },
]


async def seed_demo_data(session: AsyncSession) -> None:
    """
    Seed the database with demo data for development.
    Idempotent: skips if data already exists (checks first property title).
    """
    # Check if seed data already exists
    result = await session.execute(
        select(Property).where(Property.title == "Villa Cocotier")
    )
    if result.scalar_one_or_none():
        print("Seed data already exists, skipping.")
        return

    # Get landlord user
    result = await session.execute(
        select(User).where(User.email == "landlord@test.com")
    )
    landlord = result.scalar_one_or_none()
    if not landlord:
        print("Landlord user not found, skipping seed data.")
        return

    # Get tenant user
    result = await session.execute(
        select(User).where(User.email == "tenant@test.com")
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        print("Tenant user not found, skipping seed data.")
        return

    # Get provider user
    result = await session.execute(
        select(User).where(User.email == "provider@test.com")
    )
    provider_user = result.scalar_one_or_none()
    if not provider_user:
        print("Provider user not found, skipping seed data.")
        return

    print("Seeding demo data...")

    # --- Create properties ---
    created_properties = []
    for prop_data in SEED_PROPERTIES:
        images_data = prop_data.pop("images")
        is_featured = prop_data.pop("is_featured", False)

        prop = Property(
            owner_id=landlord.id,
            status=PropertyStatus.ACTIVE,
            rental_period=RentalPeriod.MONTHLY,
            currency="XOF",
            country="Bénin",
            is_available=True,
            is_verified=True,
            is_featured=is_featured,
            views_count=random.randint(15, 250),
            favorites_count=random.randint(2, 45),
            smoking_allowed=False,
            **prop_data,
        )
        session.add(prop)
        await session.flush()

        # Add images
        for idx, img_data in enumerate(images_data):
            image = PropertyImage(
                property_id=prop.id,
                url=img_data["url"],
                thumbnail_url=img_data["url"],
                caption=img_data.get("caption"),
                is_primary=(idx == 0),
                order=idx,
            )
            session.add(image)

        created_properties.append(prop)

    await session.flush()
    print(f"  Created {len(created_properties)} properties with images")

    # --- Create bookings ---
    today = date.today()
    booking_configs = [
        {
            "property_idx": 0,
            "status": BookingStatus.PENDING,
            "check_in": today + timedelta(days=15),
            "check_out": today + timedelta(days=45),
            "reference": "BK-DEMO-001",
            "tenant_notes": "Bonjour, je suis intéressé par cette villa pour 1 mois.",
        },
        {
            "property_idx": 1,
            "status": BookingStatus.APPROVED,
            "check_in": today + timedelta(days=7),
            "check_out": today + timedelta(days=37),
            "reference": "BK-DEMO-002",
            "tenant_notes": "Nous sommes un couple, arrivée prévue le matin.",
        },
        {
            "property_idx": 3,
            "status": BookingStatus.ACTIVE,
            "check_in": today - timedelta(days=10),
            "check_out": today + timedelta(days=20),
            "reference": "BK-DEMO-003",
            "tenant_notes": "Famille de 4 personnes, merci pour votre accueil.",
        },
        {
            "property_idx": 2,
            "status": BookingStatus.COMPLETED,
            "check_in": today - timedelta(days=60),
            "check_out": today - timedelta(days=30),
            "reference": "BK-DEMO-004",
        },
    ]

    for cfg in booking_configs:
        prop = created_properties[cfg["property_idx"]]
        duration = (cfg["check_out"] - cfg["check_in"]).days
        months = max(1, duration // 30)
        base_price = float(prop.price) * months
        service_fee = base_price * 0.05
        total = base_price + service_fee

        booking = Booking(
            property_id=prop.id,
            tenant_id=tenant.id,
            reference=cfg["reference"],
            check_in=cfg["check_in"],
            check_out=cfg["check_out"],
            status=cfg["status"],
            base_price=Decimal(str(base_price)),
            service_fee=Decimal(str(service_fee)),
            deposit_amount=prop.deposit,
            total_amount=Decimal(str(total)),
            currency="XOF",
            guests_count=2,
            tenant_notes=cfg.get("tenant_notes"),
        )
        session.add(booking)

    await session.flush()
    print(f"  Created {len(booking_configs)} bookings")

    # --- Create provider profile ---
    provider = ServiceProvider(
        user_id=provider_user.id,
        business_name="Sena Services Pro",
        description="Professionnel qualifié en plomberie et électricité avec plus de 5 ans d'expérience. "
        "Interventions rapides et travail soigné garanti. Devis gratuit.",
        categories=["plumbing", "electrical"],
        service_areas=["Cotonou", "Abomey-Calavi"],
        hourly_rate=Decimal("5000"),
        minimum_charge=Decimal("15000"),
        currency="XOF",
        is_available=True,
        is_verified=True,
        completed_jobs=23,
        rating=Decimal("4.50"),
        response_time_hours=2,
        portfolio_images=[
            "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?w=400&h=300&fit=crop",
        ],
    )
    session.add(provider)
    await session.flush()
    print("  Created provider profile: Sena Services Pro")

    # --- Create service requests ---
    for req_data in SEED_SERVICE_REQUESTS:
        request = ServiceRequest(
            requester_id=tenant.id,
            status=ServiceRequestStatus.PENDING,
            currency="XOF",
            **req_data,
        )
        session.add(request)

    await session.flush()
    print(f"  Created {len(SEED_SERVICE_REQUESTS)} service requests")

    await session.commit()
    print("Seed data created successfully!")


async def init_seed_data() -> None:
    """Initialize seed data. Called during application startup in debug mode."""
    from app.core.database import async_session_maker

    async with async_session_maker() as session:
        try:
            await seed_demo_data(session)
        except Exception as e:
            print(f"Error seeding demo data: {e}")
            await session.rollback()
