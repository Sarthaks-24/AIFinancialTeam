"""Nexus routing for the six Phase 2 AI-Financial-Team specialists."""

from __future__ import annotations

import re


def _keyword_fallback(question: str, default: str | None = "Atlas") -> str | None:
    q = question.lower()
    if any(word in q for word in ("cash", "liquidity", "working capital", "bank balance", "treasury", "collections", "payment")):
        return "Nova"
    if any(word in q for word in ("revenue", "ebitda", "profit", "margin", "forecast", "growth", "trend", "chart", "compare", "budget", "variance", "expense", "spend", "data")):
        return "Vega"
    if any(word in q for word in ("vendor", "procurement", "contract", "invoice", "approval", "workflow", "operations")):
        return "Aria"
    if any(word in q for word in ("gst", "tax", "compliance", "regulatory", "filing", "audit", "fraud", "policy", "governance", "risk")):
        return "Orion"
    if any(word in q for word in ("onboard", "setup", "connect", "help", "feature", "troubleshoot", "how do i")):
        return "Luna"
    if any(word in q for word in ("summary", "executive", "kpi", "health", "strategy", "company")):
        return "Atlas"
    return default


def classify_specialist(question: str) -> str:
    """Use deterministic routing until model-based routing is tuned in Phase 2."""
    return _keyword_fallback(question) or "Atlas"


def has_explicit_intent(question: str) -> bool:
    return _keyword_fallback(question, default=None) is not None


def is_follow_up(question: str) -> bool:
    q = question.strip().lower()
    if not q or len(re.findall(r"\w+", q)) > 16:
        return False
    return any(
        phrase in q
        for phrase in (
            "compared to", "compare it", "what about", "how about", "better or worse",
            "last month", "this month", "that", "it", "same period", "why did it",
        )
    )
