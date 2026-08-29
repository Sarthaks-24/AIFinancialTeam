from __future__ import annotations

import logging

from echo import service as echo
from nexus.base import EchoContext
from nexus.permissions import user_can_access
from nexus.registry import get_specialist, resolve_name
from nexus.specialists.classify import (
    classify_specialist,
    has_explicit_intent,
    is_follow_up,
)

logger = logging.getLogger(__name__)


def route_query(
    question: str,
    user=None,
    specialist_name: str | None = None,
    stream: bool = True,
    conversation_id: int | None = None,
    event_sink=None,
    companion_mode: bool = False,
) -> dict:
    if not question or not str(question).strip():
        return {
            "agent": "Nexus",
            "analysis": "No question provided.",
            "recommendation": "Please enter a valid question.",
        }

    user_id = getattr(user, "id", None) if user is not None else None
    selected = specialist_name
    if not selected:
        selected = (
            echo.get_last_specialist(user_id)
            if is_follow_up(question) and not has_explicit_intent(question)
            else None
        )
        selected = selected or classify_specialist(question)
    canonical_name = resolve_name(selected) or selected
    specialist = get_specialist(canonical_name)

    if specialist is None:
        logger.error("No specialist registered for: %s", selected)
        return {
            "agent": "Nexus",
            "analysis": f"No specialist is registered for '{selected}'.",
            "recommendation": "Choose one of the available specialists and try again.",
        }

    if user is not None and not user_can_access(user, specialist):
        return {
            "agent": specialist.name,
            "analysis": "You do not have permission to use this specialist.",
            "recommendation": "Contact an admin if you need access.",
        }

    turns = echo.get_context(user_id, specialist.name, conversation_id=conversation_id)
    facts = echo.get_relevant_facts(user_id, question)
    context = EchoContext(
        user_id=user_id,
        specialist_name=specialist.name,
        turns=turns,
        facts=facts,
        stream=stream,
        event_sink=event_sink,
        companion_mode=companion_mode,
    )

    user_turn = echo.write_turn(user_id, specialist.name, "user", question, conversation_id=conversation_id)
    if user_turn and not conversation_id:
        conversation_id = user_turn.conversation_id

    try:
        response = specialist.handle(question, context)
    except Exception:
        logger.exception("Specialist %s failed", specialist.name)
        return {
            "agent": specialist.name,
            "analysis": "This specialist is temporarily unavailable.",
            "recommendation": "Please try again shortly.",
        }

    payload = response.to_dict()
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if not stream:
        echo.write_turn(
            user_id,
            specialist.name,
            "specialist",
            payload.get("analysis") or str(payload),
            conversation_id=conversation_id,
        )
    return payload
