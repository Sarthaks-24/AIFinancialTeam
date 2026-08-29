"""Echo shared-memory service.

Phase 1 retrieval is recency + simple keyword match on MemoryFact.
Embeddings come later (Phase 4).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from .models import Conversation, MemoryFact, Turn

logger = logging.getLogger(__name__)


def _active_facts_qs(user_id: int):
    now = timezone.now()
    return MemoryFact.objects.filter(user_id=user_id).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def get_or_create_conversation(user_id: int, specialist_name: str) -> Conversation:
    conversation = (
        Conversation.objects.filter(user_id=user_id, specialist=specialist_name)
        .order_by("-last_active_at")
        .first()
    )
    if conversation:
        Conversation.objects.filter(pk=conversation.pk).update(
            last_active_at=timezone.now()
        )
        conversation.refresh_from_db()
        return conversation

    return Conversation.objects.create(
        user_id=user_id,
        specialist=specialist_name,
    )


def create_conversation(user_id: int, title: str = "") -> Conversation:
    """Create an explicit, user-owned chat session."""
    user = Conversation._meta.get_field("user").remote_field.model.objects.get(pk=user_id)
    organization = getattr(getattr(user, "profile", None), "organization", None)
    return Conversation.objects.create(
        user_id=user_id,
        organization=organization,
        title=title.strip()[:255],
    )


def get_conversation(
    user_id: int | None, conversation_id: int, include_archived: bool = False
) -> Conversation | None:
    if not user_id:
        return None
    conversations = Conversation.objects.filter(pk=conversation_id, user_id=user_id)
    if not include_archived:
        conversations = conversations.filter(archived_at__isnull=True)
    return conversations.first()


def archive_conversation(user_id: int | None, conversation_id: int) -> Conversation | None:
    conversation = get_conversation(user_id, conversation_id)
    if not conversation:
        return None
    conversation.archived_at = timezone.now()
    conversation.save(update_fields=["archived_at"])
    return conversation


def get_context(
    user_id: int | None,
    specialist_name: str,
    limit: int = 10,
    conversation_id: int | None = None,
) -> list[dict]:
    if not user_id:
        return []

    conversation = (
        get_conversation(user_id, conversation_id)
        if conversation_id
        else Conversation.objects.filter(user_id=user_id, specialist=specialist_name)
        .order_by("-last_active_at")
        .first()
    )
    if not conversation:
        return []

    turns = conversation.turns.order_by("-created_at")[:limit]
    ordered = list(reversed(list(turns)))
    return [
        {
            "role": turn.role,
            "specialist_name": turn.specialist_name,
            "content": turn.content,
            "created_at": turn.created_at.isoformat(),
        }
        for turn in ordered
    ]


def get_last_specialist(user_id: int | None) -> str | None:
    """Return the specialist from the user's most recently active conversation."""
    if not user_id:
        return None
    conversation = (
        Conversation.objects.filter(user_id=user_id)
        .order_by("-last_active_at")
        .first()
    )
    return conversation.specialist if conversation else None


def _legacy_write_turn(
    user_id: int | None,
    specialist_name: str,
    role: str,
    content: str,
) -> Turn | None:
    if not user_id or not content:
        return None

    conversation = get_or_create_conversation(user_id, specialist_name)
    turn = Turn.objects.create(
        conversation=conversation,
        role=role,
        specialist_name=specialist_name,
        content=content,
    )
    logger.debug(
        "Echo wrote turn user=%s specialist=%s role=%s",
        user_id,
        specialist_name,
        role,
    )
    return turn


def write_turn(
    user_id: int | None,
    specialist_name: str,
    role: str,
    content: str,
    conversation_id: int | None = None,
) -> Turn | None:
    if not user_id or not content:
        return None

    conversation = (
        get_conversation(user_id, conversation_id)
        if conversation_id
        else get_or_create_conversation(user_id, specialist_name)
    )
    if not conversation:
        return None
    if not conversation.title and role == Turn.Role.USER:
        conversation.title = content.strip()[:80]
        conversation.save(update_fields=["title", "last_active_at"])
    turn = Turn.objects.create(
        conversation=conversation,
        role=role,
        specialist_name=specialist_name,
        content=content,
    )
    logger.debug(
        "Echo wrote turn user=%s specialist=%s role=%s",
        user_id,
        specialist_name,
        role,
    )
    return turn


def get_relevant_facts(user_id: int | None, query: str, limit: int = 5) -> list[dict]:
    if not user_id:
        return []

    facts = list(_active_facts_qs(user_id))
    if not facts:
        return []

    # Get embedding for the query
    try:
        from agents.services.ai_service import client
        response = client.models.embed_content(
            model='text-embedding-004',
            contents=query,
        )
        query_embedding = response.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding for query: {e}")
        query_embedding = None

    if query_embedding:
        scored = []
        for fact in facts:
            if fact.embedding:
                # Cosine similarity
                dot_product = sum(a * b for a, b in zip(query_embedding, fact.embedding))
                mag1 = sum(a * a for a in query_embedding) ** 0.5
                mag2 = sum(b * b for b in fact.embedding) ** 0.5
                score = dot_product / (mag1 * mag2) if (mag1 * mag2) > 0 else 0
                scored.append((score, fact))
            else:
                scored.append((0, fact))
        
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        selected = [fact for score, fact in scored if score > 0.5][:limit]
        if not selected:
            # Fallback to recent if no strong match
            selected = sorted(facts, key=lambda f: f.created_at, reverse=True)[:limit]
    else:
        # Fallback to simple keyword match if embedding fails
        tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_]{3,}", query or "")}
        if not tokens:
            selected = sorted(facts, key=lambda f: f.created_at, reverse=True)[:limit]
        else:
            scored = []
            for fact in facts:
                haystack = f"{fact.key} {fact.value}".lower()
                score = sum(1 for token in tokens if token in haystack)
                scored.append((score, fact))
            scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
            selected = [fact for score, fact in scored if score > 0][:limit]
            if not selected:
                selected = sorted(facts, key=lambda f: f.created_at, reverse=True)[:limit]

    return [
        {
            "category": fact.category,
            "key": fact.key,
            "value": fact.value,
            "created_at": fact.created_at.isoformat(),
        }
        for fact in selected
    ]


def write_fact(
    user_id: int | None,
    category: str,
    key: str,
    value: str,
    source_turn_id: int | None = None,
    expires_at: datetime | None = None,
) -> MemoryFact | None:
    if not user_id or not key:
        return None
        
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.get(id=user_id)
    org = user.profile.organization if hasattr(user, 'profile') else None

    embedding = None
    try:
        from agents.services.ai_service import client
        text_to_embed = f"Category: {category}. {key}: {value}"
        response = client.models.embed_content(
            model='text-embedding-004',
            contents=text_to_embed,
        )
        embedding = response.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding for fact: {e}")

    return MemoryFact.objects.create(
        user_id=user_id,
        organization=org,
        category=category,
        key=key,
        value=value,
        source_turn_id=source_turn_id,
        expires_at=expires_at,
        embedding=embedding,
    )
