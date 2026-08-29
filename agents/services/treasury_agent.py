import logging

from agents.models import FinancialMetric
from agents.services.ai_service import analyze_financial_data

logger = logging.getLogger(__name__)

SYSTEM_CONTEXTS = {"kpi", "dashboard"}


def analyze_cash(question):

    latest_record = FinancialMetric.objects.order_by('-created_at').first()

    if not latest_record:
        return {
            "agent": "Treasury Agent",
            "analysis": "No cash data available.",
            "recommendation": "Please upload a financial statement first."
        }

    cash_position = latest_record.cash_position

    if cash_position < 10000:
        liquidity_status = "Low"
        recommendation = (
            "Cash reserves are low. Review cash flow and prioritize collections."
        )

    elif cash_position < 50000:
        liquidity_status = "Moderate"
        recommendation = (
            "Monitor liquidity closely and optimize working capital."
        )

    else:
        liquidity_status = "Healthy"
        recommendation = (
            "Current liquidity position is healthy."
        )

    analysis = (
        f"Current cash position is ₹{cash_position}. "
        f"Liquidity status is {liquidity_status}."
    )

    result = {
        "agent": "Treasury Agent",
        "cash_position": float(cash_position),
        "liquidity_status": liquidity_status,
        "analysis": analysis,
        "recommendation": recommendation
    }

    records = FinancialMetric.objects.order_by("created_at")

    if records.count() > 1:
        result["chart"] = {
            "type": "line",
            "x_key": "month",
            "series": ["cash_position"],
            "data": [
                {"month": r.month, "cash_position": float(r.cash_position)}
                for r in records
            ],
        }

    if question not in SYSTEM_CONTEXTS and records.count() > 1:

        financial_context = ""
        for row in records:
            financial_context += (
                f"Month: {row.month}, Cash Position: ₹{row.cash_position}, "
                f"Revenue: ₹{row.revenue}, Expenses: ₹{row.expenses}\n"
            )

        try:
            ai_response = analyze_financial_data(financial_context, question)
            result["analysis"] = ai_response
        except Exception as e:
            logger.exception("Treasury Agent AI error: %s", e)

    return result