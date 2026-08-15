from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TWOPLACES = Decimal("0.01")
MAX_PLAUSIBLE_PRICE = Decimal("10000.00")


class MoneyError(ValueError):
    pass


def parse_money(value: object) -> Decimal:
    if value is None or value == "":
        raise MoneyError("Price is required")
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, float):
        raise MoneyError("Float prices are not allowed")
    elif isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "").replace("USD", "").strip()
        if not cleaned:
            raise MoneyError("Price is empty")
        try:
            amount = Decimal(cleaned)
        except InvalidOperation as exc:
            raise MoneyError(f"Malformed price: {value}") from exc
    else:
        raise MoneyError(f"Unsupported price type: {type(value)}")
    return quantize_money(amount)


def quantize_money(amount: Decimal) -> Decimal:
    if amount < 0:
        raise MoneyError("Price cannot be negative")
    if amount > MAX_PLAUSIBLE_PRICE:
        raise MoneyError("Price exceeds plausible maximum")
    return amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def savings(normal: Decimal | None, deal: Decimal | None) -> tuple[Decimal | None, Decimal | None]:
    """Return (absolute_savings, percent_savings 0-100)."""
    if normal is None or deal is None:
        return None, None
    if normal <= 0:
        return None, None
    absolute = quantize_money(normal - deal) if normal >= deal else Decimal("0.00")
    percent = ((normal - deal) / normal * Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if percent < 0:
        percent = Decimal("0.00")
    return absolute, percent
