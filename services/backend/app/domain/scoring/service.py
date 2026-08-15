from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.deals.money import savings
from app.domain.schedules.engine import AvailabilityStatus
from app.domain.verification.freshness import describe_freshness


@dataclass(frozen=True)
class ScoreFactor:
    name: str
    contribution: float
    explanation: str


@dataclass(frozen=True)
class DealScore:
    score: int
    factors: list[ScoreFactor]


@dataclass(frozen=True)
class ScoreInput:
    normal_prices: list[Decimal | None]
    deal_prices: list[Decimal | None]
    item_count: int
    last_verified_at: datetime | None
    availability_status: AvailabilityStatus
    now: datetime


class DealScoringService:
    """Transparent heuristic. Not a scientific quality score."""

    def score(self, payload: ScoreInput) -> DealScore:
        factors: list[ScoreFactor] = []
        total = 0.0

        percents: list[Decimal] = []
        absolutes: list[Decimal] = []
        deal_only: list[Decimal] = []
        for normal, deal in zip(payload.normal_prices, payload.deal_prices, strict=False):
            absolute, percent = savings(normal, deal)
            if percent is not None:
                percents.append(percent)
            if absolute is not None:
                absolutes.append(absolute)
            if deal is not None:
                deal_only.append(deal)

        if percents:
            avg_pct = float(sum(percents) / len(percents))
            contribution = min(avg_pct / 100.0, 1.0) * 40.0
            factors.append(ScoreFactor("percent_savings", contribution, f"Average savings {avg_pct:.0f}%"))
            total += contribution
        if absolutes:
            avg_abs = float(sum(absolutes) / len(absolutes))
            contribution = min(avg_abs / 20.0, 1.0) * 20.0
            factors.append(ScoreFactor("absolute_savings", contribution, f"About ${avg_abs:.2f} off"))
            total += contribution
        if deal_only:
            avg_price = float(sum(deal_only) / len(deal_only))
            contribution = (1.0 - min(avg_price / 50.0, 1.0)) * 15.0
            factors.append(ScoreFactor("absolute_price", contribution, f"Deal price around ${avg_price:.2f}"))
            total += contribution

        item_contribution = min(payload.item_count / 5.0, 1.0) * 10.0
        factors.append(ScoreFactor("item_count", item_contribution, f"{payload.item_count} discounted item(s)"))
        total += item_contribution

        freshness = describe_freshness(payload.last_verified_at, payload.now)
        if freshness.days_ago is None:
            verify_contribution = 0.0
            verify_expl = "No verification yet"
        elif freshness.days_ago == 0:
            verify_contribution = 10.0
            verify_expl = "Verified today"
        else:
            verify_contribution = max(0.0, 10.0 - freshness.days_ago * 1.2)
            verify_expl = freshness.label
        factors.append(ScoreFactor("verification_freshness", verify_contribution, verify_expl))
        total += verify_contribution

        if payload.availability_status == AvailabilityStatus.ACTIVE_NOW:
            avail = 5.0
            avail_expl = "Available right now"
        elif payload.availability_status in {
            AvailabilityStatus.STARTS_SOON,
            AvailabilityStatus.ACTIVE_LATER_TODAY,
        }:
            avail = 3.0
            avail_expl = "Available later today"
        else:
            avail = 1.0
            avail_expl = "Not available today"
        factors.append(ScoreFactor("availability", avail, avail_expl))
        total += avail

        return DealScore(score=int(round(min(total, 100.0))), factors=factors)
