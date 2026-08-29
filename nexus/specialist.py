from __future__ import annotations

from abc import ABC, abstractmethod

from nexus.base import EchoContext, SpecialistResponse


class BaseSpecialist(ABC):
    """Contract every AI-Financial-Team specialist must implement.

    Freeze early — Person B builds against this interface.
    """

    name: str
    domain: str
    model: str = "gemini"
    # Empty list = any authenticated user. Non-empty = user must be in one of these groups (or Admin).
    required_groups: list[str] = []
    aliases: list[str] = []
    title: str = "AI Specialist"
    description: str = "A focused AI-Financial-Team specialist."
    suggested_prompts: list[str] = []
    voice_enabled: bool = True
    collaboration_enabled: bool = True

    @abstractmethod
    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        ...

    def can_delegate_to(self) -> list[str]:
        return []

    def delegate(
        self,
        to_specialist: str,
        question: str,
        context: EchoContext,
        summary: str = "",
    ) -> SpecialistResponse | None:
        """Convenience wrapper around the delegation engine.

        Specialists call ``self.delegate("Vega", question, ctx)``
        instead of importing the engine directly.
        """
        from nexus.delegation import delegate

        return delegate(
            from_specialist=self.name,
            to_specialist=to_specialist,
            question=question,
            user_id=context.user_id,
            summary=summary,
            max_depth=context._max_delegation_depth,
            _current_depth=context._delegation_depth,
            event_sink=context.event_sink,
        )
