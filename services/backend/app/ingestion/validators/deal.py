from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.deals.money import MAX_PLAUSIBLE_PRICE, MoneyError, parse_money


class DealValidator:
    def validate(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not payload.get("title"):
            errors.append("missing_title")
        venue = payload.get("venue") or {}
        if not venue.get("name") and not payload.get("venue_location_id"):
            errors.append("missing_venue")
        schedules = payload.get("schedules") or []
        if not schedules:
            errors.append("missing_schedule")
        for index, schedule in enumerate(schedules):
            days = schedule.get("days_of_week") or []
            if not days:
                errors.append(f"schedule_{index}_missing_days")
            if any(day not in range(1, 8) for day in days):
                errors.append(f"schedule_{index}_invalid_days")
            start = schedule.get("start_time")
            end = schedule.get("end_time")
            if start == "close":
                errors.append(f"schedule_{index}_impossible_start")
            valid_from = schedule.get("valid_from")
            valid_until = schedule.get("valid_until")
            if valid_from and valid_until and str(valid_until) < str(valid_from):
                errors.append(f"schedule_{index}_end_before_start_date")
            if start and end and start != "close" and end != "close":
                try:
                    start_t = datetime.strptime(start, "%H:%M").time()
                    end_t = datetime.strptime(end, "%H:%M").time()
                    # end < start is overnight and allowed
                    _ = (start_t, end_t)
                except ValueError:
                    errors.append(f"schedule_{index}_malformed_time")
        for index, item in enumerate(payload.get("items") or []):
            try:
                normal = parse_money(item["normal_price"]) if item.get("normal_price") is not None else None
                deal = parse_money(item["deal_price"]) if item.get("deal_price") is not None else None
            except MoneyError:
                errors.append(f"item_{index}_malformed_price")
                continue
            if deal is not None and normal is not None and deal > normal:
                errors.append(f"item_{index}_deal_exceeds_normal")
            if normal is not None and normal > MAX_PLAUSIBLE_PRICE:
                errors.append(f"item_{index}_extreme_price")
            if deal is not None and deal > MAX_PLAUSIBLE_PRICE:
                errors.append(f"item_{index}_extreme_price")
        confidence = payload.get("confidence")
        if confidence is not None:
            try:
                if Decimal(str(confidence)) < Decimal("0.20"):
                    errors.append("low_confidence")
            except Exception:
                errors.append("invalid_confidence")
        return errors
