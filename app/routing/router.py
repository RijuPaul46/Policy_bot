import json
import logging
import re

from app.generation.llm import GroqClient
from app.generation.prompts import ROUTER_PROMPT
from app.routing.tools.calculator import calculate

logger = logging.getLogger(__name__)
_GREETINGS = re.compile(r"^\s*(hi|hello|hey|good morning|good afternoon)\b", re.I)
_EMI = re.compile(
    r"(?:emi|monthly payment).{0,80}?(\d[\d,]*(?:\.\d+)?)"
    r".{0,50}?(\d+(?:\.\d+)?)\s*%\s*(?:per year|annual|annually|apr)?"
    r".{0,50}?(\d+)\s*(year|years|month|months)\b",
    re.I,
)


def route(question: str) -> dict | None:
    if _GREETINGS.match(question):
        return {
            "route": "out_of_scope",
            "answer": "Hello! I can help answer questions about the indexed policy documents.",
        }
    match = _EMI.search(question)
    if match:
        principal, rate, duration, unit = match.groups()
        months = int(duration) * (12 if unit.lower().startswith("year") else 1)
        payment = calculate(
            "emi",
            principal=principal,
            annual_rate=rate,
            months=months,
        )
        return {
            "route": "calculator",
            "answer": f"Estimated monthly payment: ${payment:,.2f}.",
        }
    return None


def classify_with_llm(question: str, llm: GroqClient) -> dict | None:
    response = llm.complete(
        [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Intent classifier returned invalid JSON; using retrieval fallback")
        return None
    if not isinstance(result, dict):
        logger.warning("Intent classifier returned a non-object; using retrieval fallback")
        return None

    intent = result.get("intent")
    if intent == "retrieval":
        return None
    if intent == "out_of_scope":
        return {
            "route": "out_of_scope",
            "answer": "I can help with questions about the indexed policy documents.",
        }
    if intent != "calculator":
        logger.warning("Intent classifier returned an unsupported intent")
        return None

    operation = result.get("operation")
    parameters = result.get("parameters")
    if operation not in {"emi", "simple_interest", "compound_interest", "fee_total"}:
        logger.warning("Intent classifier returned an unsupported calculator operation")
        return None
    if not isinstance(parameters, dict):
        logger.warning("Intent classifier omitted calculator parameters")
        return None
    try:
        value = calculate(operation, **parameters)
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        logger.warning("Intent classifier produced invalid calculator inputs: %s", exc)
        return None
    label = {
        "emi": "Estimated monthly payment",
        "simple_interest": "Simple interest",
        "compound_interest": "Compound amount",
        "fee_total": "Total fees",
    }[operation]
    return {"route": "calculator", "answer": f"{label}: ${value:,.2f}."}
