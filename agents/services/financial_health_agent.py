from agents.models import FinancialMetric


def analyze_financial_health(question, organization=None):

    records = FinancialMetric.objects.filter(organization=organization).order_by("-created_at")[:2]

    if len(records) < 2:
        return {
            "agent": "Financial Health Agent",
            "health_score": 0,
            "status": "No Data",
            "strengths": [],
            "weaknesses": [],
            "recommendations": ["Please upload at least two financial records."],
            "ai_insight": "Not enough financial data available."
        }

    current = records[0]
    previous = records[1]

    if current.cash_position < 10000:
        liquidity_status = "Low"
    elif current.cash_position < 50000:
        liquidity_status = "Moderate"
    else:
        liquidity_status = "Healthy"

    budget_status = (
        "Overspending" if current.expenses > current.budget
        else "Under Budget" if current.expenses < current.budget
        else "On Budget"
    )

    score = 100

    # Revenue
    if current.revenue < previous.revenue:
        score -= 15

    # EBITDA
    if current.ebitda < previous.ebitda:
        score -= 20

    # Liquidity
    if liquidity_status != "Healthy":
        score -= 15

    # Budget
    if budget_status == "Overspending":
        score -= 20

    if score >= 80:
        status = "Healthy"
    elif score >= 60:
        status = "Moderate Risk"
    else:
        status = "High Risk"

    strengths = []
    weaknesses = []
    recommendations = []

    if current.cash_position > 30000:
        strengths.append("Cash position remains stable.")

    if current.revenue < previous.revenue:
        weaknesses.append("Revenue decline detected.")
        recommendations.append("Focus on revenue growth initiatives.")

    if current.ebitda < previous.ebitda:
        weaknesses.append("EBITDA has decreased significantly.")
        recommendations.append("Reduce operating expenses and improve profitability.")

    if budget_status == "Overspending":
        weaknesses.append("Budget overspending observed.")
        recommendations.append("Strengthen budget controls.")

    if liquidity_status != "Healthy":
        recommendations.append("Monitor cash flow and working capital closely.")

    changes = []
    if current.revenue != previous.revenue:
        direction = "increased" if current.revenue > previous.revenue else "decreased"
        changes.append(f"Revenue {direction} from ₹{previous.revenue} to ₹{current.revenue}.")
    if current.ebitda != previous.ebitda:
        direction = "increased" if current.ebitda > previous.ebitda else "decreased"
        changes.append(f"EBITDA {direction} from ₹{previous.ebitda} to ₹{current.ebitda}.")

    analysis = f"Financial health is {status} with a score of {score}/100."
    if changes:
        analysis += " " + " ".join(changes[:2])
    if recommendations:
        recommendation = recommendations[0]
    else:
        recommendation = "Continue monitoring revenue, profitability, liquidity, and budget variance."

    return {
        "agent": "Financial Health Agent",
        "health_score": score,
        "status": status,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "analysis": analysis,
        "recommendation": recommendation,
    }
