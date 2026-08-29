import logging

from agents.models import FinancialMetric
from agents.services.ai_service import analyze_financial_data

logger = logging.getLogger(__name__)

SYSTEM_CONTEXTS = {"kpi", "dashboard"}


def analyze_budget(question, organization=None):

    records = FinancialMetric.objects.filter(organization=organization).order_by("created_at")
    latest_record = records.last()

    if not latest_record:
        return {
            "agent": "Budget Agent",
            "analysis": "No budget data available.",
            "recommendation": "Please upload a financial statement first."
        }

    total_budget = latest_record.budget
    total_actual = latest_record.expenses

    variance = total_actual - total_budget

    if variance > 0:
        status = "Overspending"
        recommendation = (
            "Review departmental spending and cost controls."
        )
    elif variance < 0:
        status = "Under Budget"
        recommendation = (
            "Spending is within budget limits."
        )
    else:
        status = "On Budget"
        recommendation = (
            "Budget performance is on target."
        )

    analysis = (
        f"For {latest_record.month}, budget was ₹{total_budget}, actual spending was ₹{total_actual}, "
        f"variance is ₹{variance}. Status: {status}."
    )

    result = {
        "agent": "Budget Agent",
        "total_budget": float(total_budget),
        "total_actual": float(total_actual),
        "variance": float(variance),
        "status": status,
        "analysis": analysis,
        "recommendation": recommendation
    }

    if records.count() > 1:
        result["chart"] = {
            "type": "bar",
            "x_key": "month",
            "series": ["budget", "expenses"],
            "data": [
                {"month": r.month, "budget": float(r.budget), "expenses": float(r.expenses)}
                for r in records
            ],
        }

    if question not in SYSTEM_CONTEXTS and records.count() > 1:

        financial_context = ""
        for row in records:
            financial_context += (
                f"Month: {row.month}, Budget: ₹{row.budget}, "
                f"Expenses: ₹{row.expenses}, Revenue: ₹{row.revenue}\n"
            )

        try:
            ai_response = analyze_financial_data(
                financial_context,
                question,
                specialist_name="Budget Agent",
            )
            result["analysis"] = ai_response
        except Exception as e:
            logger.exception("Budget Agent AI error: %s", e)

    return result
