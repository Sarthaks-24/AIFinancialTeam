"""AI-Financial-Team specialists (Phase 2 + Phase 3 collaboration).

Each specialist:
1. Gathers its domain data.
2. Builds a data-context string for Gemini.
3. Calls ask_specialist() with its persona prompt + Echo context.
4. Falls back to a template response if Gemini fails or data is absent.

Phase 3 additions:
- Atlas detects cross-functional questions and delegates to Vega + Nova,
  then synthesizes their responses via ask_synthesis().
- Other specialists declare can_delegate_to() for future use.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from django.contrib.auth import get_user_model

from agents.models import ComplianceRecord, FinancialMetric, Vendor
from agents.services.ai_service import ask_specialist, ask_synthesis
from nexus.base import EchoContext, SpecialistResponse
from nexus.registry import register_specialist
from nexus.specialist import BaseSpecialist

User = get_user_model()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _organization_for_user(user_id: int | None):
    """Return the caller's organization, or the legacy unscoped workspace."""
    if not user_id:
        return None

    user = User.objects.filter(id=user_id).first()
    return user.profile.organization if user and hasattr(user, "profile") else None


def _financial_records(user_id: int | None):
    org = _organization_for_user(user_id)
    return list(FinancialMetric.objects.filter(organization=org).order_by("created_at"))


def _currency(value) -> str:
    return f"INR {float(value):,.0f}"


def _financial_data_context(records) -> str:
    """Build a text block of financial records for Gemini."""
    lines = []
    for row in records:
        lines.append(
            f"Month: {row.month}, Revenue: {_currency(row.revenue)}, "
            f"Expenses: {_currency(row.expenses)}, EBITDA: {_currency(row.ebitda)}, "
            f"Cash: {_currency(row.cash_position)}, Budget: {_currency(row.budget)}"
        )
    return "\n".join(lines)


def _vendor_data_context(vendors) -> str:
    """Build a text block of vendor records for Gemini."""
    lines = []
    for v in vendors:
        renewal = v.contract_renewal_date.isoformat() if v.contract_renewal_date else "Not set"
        lines.append(
            f"Vendor: {v.name}, Category: {v.category or 'N/A'}, "
            f"Annual spend: {_currency(v.annual_spend)}, Risk: {v.risk_level}, "
            f"Contract renewal: {renewal}, Active: {v.is_active}"
        )
        for c in v.contracts.all():
            lines.append(f"  - Contract: {c.title}, Start: {c.start_date}, End: {c.end_date}, Total Value: {_currency(c.total_value)}")
    return "\n".join(lines)


