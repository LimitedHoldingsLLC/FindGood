"""Sample catalog. Fictional venues — not verified real-world information.

python -m app.db.seed
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select

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


class VenueSpec(TypedDict):
    name: str
    description: str
    website_url: str
    phone: str
    category: str
    location: LocationSpec


def seed() -> None:
    configure_logging("console", "INFO")
    db = SessionLocal()
    try:
        if db.scalar(select(Venue).limit(1)):
            logger.info("seed_skipped", reason="venues_already_exist")
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


def _venues() -> list[Venue]:
    specs: list[VenueSpec] = [
        {
            "name": "Harbor & Rye",
            "description": "A fictional downtown gastropub with rye whiskey and a harbor-view bar.",
            "website_url": "https://harborandrye.example",
            "phone": "213-555-0142",
            "category": "gastropub",
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
    ]
    venues: list[Venue] = []
    for spec in specs:
        venue = Venue(
            id=new_id(),
            name=spec["name"],
            slug=slugify(spec["name"]),
            description=spec["description"],
            website_url=spec["website_url"],
            phone=spec["phone"],
            primary_category=spec["category"],
            status=RecordStatus.PUBLISHED,
        )
        venue.locations.append(
            VenueLocation(
                id=new_id(),
                label="Main",
                timezone="America/Los_Angeles",
                status=RecordStatus.PUBLISHED,
                **spec["location"],
            )
        )
        venues.append(venue)
    return venues


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
    ) -> Deal:
        location = venue.locations[0]
        deal = Deal(
            id=new_id(),
            venue_location_id=location.id,
            title=title,
            description=description,
            deal_type=deal_type,
            offering_kind=offering_kind,
            status=RecordStatus.PUBLISHED,
            publication_state=publication_state,
            source_confidence=Decimal("0.900"),
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

    harbor_source = add_source(harbor, SourceType.MANUAL, "manual://harbor-and-rye")
    casa_source = add_source(casa, SourceType.MANUAL, "manual://casa-nube")
    pearl_source = add_source(pearl, SourceType.MANUAL, "manual://pearl-counter")
    sunday_source = add_source(sunday, SourceType.MANUAL, "manual://sunday-provisions")
    nightbird_source = add_source(nightbird, SourceType.MANUAL, "manual://nightbird-room")
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
