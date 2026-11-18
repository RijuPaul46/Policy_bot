from decimal import Decimal

import pytest

from app.routing.tools.calculator import calculate
from app.routing.router import classify_with_llm, route


def test_emi_known_value():
    assert calculate(
        "emi",
        principal="50000",
        annual_rate="8.5",
        months=60,
    ) == Decimal("1025.83")


def test_zero_rate_emi_and_fee_total():
    assert calculate("emi", principal=1200, annual_rate=0, months=12) == Decimal("100.00")
    assert calculate("fee_total", fees=["10.25", "2.75"]) == Decimal("13.00")


def test_calculator_rejects_negative_amount():
    with pytest.raises(ValueError):
        calculate("simple_interest", principal=-5, rate=5, years=1)


def test_fast_router_handles_greeting_and_emi():
    assert route("Hello there")["route"] == "out_of_scope"
    result = route("Calculate EMI for $50,000 at 8.5% for 5 years")
    assert result["route"] == "calculator"
    assert "$1,025.83" in result["answer"]


def test_llm_router_falls_back_when_classifier_json_is_corrupt():
    class FakeLLM:
        def complete(self, messages, temperature=0.1):
            return "not json"

    assert classify_with_llm("calculate something", FakeLLM()) is None


def test_llm_router_uses_decimal_calculator():
    class FakeLLM:
        def complete(self, messages, temperature=0.1):
            return (
                '{"intent":"calculator","operation":"simple_interest",'
                '"parameters":{"principal":"1000","rate":"5","years":"2"}}'
            )

    result = classify_with_llm("calculate interest", FakeLLM())
    assert result == {"route": "calculator", "answer": "Simple interest: $100.00."}
