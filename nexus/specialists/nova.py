"""Nova — AI Financial Advisor (AI-Financial-Team finance specialist).

Wraps existing treasury / cash analysis and pulls Echo conversation
context into Gemini prompts so follow-ups work.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model

from agents.models import FinancialMetric
from agents.services.ai_service import analyze_financial_data
from nexus.base import EchoContext, SpecialistResponse
from nexus.registry import register_specialist
from nexus.specialist import BaseSpecialist

logger = logging.getLogger(__name__)
User = get_user_model()

SYSTEM_CONTEXTS = {"kpi", "dashboard"}


def _financial_records_for_user(user_id: int | None):
    """Scope Nova's financial view to the caller's organization."""
    if not user_id:
        return FinancialMetric.objects.filter(organization=None).order_by("created_at")

    user = User.objects.filter(id=user_id).first()
    organization = user.profile.organization if user and hasattr(user, "profile") else None
    return FinancialMetric.objects.filter(organization=organization).order_by("created_at")


@register_specialist
class NovaAgent(BaseSpecialist):
    name = "Nova"
    domain = "finance"
    model = "gemini"
    required_groups = ["CFO", "Finance Manager"]
    aliases = ["Treasury Agent", "Financial Advisor"]
    title = "AI Financial Advisor"
    description = "Cash flow, liquidity, payments, collections, and treasury context."
    suggested_prompts = [
        "What is today's cash position?",
        "Show the cash trend.",
        "What should we watch in collections?",
    ]

    def can_delegate_to(self) -> list[str]:
        return ["Vega"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        raw = self._analyze_cash(question, context)
        # Surface Nova branding even when reusing treasury-shaped payload
        raw["agent"] = "Nova"
        return SpecialistResponse.from_dict(raw, default_agent="Nova")

    def _analyze_cash(self, question: str, context: EchoContext) -> dict:
        records = _financial_records_for_user(context.user_id)
        latest_record = records.order_by("-created_at").first()

        if not latest_record:
            return {
                "agent": "Nova",
                "analysis": "No cash data available.",
                "recommendation": "Please upload a financial statement first.",
            }

        cash_position = latest_record.cash_position

        if cash_position < 10000:
            liquidity_status = "Low"
            recommendation = (
                "Cash reserves are low. Review cash flow and prioritize collections."
            )
        elif cash_position < 50000:
            liquidity_status = "Moderate"
            recommendation = "Monitor liquidity closely and optimize working capital."
        else:
            liquidity_status = "Healthy"
            recommendation = "Current liquidity position is healthy."

        analysis = (
            f"Current cash position is ₹{cash_position}. "
            f"Liquidity status is {liquidity_status}."
        )

        result = {
            "agent": "Nova",
            "cash_position": float(cash_position),
            "liquidity_status": liquidity_status,
            "analysis": analysis,
            "recommendation": recommendation,
        }

        wants_visual = any(word in question.lower() for word in ("chart", "graph", "trend", "history"))
        if wants_visual and records.count() > 1:
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

            conversation_block = context.format_for_prompt()
            try:
                ai_response = analyze_financial_data(
                    financial_context,
                    question,
                    conversation_context=conversation_block or None,
                    style=context.response_style,
                )
                result["analysis"] = ai_response
            except Exception as e:
                logger.exception("Nova AI error: %s", e)

        return result
