from agents.models import FinancialMetric
from .treasury_agent import analyze_cash
from .budget_agent import analyze_budget


def get_kpis(user):
    org = user.profile.organization if hasattr(user, 'profile') else None
    latest = FinancialMetric.objects.filter(organization=org).order_by("-created_at").first()

    if latest is None:
        return {
            "revenue": 0,
            "expenses": 0,
            "ebitda": 0,
            "cash_position": 0,
            "liquidity_status": "Unknown",
            "budget_variance": 0,
            "budget_status": "Unknown",
        }

    treasury = analyze_cash("kpi", organization=org)
    budget = analyze_budget("kpi", organization=org)

    return {
        "revenue": float(latest.revenue),
        "expenses": float(latest.expenses),
        "ebitda": float(latest.ebitda),

        "cash_position": float(latest.cash_position),
        "liquidity_status": treasury["liquidity_status"],

        "budget_variance": budget["variance"],
        "budget_status": budget["status"],
    }