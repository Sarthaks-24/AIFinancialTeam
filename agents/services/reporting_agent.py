import logging

from agents.models import FinancialMetric, Report
from agents.services.ai_service import ask_gemini

from .budget_agent import analyze_budget
from .execution_agent import create_tasks
from .fpna_agent import analyze_finance
from .treasury_agent import analyze_cash

logger = logging.getLogger(__name__)


def generate_report(question, organization=None):

    # Pass "dashboard" so these three skip their own Gemini call — we only
    # need their structured numbers and charts here, since this agent
    # writes its own single AI narrative below.
    finance_data = analyze_finance("dashboard", organization=organization)
    treasury_data = analyze_cash("dashboard", organization=organization)
    budget_data = analyze_budget("dashboard", organization=organization)

    records = FinancialMetric.objects.filter(organization=organization).order_by("-created_at")[:2]

    if records.count() < 2:
        revenue_change = 0
        ebitda_change = 0
        current_month_label = records[0].month if records else "N/A"
    else:
        current, previous = records[0], records[1]
        revenue_change = float(current.revenue) - float(previous.revenue)
        ebitda_change = float(current.ebitda) - float(previous.ebitda)
        current_month_label = current.month

    cash_position = treasury_data.get("cash_position", 0)
    liquidity = treasury_data.get("liquidity_status", "Unknown")

    variance = budget_data.get("variance", 0)
    budget_status = budget_data.get("status", "Unknown")

    # -------------------------
    # AI Executive Report
    # -------------------------

    prompt = f"""
You are an experienced Chief Financial Officer.

Analyze the following financial information and generate:

1. Executive Summary
2. Key Risks
3. Recommendations

Financial Analysis:
{finance_data.get("analysis", "No analysis available.")}

Treasury Analysis:
{treasury_data.get("analysis", "No analysis available.")}

Budget Analysis:
{budget_data.get("analysis", "No analysis available.")}

Provide a professional CFO-level response.
"""

    try:
        ai_report = ask_gemini(prompt)

    except Exception as e:

        logger.exception("AI Report Error: %s", e)

        ai_report = """
Executive Summary:
AI report generation is temporarily unavailable.

Key Risks:
- Revenue decline
- EBITDA decline
- Budget overspending

Recommendations:
- Improve revenue performance
- Control operating expenses
- Monitor cash flow closely.
"""

    # -------------------------
    # Existing Executive Summary
    # -------------------------

    executive_summary = f"""
As of {current_month_label}, revenue {'increased' if revenue_change > 0 else 'decreased'} by ₹{abs(revenue_change):,.2f}
and EBITDA {'increased' if ebitda_change > 0 else 'decreased'} by ₹{abs(ebitda_change):,.2f} compared to the previous month.

Current cash position is ₹{cash_position:,.2f} with {liquidity.lower()} liquidity.

Budget analysis shows a variance of ₹{abs(variance):,.2f}
with a status of {budget_status}.

Management should focus on revenue growth,
cost optimization, liquidity monitoring,
and budget discipline.
"""

    # -------------------------
    # Recommended Actions
    # -------------------------

    actions = []

    if revenue_change < 0:
        actions.append(
            "Investigate revenue decline and identify underperforming business areas."
        )

    if ebitda_change < 0:
        actions.append(
            "Review operating expenses and improve profitability."
        )

    if liquidity.lower() != "healthy":
        actions.append(
            "Monitor cash flow and optimize working capital."
        )

    if budget_status == "Overspending":
        actions.append(
            "Review departmental spending and enforce budget controls."
        )

    # -------------------------
    # Execution Layer
    # -------------------------

    execution_result = create_tasks(actions, organization=organization) if actions else {
        "agent": "Execution Agent",
        "tasks_created": []
    }

    Report.objects.create(
        organization=organization,
        report_type="Executive Financial Report",
        summary=executive_summary
    )

    # -------------------------
    # Charts
    # -------------------------

    charts = []

    if finance_data.get("chart"):
        charts.append({**finance_data["chart"], "title": "Revenue, Expenses & EBITDA Trend"})

    if treasury_data.get("chart"):
        charts.append({**treasury_data["chart"], "title": "Cash Position Trend"})

    if budget_data.get("chart"):
        charts.append({**budget_data["chart"], "title": "Budget vs Expenses"})

    return {
        "agent": "Reporting Agent",
        "ai_report": ai_report,
        "executive_summary": executive_summary,
        "recommended_actions": actions,
        "execution": execution_result,
        "charts": charts
    }