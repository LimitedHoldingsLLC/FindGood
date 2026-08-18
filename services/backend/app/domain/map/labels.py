"""Short deal labels for map markers. Deterministic, no AI."""

from decimal import Decimal
from typing import Any


def marker_label(*, title: str, deal_type: str, items: list[Any]) -> str:
    priced = [item for item in items if getattr(item, "deal_price", None) is not None]
    if priced:
        cheapest = min(priced, key=lambda item: Decimal(str(item.deal_price)))
        amount = Decimal(str(cheapest.deal_price))
        money = f"${int(amount)}" if amount == amount.to_integral_value() else f"${amount.quantize(Decimal('0.01'))}"
        if deal_type == "happy_hour":
            return f"{money} HH"
        name = str(getattr(cheapest, "name", "") or "").strip()
        if name and len(name) <= 14:
            return f"{money} {name}"
        return money
    percents = [item for item in items if getattr(item, "percent_savings", None) is not None]
    if percents:
        best = max(percents, key=lambda item: Decimal(str(item.percent_savings)))
        return f"{int(Decimal(str(best.percent_savings)))}% off"
    compact = title.strip()
    if deal_type == "happy_hour":
        return "HH"
    return compact[:16]