def _compliance_data_context(records) -> str:
    """Build a text block of compliance records for Gemini."""
    lines = []
    for r in records:
        due = r.due_date.isoformat() if r.due_date else "No due date"
        evidence = r.evidence_reference or "None"
        lines.append(
            f"Record: {r.name}, Jurisdiction: {r.jurisdiction or 'N/A'}, "
            f"Status: {r.status}, Due: {due}, Evidence: {evidence}, "
            f"Notes: {r.notes[:120] if r.notes else 'None'}"
        )
        for p in r.policies.all():
            lines.append(f"  - Policy: {p.title}, Last Updated: {p.last_updated.isoformat() if p.last_updated else 'None'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Atlas — AI Chief of Staff (Phase 3: synthesis orchestrator)
# ---------------------------------------------------------------------------

ATLAS_PERSONA = (
    "You are the AI Chief of Staff for a finance team. You provide executive "
    "summaries, business health assessments, and KPI narration. Synthesize the "
    "financial data into a concise executive briefing. Highlight key trends, "
    "notable changes, and areas that need attention. Do not fabricate numbers."
)

# Keywords that signal Atlas should delegate for a cross-functional answer.
_SYNTHESIS_DATA_KEYWORDS = {
    "trend", "compare", "chart", "data", "variance", "analysis",
    "increase", "decrease", "growth", "decline", "change", "why",
    "driver", "explain", "what happened", "falling", "rising",
}
_SYNTHESIS_FINANCE_KEYWORDS = {
    "cash", "collection", "liquidity", "payment", "treasury",
    "receivable", "payable", "working capital", "revenue",
}


def _needs_synthesis(question: str) -> bool:
    """Return True if the question touches both data-analysis and finance domains."""
    q = question.lower()
    has_data = any(kw in q for kw in _SYNTHESIS_DATA_KEYWORDS)
    has_finance = any(kw in q for kw in _SYNTHESIS_FINANCE_KEYWORDS)
    return has_data and has_finance


@register_specialist
class AtlasAgent(BaseSpecialist):
    name = "Atlas"
    domain = "executive_intelligence"
    title = "AI Chief of Staff"
    description = "Executive summaries, business health, and KPI narration."
    suggested_prompts = [
        "Give me an executive financial summary.",
        "Why are collections falling?",
        "How is the business performing this month?",
    ]
    required_groups = ["CFO", "Finance Manager"]

    def can_delegate_to(self) -> list[str]:
        return ["Vega", "Nova"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        records = _financial_records(context.user_id)
        if not records:
            return SpecialistResponse(
                self.name,
                "I do not have KPI data to summarize yet.",
                "Upload financial data first.",
            )

        # Phase 3: detect cross-functional questions and delegate.
        if _needs_synthesis(question) and context._delegation_depth == 0:
            synthesis = self._synthesize(question, records, context)
            if synthesis is not None:
                return synthesis

        # Standard Atlas solo answer.
        data_ctx = _financial_data_context(records)
        conversation_ctx = context.format_for_prompt() or None

        ai_response = ask_specialist(
            data_context=data_ctx,
            question=question,
            specialist_name="Atlas",
            persona_prompt=ATLAS_PERSONA,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
            companion_mode=context.companion_mode,
        )

        # Fallback: if Gemini fails, return template
        if not ai_response:
            latest = records[-1]
            ai_response = (
                f"Latest period: revenue {_currency(latest.revenue)}, "
                f"EBITDA {_currency(latest.ebitda)}, "
                f"cash {_currency(latest.cash_position)}."
            )
            if len(records) > 1:
                prev = records[-2]
                change = float(latest.revenue - prev.revenue)
                direction = "up" if change >= 0 else "down"
                ai_response += f" Revenue is {direction} {_currency(abs(change))} versus {prev.month}."

        return SpecialistResponse(
            self.name,
            ai_response,
            "Use Vega for a detailed trend or Nova for cash context.",
        )

    def _synthesize(
        self,
        question: str,
        records,
        context: EchoContext,
    ) -> SpecialistResponse | None:
        contributors: list[str] = []
        delegate_results: list[dict] = []

        def call_vega():
            return self.delegate(
                "Vega",
                f"Analyze the trend in financial metrics relevant to: {question}",
                context,
                summary="Atlas is investigating a cross-functional question for the user.",
            )

        def call_nova():
            return self.delegate(
                "Nova",
                f"What is the current financial position relevant to: {question}",
                context,
                summary="Atlas is investigating a cross-functional question for the user.",
            )

        # Run handoffs in process.  Each specialist performs ORM work, and sharing
        # Django's request/test transaction across worker threads is not reliable.
        # The delegation contract remains isolated: a failed handoff returns None
        # and Atlas can still synthesize the other specialist's response.
        vega_response = call_vega()
        nova_response = call_nova()

        if vega_response:
            contributors.append("Vega")
            delegate_results.append({
                "specialist": "Vega",
                "analysis": vega_response.analysis,
            })

        if nova_response:
            contributors.append("Nova")
            delegate_results.append({
                "specialist": "Nova",
                "analysis": nova_response.analysis,
            })


        if not delegate_results:
            # Both delegates failed — fall back to solo Atlas.
            return None

        # Synthesize with Gemini.
        data_ctx = _financial_data_context(records)
        conversation_ctx = context.format_for_prompt() or None

        synthesis = ask_synthesis(
            question=question,
            delegate_results=delegate_results,
            data_context=data_ctx,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
            companion_mode=context.companion_mode,
        )

        # Fallback: if synthesis Gemini call fails, stitch manually.
        if not synthesis:
            parts = [r["analysis"] for r in delegate_results]
            synthesis = " ".join(parts)

        return SpecialistResponse(
            agent=self.name,
            analysis=synthesis,
            recommendation="This answer was synthesized from multiple specialists.",
            contributors=contributors,
        )


# ---------------------------------------------------------------------------
# Vega — AI Data Analyst
# ---------------------------------------------------------------------------

VEGA_PERSONA = (
    "You are the AI Data Analyst for a finance team. You analyze trends, "
    "comparisons, and explain data patterns. Provide clear, numbers-driven "
    "analysis of the financial data. Identify trends, changes, and drivers. "
    "Be specific about percentages and directional changes. Do not fabricate numbers."
)


@register_specialist
class VegaAgent(BaseSpecialist):
    name = "Vega"
    domain = "data_intelligence"
    title = "AI Data Analyst"
    description = "Trends, comparisons, charts, and explanations based on uploaded data."
    suggested_prompts = [
        "Show the revenue trend.",
        "Compare EBITDA with last month.",
        "What is driving expense changes?",
    ]
    required_groups = ["CFO", "Finance Manager"]

    def can_delegate_to(self) -> list[str]:
        return ["Nova"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        records = _financial_records(context.user_id)
        if not records:
            return SpecialistResponse(
                self.name,
                "There is no uploaded data to analyse yet.",
                "Upload at least two financial periods to compare trends.",
            )

        data_ctx = _financial_data_context(records)
        conversation_ctx = context.format_for_prompt() or None

        ai_response = ask_specialist(
            data_context=data_ctx,
            question=question,
            specialist_name="Vega",
            persona_prompt=VEGA_PERSONA,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
        )

        # Determine which metric to chart
        q = question.lower()
        metric, label = "revenue", "Revenue"
        if any(word in q for word in ("ebitda", "profit", "margin")):
            metric, label = "ebitda", "EBITDA"
        elif any(word in q for word in ("cash", "liquidity", "treasury")):
            metric, label = "cash_position", "Cash position"
        elif any(word in q for word in ("expense", "spend", "cost")):
            metric, label = "expenses", "Expenses"
        elif "budget" in q:
            metric, label = "budget", "Budget"

        # Fallback: if Gemini fails, return template
        if not ai_response:
            latest = records[-1]
            ai_response = f"{label} for {latest.month} is {_currency(getattr(latest, metric))}."
            if len(records) > 1:
                prev = records[-2]
                change = float(getattr(latest, metric) - getattr(prev, metric))
                direction = "increased" if change >= 0 else "decreased"
                ai_response += f" It {direction} by {_currency(abs(change))} from {prev.month}."

        chart_data = {
            "chart": {
                "type": "line",
                "title": f"{label} trend",
                "x_key": "month",
                "series": [metric],
                "data": [
                    {"month": row.month, metric: float(getattr(row, metric))}
                    for row in records
                ],
            }
        }

        return SpecialistResponse(
            self.name,
            ai_response,
            "Ask a more specific comparison if you want to investigate a driver.",
            data=chart_data,
        )


# ---------------------------------------------------------------------------
# Aria — AI Operations Manager
# ---------------------------------------------------------------------------

ARIA_PERSONA = (
    "You are the AI Operations Manager. You handle procurement, vendor management, "
    "contracts, invoices, approvals, and operational workflows. Analyze the vendor "
    "data to assess risks, flag upcoming renewals, and provide actionable operations "
    "advice. Do not fabricate vendor data."
)


@register_specialist
class AriaAgent(BaseSpecialist):
    name = "Aria"
    domain = "operations"
    title = "AI Operations Manager"
    description = "Procurement, vendors, contracts, invoices, approvals, and workflows."
    suggested_prompts = [
        "Review vendor risk exposure.",
        "Which contracts are up for renewal?",
        "Summarize our vendor portfolio.",
    ]
    required_groups = ["CFO", "Finance Manager"]

    def can_delegate_to(self) -> list[str]:
        return ["Nova"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        org = _organization_for_user(context.user_id)
        vendors = list(Vendor.objects.filter(organization=org, is_active=True))
        if not vendors:
            return SpecialistResponse(
                self.name,
                "I do not have vendor or procurement records to review yet.",
                "Add vendors in Django Admin before requesting a vendor-risk or contract-renewal review.",
            )

        data_ctx = _vendor_data_context(vendors)
        conversation_ctx = context.format_for_prompt() or None

        ai_response = ask_specialist(
            data_context=data_ctx,
            question=question,
            specialist_name="Aria",
            persona_prompt=ARIA_PERSONA,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
        )

        # Compute structured data for the UI card
        today = timezone.localdate()
        renewal_window = today + timedelta(days=90)
        high_risk = [v for v in vendors if v.risk_level == Vendor.RiskLevel.HIGH]
        renewals = [
            v for v in vendors
            if v.contract_renewal_date and today <= v.contract_renewal_date <= renewal_window
        ]

        structured = {
            "active_vendors": len(vendors),
            "high_risk_vendors": len(high_risk),
            "upcoming_renewals": len(renewals),
        }

        # Fallback: if Gemini fails, return template
        if not ai_response:
            ai_response = f"I found {len(vendors)} active vendors, including {len(high_risk)} marked high risk."
            if renewals:
                ai_response += f" {len(renewals)} contract renewal(s) fall due within the next 90 days."

        return SpecialistResponse(
            self.name,
            ai_response,
            "Prioritize high-risk vendors and upcoming renewals for an owner review.",
            data=structured,
        )


# ---------------------------------------------------------------------------
# Orion — AI Compliance Officer
# ---------------------------------------------------------------------------

ORION_PERSONA = (
    "You are the AI Compliance Officer. You handle compliance, audit readiness, "
    "policy validation, governance, and risk assessment. Analyze compliance records "
    "to identify overdue items, missing evidence, and areas that need attention. "
    "Provide clear audit-readiness guidance. Do not fabricate compliance data."
)


@register_specialist
class OrionAgent(BaseSpecialist):
    name = "Orion"
    domain = "compliance_and_risk"
    title = "AI Compliance Officer"
    description = "Compliance, audit, policy validation, governance, and risk questions."
    suggested_prompts = [
        "How audit-ready are we?",
        "Which compliance items are overdue?",
        "What evidence is missing for our filings?",
    ]
    required_groups = ["CFO", "Auditor"]

    def can_delegate_to(self) -> list[str]:
        return ["Atlas"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        org = _organization_for_user(context.user_id)
        records = list(ComplianceRecord.objects.filter(organization=org))
        if not records:
            return SpecialistResponse(
                self.name,
                "I do not have compliance filings, audit evidence, policy documents, or a risk register to verify a conclusion.",
                "Add compliance records and evidence references in Django Admin for a scoped review.",
            )

        data_ctx = _compliance_data_context(records)
        conversation_ctx = context.format_for_prompt() or None

        ai_response = ask_specialist(
            data_context=data_ctx,
            question=question,
            specialist_name="Orion",
            persona_prompt=ORION_PERSONA,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
            max_output_tokens=350,  # Orion may need more room for audit checklists
        )

        # Compute structured data for the UI card
        attention = [r for r in records if r.status != ComplianceRecord.Status.COMPLIANT]
        overdue = [r for r in records if r.status == ComplianceRecord.Status.OVERDUE]
        without_evidence = [r for r in records if not r.evidence_reference]

        structured = {
            "records_reviewed": len(records),
            "attention_items": len(attention),
            "overdue_items": len(overdue),
            "missing_evidence": len(without_evidence),
        }

        # Fallback: if Gemini fails, return template
        if not ai_response:
            ai_response = f"I reviewed {len(records)} compliance records: {len(attention)} need attention and {len(overdue)} are overdue."
            if without_evidence:
                ai_response += f" {len(without_evidence)} record(s) do not include an evidence reference."

        return SpecialistResponse(
            self.name,
            ai_response,
            "Resolve overdue items and attach evidence before treating any review as complete.",
            data=structured,
        )


# ---------------------------------------------------------------------------
# Luna — AI Product Specialist
# ---------------------------------------------------------------------------

LUNA_PRODUCT_KNOWLEDGE = """
AI-Financial-Team is a platform with six AI specialists:

1. Atlas (Chief of Staff) — Executive summaries, KPI narration, business health.
   Access: CFO, Finance Manager roles.

2. Vega (Data Analyst) — Trends, comparisons, charts, data explanations.
   Access: CFO, Finance Manager roles.

3. Nova (Financial Advisor) — Cash flow, liquidity, payments, collections, treasury.
   Access: CFO, Finance Manager roles.

4. Aria (Operations Manager) — Vendors, procurement, contracts, approvals.
   Access: CFO, Finance Manager roles.

5. Orion (Compliance Officer) — Compliance, audit, governance, risk flags.
   Access: CFO, Auditor roles.

6. Luna (Product Specialist) — Onboarding, setup, feature help, troubleshooting.
   Access: Any authenticated user.

Key workflows:
- Upload financial data: Go to Finance Data page > Upload CSV/Excel with columns: Month, Revenue, Expenses, EBITDA, Cash, Budget.
- View dashboards: Go to Dashboard page (requires CFO role).
- View KPIs: Go to KPI page (requires Finance Manager role).
- Chat with specialists: Go to Chat page > Select a specialist from the dropdown > Type or speak your question.
- Voice chat: Click the microphone icon in Chat to ask a question by voice. The specialist will respond with audio.
- View reports: Go to Reports page (requires Auditor role).
- Manage tasks: Go to Tasks page to view and update task statuses.
- Add vendor/compliance data: Use Django Admin to add Vendor or Compliance records.

Troubleshooting:
- "I can't see a specialist" — Your role may not have access. Contact an admin to get the right group (CFO, Finance Manager, or Auditor).
- "No data available" — Upload financial data first via the Finance Data page.
- "Voice not working" — Allow microphone access in your browser. Use Chrome for best compatibility.
- "File upload fails" — Ensure your file is CSV or Excel, under 5MB, with the required columns.
"""

LUNA_PERSONA = (
    "You are the AI Product Specialist. You help users onboard, navigate features, "
    "understand which specialist to use, troubleshoot issues, and set up their workspace. "
    "You do NOT answer finance, operations, or compliance questions — redirect users to "
    "the appropriate specialist. Use the product knowledge base to answer accurately."
)


@register_specialist
class LunaAgent(BaseSpecialist):
    name = "Luna"
    domain = "product_guidance"
    title = "AI Product Specialist"
    description = "Onboarding, setup, feature discovery, and troubleshooting for this workspace."
    suggested_prompts = [
        "How do I upload financial data?",
        "Which specialist should I ask about a vendor?",
        "What can each specialist do?",
    ]
    # Luna is available to any authenticated user
    required_groups = []
    collaboration_enabled = False

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        conversation_ctx = context.format_for_prompt() or None

        ai_response = ask_specialist(
            data_context=LUNA_PRODUCT_KNOWLEDGE,
            question=question,
            specialist_name="Luna",
            persona_prompt=LUNA_PERSONA,
            conversation_context=conversation_ctx,
            style=context.response_style,
            stream=context.stream,
        )

        # Fallback: if Gemini fails, return static guide
        if not ai_response:
            ai_response = (
                "You can upload monthly metrics in Finance Data, review them in Dashboard and KPI, "
                "and use the chat to speak with a specialist. Choose Nova for cash, Vega for data "
                "analysis, Aria for operations, Orion for compliance, or Atlas for an executive summary."
            )

        return SpecialistResponse(
            self.name,
            ai_response,
            "Tell me which screen or workflow you want help with and I will guide you through it.",
        )
