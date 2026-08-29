"""Ledger specialist for the reconciliation engine."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from agents.services.reconciliation_service import run_reconciliation
from nexus.base import EchoContext, SpecialistResponse
from nexus.registry import register_specialist
from nexus.specialist import BaseSpecialist

User = get_user_model()


def _organization_for_user(user_id: int | None):
    if not user_id:
        return None

    user = User.objects.filter(pk=user_id).first()
    return user.profile.organization if user and hasattr(user, "profile") else None


@register_specialist
class LedgerAgent(BaseSpecialist):
    name = "Ledger"
    domain = "reconciliation"
    title = "AI Reconciliation Controller"
    description = "Settlement-to-ledger matching, exception classification, and reconciliation accuracy."
    suggested_prompts = [
        "Run a reconciliation of the latest settlement and ledger files.",
        "Which reconciliation exceptions need review?",
        "How accurate was the latest reconciliation run?",
    ]
    required_groups = ["CFO", "Finance Manager"]
    aliases = ["Reconciliation", "Recon", "Reconciliation Engine"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        result = run_reconciliation(
            organization=_organization_for_user(context.user_id),
        )
        exceptions = result.get("exceptions_count", 0)
        analysis = result.get("ai_summary") or (
            f"Reconciliation processed {result.get('total_processed', 0)} records "
            f"with {exceptions} exception(s)."
        )
        recommendation = (
            f"Review the {exceptions} flagged exception(s) before posting settlement results."
            if exceptions
            else "No exceptions were found; the reconciliation is ready for review."
        )
        return SpecialistResponse(
            self.name,
            analysis,
            recommendation,
            data=result,
        )