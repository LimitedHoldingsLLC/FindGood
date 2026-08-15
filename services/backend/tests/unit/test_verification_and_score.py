from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.schedules.engine import AvailabilityStatus
from app.domain.scoring.service import DealScoringService, ScoreInput
from app.domain.verification.freshness import describe_freshness


def test_verified_today_label() -> None:
    now = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
    result = describe_freshness(now - timedelta(hours=2), now)
    assert result.label == "Verified today"
    assert result.is_fresh is True


def test_verified_three_days_ago() -> None:
    now = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
    result = describe_freshness(now - timedelta(days=3), now)
    assert result.label == "Last verified 3 days ago"


def test_score_returns_factors() -> None:
    score = DealScoringService().score(
        ScoreInput(
            normal_prices=[Decimal("16.00")],
            deal_prices=[Decimal("8.00")],
            item_count=1,
            last_verified_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
            availability_status=AvailabilityStatus.ACTIVE_NOW,
            now=datetime(2026, 8, 14, 20, 0, tzinfo=UTC),
        )
    )
    assert 0 <= score.score <= 100
    names = {factor.name for factor in score.factors}
    assert "percent_savings" in names
    assert "verification_freshness" in names
