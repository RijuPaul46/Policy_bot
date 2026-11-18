from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _amount(value: str | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except InvalidOperation as exc:
        raise ValueError("A valid numeric amount is required") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amounts must be finite and non-negative")
    return amount


def calculate(operation: str, **parameters: str | Decimal | int | list) -> Decimal:
    if operation == "emi":
        principal = _amount(parameters["principal"])
        annual_rate = _amount(parameters["annual_rate"])
        months = int(parameters["months"])
        if months <= 0:
            raise ValueError("Loan duration must be positive")
        monthly_rate = annual_rate / Decimal(1200)
        if monthly_rate == 0:
            return (principal / months).quantize(Decimal("0.01"), ROUND_HALF_UP)
        factor = (Decimal(1) + monthly_rate) ** months
        payment = principal * monthly_rate * factor / (factor - Decimal(1))
        return payment.quantize(Decimal("0.01"), ROUND_HALF_UP)

    if operation == "fee_total":
        fees = parameters.get("fees", [])
        if not isinstance(fees, list):
            raise ValueError("fees must be a list of amounts")
        return sum((_amount(fee) for fee in fees), Decimal(0)).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )

    principal = _amount(parameters["principal"])
    rate = _amount(parameters["rate"]) / Decimal(100)
    if operation == "simple_interest":
        years = _amount(parameters["years"])
        return (principal * rate * years).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if operation == "compound_interest":
        years = int(parameters["years"])
        compounds_per_year = int(parameters.get("compounds_per_year", 1))
        if years < 0 or compounds_per_year <= 0:
            raise ValueError("Years must be non-negative and compounding positive")
        amount = principal * (
            Decimal(1) + rate / compounds_per_year
        ) ** (years * compounds_per_year)
        return amount.quantize(Decimal("0.01"), ROUND_HALF_UP)
    raise ValueError(f"Unsupported calculation: {operation}")
