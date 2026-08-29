from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EchoContext:
    """Scoped context Nexus passes into a specialist."""

    user_id: int | None
    specialist_name: str
    turns: list[dict] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    summary: str | None = None  # scoped handoff summary (Phase 3)
    event_sink: Any = None  # callback for emitting out-of-band events (e.g., delegation)
    companion_mode: bool = False
    response_style: str = "concise"  # concise | voice
    stream: bool = True  # whether to stream generator responses
    # Delegation depth tracking (internal — set by delegation engine)
    _delegation_depth: int = 0
    _max_delegation_depth: int = 2

    def format_for_prompt(self) -> str:
        parts: list[str] = []

        if self.summary:
            parts.append(f"Handoff summary:\n{self.summary}")

        if self.facts:
            fact_lines = [
                f"- [{f.get('category')}] {f.get('key')}: {f.get('value')}"
                for f in self.facts
            ]
            parts.append("Known facts:\n" + "\n".join(fact_lines))

        if self.turns:
            turn_lines = []
            for turn in self.turns[-6:]:
                role = turn.get("role", "user")
                label = "User" if role == "user" else turn.get("specialist_name", "Assistant")
                content = (turn.get("content") or "")[:400]
                turn_lines.append(f"{label}: {content}")
            parts.append("Recent conversation:\n" + "\n".join(turn_lines))

        return "\n\n".join(parts)


@dataclass
class SpecialistResponse:
    agent: str
    analysis: str
    recommendation: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    contributors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "agent": self.agent,
            "analysis": self.analysis,
            "recommendation": self.recommendation,
        }
        if self.contributors:
            payload["contributors"] = self.contributors
        payload.update(self.data)
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any], default_agent: str = "Unknown") -> SpecialistResponse:
        data = {
            key: value
            for key, value in raw.items()
            if key not in {"agent", "analysis", "recommendation", "contributors"}
        }
        return cls(
            agent=raw.get("agent", default_agent),
            analysis=raw.get("analysis", ""),
            recommendation=raw.get("recommendation", ""),
            data=data,
            contributors=raw.get("contributors", []),
        )
