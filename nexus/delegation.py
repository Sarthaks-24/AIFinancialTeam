"""Nexus delegation engine — cross-specialist collaboration.

Specialists call `delegate()` to request another specialist's analysis
mid-answer.  Only scoped context is transferred (not the full user
conversation), depth is capped to prevent infinite recursion, and
failures are isolated so the caller can fall back.
"""

from __future__ import annotations

import logging

from echo import service as echo
from nexus.base import EchoContext, SpecialistResponse

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH = 2


def delegate(
    from_specialist: str,
    to_specialist: str,
    question: str,
    user_id: int | None = None,
    summary: str = "",
    max_depth: int = MAX_DELEGATION_DEPTH,
    _current_depth: int = 0,
    event_sink=None,
) -> SpecialistResponse | None:
    """Ask another specialist a scoped question on behalf of the caller.

    Parameters
    ----------
    from_specialist:
        Name of the specialist initiating the delegation.
    to_specialist:
        Name of the target specialist.
    question:
        A focused question formulated by the caller — NOT the raw user
        query.  This keeps context transfer scoped.
    user_id:
        Current user (for Echo lookups and permission checks).
    summary:
        Optional handoff summary giving the target specialist background
        context.
    max_depth:
        Maximum delegation depth (default 2).  Atlas→Vega is depth 1,
        Atlas→Vega→Nova is depth 2.
    _current_depth:
        Internal counter — callers should NOT set this.
    event_sink:
        Callback function for emitting real-time events.

    Returns
    -------
    SpecialistResponse | None
        The delegate's response, or ``None`` if delegation was refused
        or the delegate failed.
    """
    # Lazy import to avoid circular dependency (registry ↔ specialists).
    from nexus.registry import get_specialist

    if _current_depth >= max_depth:
        logger.warning(
            "Delegation depth %d reached (max %d): %s → %s refused",
            _current_depth,
            max_depth,
            from_specialist,
            to_specialist,
        )
        return None

    target = get_specialist(to_specialist)
    if target is None:
        logger.error(
            "Delegation target '%s' not registered (requested by %s)",
            to_specialist,
            from_specialist,
        )
        return None

    # Build a scoped EchoContext for the delegate.
    # We pass the handoff summary but NOT the caller's full conversation.
    facts = echo.get_relevant_facts(user_id, question) if user_id else []
    context = EchoContext(
        user_id=user_id,
        specialist_name=target.name,
        turns=[],          # no prior turns — scoped context only
        facts=facts,
        summary=summary,
        stream=False,      # Delegates must return complete text, not a generator
        _delegation_depth=_current_depth + 1,
        _max_delegation_depth=max_depth,
        event_sink=event_sink,
    )

    logger.info(
        "Delegation [depth %d]: %s → %s — %s",
        _current_depth + 1,
        from_specialist,
        to_specialist,
        question[:80],
    )

    if event_sink:
        event_sink("delegation_started", {
            "from": from_specialist,
            "to": to_specialist,
            "activity": summary or f"Consulting {to_specialist}..."
        })

    try:
        response = target.handle(question, context)
        if event_sink:
            event_sink("delegation_completed", {
                "from": from_specialist,
                "to": to_specialist,
            })
    except Exception as e:
        logger.exception(
            "Delegate %s failed (called by %s)",
            to_specialist,
            from_specialist,
        )
        if event_sink:
            event_sink("delegation_failed", {
                "from": from_specialist,
                "to": to_specialist,
                "reason": str(e)
            })
        return None

    # Log the delegation exchange in Echo for audit.
    echo.write_turn(
        user_id,
        target.name,
        "specialist",
        f"[Delegated by {from_specialist}] {response.analysis[:300]}",
    )

    return response
