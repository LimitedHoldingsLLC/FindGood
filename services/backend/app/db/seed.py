"""Sample catalog. Fictional venues — not verified real-world information.

python -m app.db.seed
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.ids import new_id
from app.core.logging import configure_logging, get_logger
from app.db.models import (
    Deal,
    DealItem,
    DealPublication,
    DealSchedule,
    Source,
    Venue,
    VenueLocation,
    VenueProviderLink,
)
from app.db.models.enums import (
    DealOfferingKind,
    DealType,
    PublicationState,
    RecordStatus,
    SourceType,
    TrustLevel,
    VerificationType,
)
from app.db.models.verification import Verification
from app.db.session import SessionLocal
from app.domain.geo import address_hash
from app.domain.ratings.composite import ProviderRating, apply_to_venue
from app.domain.venues.slug import slugify

logger = get_logger("seed")

WEEKDAYS = [1, 2, 3, 4, 5]
WEEKEND = [6, 7]


class LocationSpec(TypedDict):
    address_line1: str
    city: str
    region: str
    postal_code: str
    neighborhood: str
    latitude: Decimal
    longitude: Decimal


class RatingSpec(TypedDict):
    provider: str
    rating: str
    review_count: int


class VenueSpec(TypedDict):
    name: str
    description: str
    website_url: str
    phone: str
    category: str
    cuisines: list[str]
    price_level: int
    drink_kinds: list[str]
    accepts_reservations: bool
    features: list[str]
    ratings: list[RatingSpec]
    location: LocationSpec


def seed() -> None:
    configure_logging("console", "INFO")
    db = SessionLocal()
    try:
        if db.scalar(select(Venue).limit(1)):
            updated = _backfill_discovery(db)
            created = _ensure_map_acceptance_venue(db)
            db.commit()
            logger.info(
                "seed_skipped",
                reason="venues_already_exist",
                discovery_backfilled=updated,
                map_acceptance_created=created,
            )
            return
        venues = _venues()
        db.add_all(venues)
        db.flush()
        deals, items, schedules, sources, publications, verifications = _catalog(venues)
        db.add_all(sources)
        db.add_all(deals)
        db.flush()
        db.add_all(schedules + items + publications + verifications)
        db.commit()
        logger.info("seed_completed", venues=len(venues), deals=len(deals))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _venue_specs() -> list[VenueSpec]:
    return [
        {
            "name": "Harbor & Rye",
            "description": "A fictional downtown gastropub with rye whiskey and a harbor-view bar.",
            "website_url": "https://harborandrye.example",
            "phone": "213-555-0142",
            "category": "gastropub",
            "cuisines": ["american", "gastropub"],
            "price_level": 2,
            "drink_kinds": ["cocktails", "beer", "wine"],
            "accepts_reservations": True,
            "features": ["good_for_groups", "walk_in"],
            "ratings": [
                {"provider": "google_places", "rating": "4.4", "review_count": 890},
                {"provider": "yelp", "rating": "4.0", "review_count": 412},
                {"provider": "tripadvisor", "rating": "4.3", "review_count": 620},
            ],
            "location": {
                "address_line1": "412 S Spring St",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90013",
                "neighborhood": "Downtown",
                "latitude": Decimal("34.048100"),
                "longitude": Decimal("-118.249800"),
            },
        },
        {
            "name": "Casa Nube",
            "description": "A fictional Silver Lake kitchen known for tacos and citrus-forward margaritas.",
            "website_url": "https://casanube.example",
            "phone": "323-555-0177",
            "category": "mexican",
            "cuisines": ["mexican"],
            "price_level": 1,
            "drink_kinds": ["cocktails", "beer"],
            "accepts_reservations": False,
            "features": ["patio", "walk_in"],
            "ratings": [
                {"provider": "google_places", "rating": "4.6", "review_count": 210},
                {"provider": "yelp", "rating": "4.5", "review_count": 156},
                {"provider": "tripadvisor", "rating": "4.8", "review_count": 88},
            ],
            "location": {
                "address_line1": "2814 Sunset Blvd",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90026",
                "neighborhood": "Silver Lake",
                "latitude": Decimal("34.086400"),
                "longitude": Decimal("-118.268900"),
            },
        },
        {
            "name": "The Pearl Counter",
            "description": "A fictional Santa Monica oyster bar with a short prix-fixe at dusk.",
            "website_url": "https://pearlcounter.example",
            "phone": "310-555-0118",
            "category": "seafood",
            "cuisines": ["seafood"],
            "price_level": 3,
            "drink_kinds": ["wine", "cocktails"],
            "accepts_reservations": True,
            "features": ["good_for_groups"],
            "ratings": [
                {"provider": "google_places", "rating": "4.7", "review_count": 640},
                {"provider": "yelp", "rating": "4.3", "review_count": 280},
                {"provider": "tripadvisor", "rating": "4.5", "review_count": 410},
            ],
            "location": {
                "address_line1": "1624 Ocean Ave",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90401",
                "neighborhood": "Santa Monica",
                "latitude": Decimal("34.012200"),
                "longitude": Decimal("-118.495500"),
            },
        },
        {
            "name": "Sunday Provisions",
            "description": "A fictional Los Feliz cafe built around weekend brunch plates.",
            "website_url": "https://sundayprovisions.example",
            "phone": "323-555-0104",
            "category": "cafe",
            "cuisines": ["cafe", "american"],
            "price_level": 2,
            "drink_kinds": ["nonalcoholic", "wine"],
            "accepts_reservations": False,
            "features": ["patio", "walk_in"],
            "ratings": [
                {"provider": "google_places", "rating": "4.2", "review_count": 180},
                {"provider": "yelp", "rating": "4.0", "review_count": 95},
                {"provider": "tripadvisor", "rating": "3.9", "review_count": 72},
            ],
            "location": {
                "address_line1": "1862 Hillhurst Ave",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90027",
                "neighborhood": "Los Feliz",
                "latitude": Decimal("34.108900"),
                "longitude": Decimal("-118.287400"),
            },
        },
        {
            "name": "Nightbird Room",
            "description": "A fictional Echo Park bar that stays late and used to run a limited cocktail flight.",
            "website_url": "https://nightbirdroom.example",
            "phone": "323-555-0190",
            "category": "bar",
            "cuisines": ["bar", "american"],
            "price_level": 2,
            "drink_kinds": ["cocktails", "beer", "wine"],
            "accepts_reservations": False,
            "features": ["late_night", "walk_in"],
            "ratings": [
                {"provider": "google_places", "rating": "3.9", "review_count": 320},
                {"provider": "yelp", "rating": "3.8", "review_count": 210},
                {"provider": "tripadvisor", "rating": "3.6", "review_count": 145},
            ],
            "location": {
                "address_line1": "1518 Echo Park Ave",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90026",
                "neighborhood": "Echo Park",
                "latitude": Decimal("34.078800"),
                "longitude": Decimal("-118.256900"),
            },
        },
        {
            "name": "The Lantern Annex",
            "description": "A FindGood-only fictional Hollywood wine room. Not listed on Google or Yelp.",
            "website_url": "https://lanternannex.example",
            "phone": "323-555-0166",
            "category": "wine_bar",
            "cuisines": ["bar", "mediterranean"],
            "price_level": 2,
            "drink_kinds": ["wine", "natural_wine"],
            "accepts_reservations": False,
            "features": ["walk_in"],
            "ratings": [],
            "location": {
                "address_line1": "123 Example Street",
                "city": "Los Angeles",
                "region": "CA",
                "postal_code": "90028",
                "neighborhood": "Hollywood",
                "latitude": Decimal("34.101600"),
                "longitude": Decimal("-118.326800"),
            },
        },
    ]


def _venues() -> list[Venue]:
    venues: list[Venue] = []
    for spec in _venue_specs():
        venue = Venue(
            id=new_id(),
            name=spec["name"],
            slug=slugify(spec["name"]),
            description=spec["description"],
            website_url=spec["website_url"],
            phone=spec["phone"],
            primary_category=spec["category"],
            cuisines=spec["cuisines"],
            price_level=spec["price_level"],
            drink_kinds=spec["drink_kinds"],
            accepts_reservations=spec["accepts_reservations"],
            features=spec["features"],
            vertical="food",
            status=RecordStatus.PUBLISHED,
        )
        loc = spec["location"]
        now = datetime.now(UTC)
        venue.locations.append(
            VenueLocation(
                id=new_id(),
                label="Main",
                timezone="America/Los_Angeles",
                status=RecordStatus.PUBLISHED,
                location_confidence="verified" if spec["name"] == "The Lantern Annex" else "high_confidence",
                geocode_source="manual" if spec["name"] == "The Lantern Annex" else "seed",
                geocode_accuracy="rooftop",
                geocoded_at=now,
                coordinates_verified_at=now if spec["name"] == "The Lantern Annex" else None,
                address_hash=address_hash(loc["address_line1"], loc["city"], loc["region"], loc["postal_code"]),
                **loc,
            )
        )
        if spec["ratings"]:
            _apply_seed_ratings(venue, spec["ratings"])
        venues.append(venue)
    return venues


def _backfill_discovery(db) -> int:
    """Fill discovery columns on existing seed venues so local DBs pick up new filters."""
    by_name = {spec["name"]: spec for spec in _venue_specs()}
    updated = 0
    for venue in db.scalars(select(Venue).options(selectinload(Venue.provider_links))):
        spec = by_name.get(venue.name)
        if spec is None:
            continue
        changed = False
        if not venue.cuisines or venue.price_level is None:
            venue.cuisines = spec["cuisines"]
            venue.price_level = spec["price_level"]
            venue.drink_kinds = spec["drink_kinds"]
            venue.accepts_reservations = spec["accepts_reservations"]
            venue.features = spec["features"]
            changed = True
        for location in venue.locations:
            if not getattr(location, "geocode_source", None):
                location.geocode_source = "manual" if venue.name == "The Lantern Annex" else "seed"
                location.location_confidence = "verified" if venue.name == "The Lantern Annex" else "high_confidence"
                location.address_hash = address_hash(
                    location.address_line1, location.city, location.region, location.postal_code
                )
                location.geocoded_at = datetime.now(UTC)
                changed = True
        ratings = spec.get("ratings") or []
        if ratings:
            existing = {link.provider for link in venue.provider_links}
            missing = [item for item in ratings if item["provider"] not in existing]
            if missing:
                now = datetime.now(UTC)
                for item in missing:
                    venue.provider_links.append(
                        VenueProviderLink(
                            id=new_id(),
                            provider=item["provider"],
                            provider_business_id=f"seed:{slugify(venue.name)}:{item['provider']}",
                            rating=Decimal(item["rating"]),
                            review_count=item["review_count"],
                            first_seen_at=now,
                            last_seen_at=now,
                            extra_metadata={"seed": True},
                        )
                    )
            source_count = int(getattr(venue, "rating_source_count", 0) or 0)
            if missing or getattr(venue, "rating", None) is None or source_count < len(ratings):
                apply_to_venue(venue, _provider_ratings(ratings))
                changed = True
        if changed:
            updated += 1
    return updated


def _provider_ratings(specs: list[RatingSpec]) -> list[ProviderRating]:
    return [
        ProviderRating(
            provider=item["provider"],
            rating=Decimal(item["rating"]),
            review_count=item["review_count"],
        )
        for item in specs
    ]


def _apply_seed_ratings(venue: Venue, specs: list[RatingSpec]) -> None:
    now = datetime.now(UTC)
    for item in specs:
        venue.provider_links.append(
            VenueProviderLink(
                id=new_id(),
                provider=item["provider"],
                provider_business_id=f"seed:{slugify(venue.name)}:{item['provider']}",
                rating=Decimal(item["rating"]),
                review_count=item["review_count"],
                first_seen_at=now,
                last_seen_at=now,
                extra_metadata={"seed": True},
            )
        )
    apply_to_venue(venue, _provider_ratings(specs))


def _ensure_map_acceptance_venue(db) -> bool:
    """Guarantee the non-Google Hollywood pin exists on databases that already have seed rows."""
    existing = db.scalar(select(Venue).where(Venue.slug == "the-lantern-annex"))
    if existing is not None:
        return False
    specs = [spec for spec in _venue_specs() if spec["name"] == "The Lantern Annex"]
    venues = []
    for spec in specs:
        venue = Venue(
            id=new_id(),
            name=spec["name"],
            slug=slugify(spec["name"]),
            description=spec["description"],
            website_url=spec["website_url"],
            phone=spec["phone"],
            primary_category=spec["category"],
            cuisines=spec["cuisines"],
            price_level=spec["price_level"],
            drink_kinds=spec["drink_kinds"],
            accepts_reservations=spec["accepts_reservations"],
            features=spec["features"],
            vertical="food",
            status=RecordStatus.PUBLISHED,
        )
        loc = spec["location"]
        now = datetime.now(UTC)
        venue.locations.append(
            VenueLocation(
                id=new_id(),
                label="Main",
                timezone="America/Los_Angeles",
                status=RecordStatus.PUBLISHED,
                location_confidence="verified",
                geocode_source="manual",
                geocode_accuracy="rooftop",
                geocoded_at=now,
                coordinates_verified_at=now,
                address_hash=address_hash(loc["address_line1"], loc["city"], loc["region"], loc["postal_code"]),
                **loc,
            )
        )
        venues.append(venue)
    db.add_all(venues)
    db.flush()
    _add_lantern_offer(db, venues[0])
    return True


def _add_lantern_offer(db, venue: Venue) -> None:
    source = Source(
        id=new_id(),
        venue_id=venue.id,
        source_type=SourceType.MANUAL,
        url="manual://lantern-annex",
        canonical_identity="manual://lantern-annex",
        is_active=True,
        crawl_enabled=False,
        trust_level=TrustLevel.HIGH,
    )
    db.add(source)
    db.flush()
    location = venue.locations[0]
    deal = Deal(
        id=new_id(),
        venue_location_id=location.id,
        title="Annex hour",
        description="House pours at a Hollywood wine room that only exists in FindGood.",
        deal_type=DealType.HAPPY_HOUR,
        offering_kind=DealOfferingKind.DRINK,
        vertical="food",
        status=RecordStatus.PUBLISHED,
        publication_state=PublicationState.PUBLISHED,
        source_confidence=Decimal("0.900"),
        freshness_status="fresh",
        last_verified_at=datetime.now(UTC),
    )
    db.add(deal)
    db.flush()
    db.add(
        DealSchedule(
            id=new_id(),
            deal_id=deal.id,
            days_of_week=WEEKDAYS,
            start_time=time(16, 0),
            end_time=time(19, 0),
        )
    )
    db.add(
        DealItem(
            id=new_id(),
            deal_id=deal.id,
            name="House martini",
            category="drink",
            normal_price=Decimal("16.00"),
            deal_price=Decimal("6.00"),
            currency="USD",
        )
    )
    db.add(
        DealPublication(
            id=new_id(),
            deal_id=deal.id,
            source_id=source.id,
            published_by="seed",
            notes="Non-Google map acceptance venue",
        )
    )
    db.add(
        Verification(
            id=new_id(),
            subject_type="deal",
            subject_id=deal.id,
            verification_type=VerificationType.MANUAL,
            verified_at=datetime.now(UTC),
            actor="seed",
            notes="Fictional seed verification — not a real-world claim",
            confidence=Decimal("1.000"),
        )
    )


def _catalog(venues: list[Venue]):
    by_name = {venue.name: venue for venue in venues}
    deals: list[Deal] = []
    items: list[DealItem] = []
    schedules: list[DealSchedule] = []
    sources: list[Source] = []
    publications: list[DealPublication] = []
    verifications: list[Verification] = []

    def add_source(venue: Venue, source_type: str, url: str, *, crawl: bool = False) -> Source:
        source = Source(
            id=new_id(),
            venue_id=venue.id,
            source_type=source_type,
            url=url,
            canonical_identity=url,
            is_active=True,
            crawl_enabled=crawl,
            trust_level=TrustLevel.HIGH if source_type == SourceType.MANUAL else TrustLevel.MEDIUM,
        )
        sources.append(source)
        return source

    def add_deal(
        venue: Venue,
        *,
        title: str,
        description: str,
        deal_type: str,
        offering_kind: str,
        days: list[int],
        start: time | None,
        end: time | None,
        ends_at_close: bool = False,
        valid_from: date | None = None,
        valid_until: date | None = None,
        offer_items: list[tuple[str, str, str, str]],
        source: Source,
        publication_state: str = PublicationState.PUBLISHED,
        freshness_status: str = "fresh",
    ) -> Deal:
        location = venue.locations[0]
        deal = Deal(
            id=new_id(),
            venue_location_id=location.id,
            title=title,
            description=description,
            deal_type=deal_type,
            offering_kind=offering_kind,
            vertical=venue.vertical,
            status=RecordStatus.PUBLISHED,
            publication_state=publication_state,
            source_confidence=Decimal("0.900"),
            freshness_status=freshness_status,
            last_verified_at=datetime.now(UTC),
        )
        deals.append(deal)
        schedules.append(
            DealSchedule(
                id=new_id(),
                deal_id=deal.id,
                days_of_week=days,
                start_time=start,
                end_time=end,
                ends_at_close=ends_at_close,
                valid_from=valid_from,
                valid_until=valid_until,
            )
        )
        for name, category, normal, deal_price in offer_items:
            items.append(
                DealItem(
                    id=new_id(),
                    deal_id=deal.id,
                    name=name,
                    category=category,
                    normal_price=Decimal(normal),
                    deal_price=Decimal(deal_price),
                    currency="USD",
                )
            )
        publications.append(
            DealPublication(
                id=new_id(),
                deal_id=deal.id,
                source_id=source.id,
                published_by="seed",
                notes="Seeded fictional catalog",
            )
        )
        verifications.append(
            Verification(
                id=new_id(),
                subject_type="deal",
                subject_id=deal.id,
                verification_type=VerificationType.MANUAL,
                verified_at=datetime.now(UTC).replace(hour=17, minute=0, second=0, microsecond=0),
                actor="seed",
                notes="Fictional seed verification — not a real-world claim",
                confidence=Decimal("1.000"),
            )
        )
        return deal

    harbor = by_name["Harbor & Rye"]
    casa = by_name["Casa Nube"]
    pearl = by_name["The Pearl Counter"]
    sunday = by_name["Sunday Provisions"]
    nightbird = by_name["Nightbird Room"]
    lantern = by_name["The Lantern Annex"]

    harbor_source = add_source(harbor, SourceType.MANUAL, "manual://harbor-and-rye")
    casa_source = add_source(casa, SourceType.MANUAL, "manual://casa-nube")
    pearl_source = add_source(pearl, SourceType.MANUAL, "manual://pearl-counter")
    sunday_source = add_source(sunday, SourceType.MANUAL, "manual://sunday-provisions")
    nightbird_source = add_source(nightbird, SourceType.MANUAL, "manual://nightbird-room")
    lantern_source = add_source(lantern, SourceType.MANUAL, "manual://lantern-annex")
    add_source(harbor, SourceType.DEMO, "demo://harbor-and-rye", crawl=True)
    add_source(nightbird, SourceType.DEMO, "demo://nightbird-new-special", crawl=True)

    add_deal(
        harbor,
        title="Weekday Harbor Hour",
        description="House cocktails and smash burgers at neighborhood prices, Monday through Friday.",
        deal_type=DealType.HAPPY_HOUR,
        offering_kind=DealOfferingKind.BOTH,
        days=WEEKDAYS,
        start=time(15, 0),
        end=time(18, 0),
        offer_items=[
            ("Rye smash burger", "food", "18.00", "10.00"),
            ("House old fashioned", "drink", "16.00", "9.00"),
        ],
        source=harbor_source,
    )
    add_deal(
        harbor,
        title="Always-on lunch board",
        description="A daily lunch special so the catalog always has something happening now.",
        deal_type=DealType.LUNCH,
        offering_kind=DealOfferingKind.FOOD,
        days=[1, 2, 3, 4, 5, 6, 7],
        start=None,
        end=None,
        offer_items=[("Market grain bowl", "food", "16.00", "11.00")],
        source=harbor_source,
    )
    add_deal(
        casa,
        title="Taco Tuesday",
        description="All-day tacos. The kind of Tuesday that actually feels like a plan.",
        deal_type=DealType.TACO_NIGHT,
        offering_kind=DealOfferingKind.FOOD,
        days=[2],
        start=None,
        end=None,
        offer_items=[("Al pastor taco", "food", "5.00", "3.00"), ("Carnitas taco", "food", "5.00", "3.00")],
        source=casa_source,
    )
    add_deal(
        casa,
        title="Citrus hour",
        description="Margaritas from 4 to 7, every weekday.",
        deal_type=DealType.DRINK_SPECIAL,
        offering_kind=DealOfferingKind.DRINK,
        days=WEEKDAYS,
        start=time(16, 0),
        end=time(19, 0),
        offer_items=[("Casa margarita", "drink", "15.00", "8.00")],
        source=casa_source,
    )
    add_deal(
        pearl,
        title="Half-price oysters",
        description="Pacific oysters, half off, late afternoon at the counter.",
        deal_type=DealType.OYSTER,
        offering_kind=DealOfferingKind.FOOD,
        days=WEEKDAYS,
        start=time(15, 0),
        end=time(18, 0),
        offer_items=[("Pacific oyster", "food", "4.00", "2.00")],
        source=pearl_source,
    )
    add_deal(
        pearl,
        title="Dusk prix fixe",
        description="Three courses before 6 PM. A quiet table, a set menu.",
        deal_type=DealType.PRIX_FIXE,
        offering_kind=DealOfferingKind.FOOD,
        days=WEEKDAYS,
        start=time(16, 30),
        end=time(18, 0),
        offer_items=[("Three-course dusk menu", "food", "62.00", "39.00")],
        source=pearl_source,
    )
    add_deal(
        sunday,
        title="Weekend brunch table",
        description="Saturday and Sunday plates with a proper coffee pour.",
        deal_type=DealType.BRUNCH,
        offering_kind=DealOfferingKind.FOOD,
        days=WEEKEND,
        start=time(9, 0),
        end=time(14, 0),
        offer_items=[("Ricotta pancakes", "food", "18.00", "12.00"), ("House drip", "drink", "5.00", "3.00")],
        source=sunday_source,
    )
    add_deal(
        nightbird,
        title="Late pour",
        description="Sunday late-night specials until close.",
        deal_type=DealType.LATE_NIGHT,
        offering_kind=DealOfferingKind.DRINK,
        days=[7],
        start=time(21, 0),
        end=None,
        ends_at_close=True,
        offer_items=[("Highball", "drink", "14.00", "8.00")],
        source=nightbird_source,
    )
    add_deal(
        lantern,
        title="Annex hour",
        description="House pours at a Hollywood wine room that only exists in FindGood.",
        deal_type=DealType.HAPPY_HOUR,
        offering_kind=DealOfferingKind.DRINK,
        days=WEEKDAYS,
        start=time(16, 0),
        end=time(19, 0),
        offer_items=[("House martini", "drink", "16.00", "6.00")],
        source=lantern_source,
    )
    add_deal(
        nightbird,
        title="Summer spritz flight",
        description="A limited-time flight that ended last month. Kept for provenance and filters.",
        deal_type=DealType.LIMITED_TIME,
        offering_kind=DealOfferingKind.DRINK,
        days=WEEKDAYS,
        start=time(17, 0),
        end=time(20, 0),
        valid_from=date(2026, 6, 1),
        valid_until=date(2026, 7, 15),
        offer_items=[("Spritz flight", "drink", "22.00", "12.00")],
        source=nightbird_source,
    )
    return deals, items, schedules, sources, publications, verifications


if __name__ == "__main__":
    seed()
