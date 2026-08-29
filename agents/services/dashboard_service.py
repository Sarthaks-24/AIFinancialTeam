from agents.models import FinancialMetric, Task, Report
from .treasury_agent import analyze_cash
from .budget_agent import analyze_budget
from .financial_health_agent import analyze_financial_health


def get_dashboard_data(user):
    org = user.profile.organization if hasattr(user, 'profile') else None

    # ----------------------------
    # Latest Financial Record
    # ----------------------------
    latest = FinancialMetric.objects.filter(organization=org).order_by("-created_at").first()

    if latest is None:
        return {
            "health_score": 0,
            "financial_status": "No Data",
            "revenue": 0,
            "ebitda": 0,
            "cash_position": 0,
            "liquidity_status": "Unknown",
            "budget_variance": 0,
            "budget_status": "Unknown",
            "total_reports": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "pending_tasks": 0,
            "recommendations": [],
            "executive_summary": "No financial data available."
        }

    # ----------------------------
    # Other Agents
    # ----------------------------
    treasury = analyze_cash("dashboard")
    budget = analyze_budget("dashboard")
    health = analyze_financial_health("dashboard")

    # ----------------------------
    # Reports & Tasks
    # ----------------------------
    total_reports = Report.objects.filter(organization=org).count()

    total_tasks = Task.objects.filter(organization=org).count()

    completed_tasks = Task.objects.filter(
        organization=org,
        status="Completed"
    ).count()

    pending_tasks = Task.objects.filter(
        organization=org,
        status="Pending"
    ).count()

    # ----------------------------
    # Recommendations
    # ----------------------------
    recommendations = health.get("recommendations", [])

    # ----------------------------
    # Executive Summary
    # ----------------------------
    executive_summary = f"""
Company financial health is {health['status']}.

Revenue stands at ₹{latest.revenue:,.2f}
with EBITDA of ₹{latest.ebitda:,.2f}.

Cash position is ₹{latest.cash_position:,.2f}
with {treasury['liquidity_status']} liquidity.

Budget status is {budget['status']}
with a variance of ₹{budget['variance']:,.2f}.
"""

    return {
        "health_score": health["health_score"],
        "financial_status": health["status"],

        "revenue": float(latest.revenue),
        "expenses": float(latest.expenses),
        "ebitda": float(latest.ebitda),
        "cash_position": float(latest.cash_position),
        "budget": float(latest.budget),
        "month": latest.month,

        "liquidity_status": treasury["liquidity_status"],
        "budget_variance": budget["variance"],
        "budget_status": budget["status"],

        "total_reports": total_reports,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,

        "recommendations": recommendations,
        "executive_summary": executive_summary,
    }