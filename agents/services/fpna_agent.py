import logging

from agents.models import FinancialMetric
from agents.services.ai_service import analyze_financial_data

logger = logging.getLogger(__name__)

SYSTEM_CONTEXTS = {"kpi", "dashboard"}


def analyze_finance(question, organization=None):

    records = FinancialMetric.objects.filter(organization=organization).order_by("created_at")

    if not records.exists():
        return {
            "agent": "FP&A Agent",
            "analysis": "No financial data found.",
            "recommendation": "Please upload an Excel or CSV file first."
        }

    result = {
        "agent": "FP&A Agent",
        "financial_data": [
            {
                "month": r.month,
                "revenue": float(r.revenue),
                "expenses": float(r.expenses),
                "ebitda": float(r.ebitda),
                "cash_position": float(r.cash_position),
                "budget": float(r.budget),
            }
            for r in records
        ]
    }

    if records.count() > 1:
        result["chart"] = {
            "type": "line",
            "x_key": "month",
            "series": ["revenue", "expenses", "ebitda"],
            "data": [
                {
                    "month": r.month,
                    "revenue": float(r.revenue),
                    "expenses": float(r.expenses),
                    "ebitda": float(r.ebitda),
                }
                for r in records
            ],
        }

    latest = records.last()
    result["analysis"] = (
        f"Latest recorded month is {latest.month}, with revenue of ₹{latest.revenue}, "
        f"expenses of ₹{latest.expenses}, and EBITDA of ₹{latest.ebitda}."
    )
    result["recommendation"] = "Structured financial snapshot."

    # Only hit Gemini with the full history for genuine chat questions,
    # not the internal "kpi"/"dashboard" snapshot calls.
    if question not in SYSTEM_CONTEXTS:

        financial_context = ""
        for row in records:
            financial_context += f"""
Month: {row.month}
Revenue: ₹{row.revenue}
Expenses: ₹{row.expenses}
EBITDA: ₹{row.ebitda}
Cash Position: ₹{row.cash_position}
Budget: ₹{row.budget}

"""

        try:
            ai_response = analyze_financial_data(
                financial_context,
                question,
                specialist_name="FP&A Agent",
            )
            result["analysis"] = ai_response
            result["recommendation"] = "Analysis generated using uploaded financial data."
        except Exception as e:
            logger.exception("FP&A Agent AI error: %s", e)
            result["analysis"] = "AI analysis is temporarily unavailable."
            result["recommendation"] = "Please try again."

    return result
