from decimal import Decimal

import pytest
from app.domain.deals.money import MoneyError, parse_money, savings


def test_parse_currency_strings() -> None:
    assert parse_money("$8.00") == Decimal("8.00")
    assert parse_money("1,234.50") == Decimal("1234.50")
    assert parse_money(Decimal("4.1")) == Decimal("4.10")


def test_rejects_floats() -> None:
    with pytest.raises(MoneyError):
        parse_money(8.5)


def test_rejects_negative_and_extreme() -> None:
    with pytest.raises(MoneyError):
        parse_money("-1.00")
    with pytest.raises(MoneyError):
        parse_money("20000")


def test_savings() -> None:
    absolute, percent = savings(Decimal("16.00"), Decimal("8.00"))
    assert absolute == Decimal("8.00")
    assert percent == Decimal("50.00")
