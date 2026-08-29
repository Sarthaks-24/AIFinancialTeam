# 07 — Nexus Orchestration

Nexus is the **routing, permission, and delegation** layer between the API views and the specialist implementations. It ensures every query lands on the right specialist with the right context and access control applied.

---

## Module Structure

```
nexus/
├── base.py          # EchoContext and SpecialistResponse data classes
├── specialist.py    # BaseSpecialist ABC
├── registry.py      # Specialist registration and lookup
├── router.py        # route_query() — main entry point
├── delegation.py    # delegate() — cross-specialist handoffs
├── permissions.py   # user_can_access() — specialist-level RBAC
└── specialists/
    ├── __init__.py  # Imports workforce to trigger @register_specialist decorators
    ├── classify.py  # LLM-based query classification
    └── workforce.py # All six specialist implementations
```

---

## Registry ([`nexus/registry.py`](../nexus/registry.py))

The registry is a module-level dict that maps specialist names to singleton instances.

### `@register_specialist`
A class decorator that instantiates the specialist and registers it:

```python
@register_specialist
class NovaAgent(BaseSpecialist):
    name = "Nova"
    ...
```

At startup, `nexus/specialists/__init__.py` imports `workforce`, which executes all `@register_specialist` decorators, populating the registry.

### Key functions
| Function | Description |
|---|---|
| `get_specialist(name) -> BaseSpecialist \| None` | Case-insensitive lookup (also checks aliases) |
| `list_specialists() -> list[BaseSpecialist]` | All registered specialists, sorted by name |
| `resolve_name(name) -> str \| None` | Maps alias or lowercase name to canonical name |

### Aliases
Specialists can declare `aliases = ["financial advisor", "treasury"]` to be reachable by multiple names. The router and UI endpoint use this for fuzzy routing.

---

## Router ([`nexus/router.py`](../nexus/router.py))

`route_query()` is the single entry point called by all API views.

```python
def route_query(
    question: str,
    user=None,
    specialist_name: str | None = None,   # explicit selection from frontend
    stream: bool = True,
    conversation_id: int | None = None,
    event_sink=None,                       # callback for SSE delegation events
    companion_mode: bool = False,
) -> dict:
```

### Routing logic

```
1. Validate question is non-empty.
2. Determine specialist name:
   a. Use explicit specialist_name if provided.
   b. Else if question looks like a follow-up AND no explicit intent keyword:
        → use echo.get_last_specialist() (continue previous conversation)
   c. Else → classify_specialist(question) via Gemini
3. Resolve canonical name via registry (handles aliases + casing).
4. Look up specialist instance from registry.
5. Check user_can_access(user, specialist) → 403 payload if denied.
6. Load Echo context: get_context() + get_relevant_facts().
7. Build EchoContext.
8. Write user turn to Echo.
9. Call specialist.handle(question, context) → SpecialistResponse.
10. Return response dict (+ conversation_id if in streaming mode).
```

---

## Classification ([`nexus/specialists/classify.py`](../nexus/specialists/classify.py))

`classify_specialist(question)` uses Gemini to pick the right specialist.

The prompt includes:
- A description of each registered specialist (from `specialist.description`).
- The user's question.
- Instruction to return exactly one specialist name or "Atlas" as fallback.

`is_follow_up(question)` checks for linguistic markers like:
- Starts with "what about", "and", "also", "how about"
- Contains "compared to", "vs", "same"
- Very short question (< 5 words)

`has_explicit_intent(question)` checks if the question contains domain-specific keywords that indicate a specialist switch (e.g., "compliance", "vendor", "treasury").

---

## Permissions ([`nexus/permissions.py`](../nexus/permissions.py))

`user_can_access(user, specialist) -> bool`

Logic:
1. If `specialist.required_groups` is empty → any authenticated user can access.
2. If the user is in the `Admin` Django group → always allowed.
3. Otherwise → check if the user is in **any** of `specialist.required_groups`.

Groups are read from `user.groups.values_list("name", flat=True)`.

This is **specialist-level** RBAC — finer-grained than view-level checks because the same `POST /api/ask/` endpoint handles all specialists.

---

## Delegation ([`nexus/delegation.py`](../nexus/delegation.py))

`delegate(from_specialist, to_specialist, question, user_id, summary, ...)` allows one specialist to ask another for a scoped answer mid-response.

### How it works

```python
# Called by AtlasAgent._synthesize():
vega_resp = self.delegate("Vega", "Analyze the revenue trend relevant to: ...", context, summary="...")
nova_resp = self.delegate("Nova", "What is the current cash position relevant to: ...", context, summary="...")
```

1. Checks delegation depth — refuses if `_current_depth >= max_depth` (default: 2).
2. Looks up the target specialist in the registry.
3. Builds a **scoped** `EchoContext`:
   - `turns = []` — delegates do NOT see the full conversation.
   - `facts` — relevant facts from Echo for the delegated question.
   - `summary` — handoff context from the caller.
   - `stream = False` — delegates always return complete text for synthesis.
   - `_delegation_depth += 1`
4. Emits `delegation_started` event via `event_sink` (for real-time SSE).
5. Calls `target.handle(question, context)`.
6. Emits `delegation_completed` (or `delegation_failed`) event.
7. Writes the delegation exchange to Echo as an audit turn.
8. Returns `SpecialistResponse | None`.

### Depth limit
| Scenario | Depth |
|---|---|
| User → Atlas (solo) | 0 |
| User → Atlas → Vega | 1 |
| User → Atlas → Vega → Nova | 2 |
| User → Atlas → Vega → Nova → X | Refused (depth 2 reached) |

---

## SSE Event Sink

The `event_sink` parameter in both `route_query()` and `delegate()` is a callback:

```python
event_sink("delegation_started", {"from": "Atlas", "to": "Vega", "activity": "Analyzing trends..."})
event_sink("delegation_completed", {"from": "Atlas", "to": "Vega"})
event_sink("delegation_failed", {"from": "Atlas", "to": "Vega", "reason": "..."})
```

The view in `agents/views.py` sets up the `event_sink` to push events into the SSE stream **before** streaming the final answer. The frontend `DelegationTimeline` component listens for these events and renders the live handoff animation.

---

## Data Classes ([`nexus/base.py`](../nexus/base.py))

### `EchoContext`
Passed into every `specialist.handle()` call.

```python
@dataclass
class EchoContext:
    user_id: int | None
    specialist_name: str
    turns: list[dict]              # Recent conversation turns from Echo
    facts: list[dict]              # Relevant MemoryFacts from Echo
    summary: str | None            # Handoff summary (delegation only)
    event_sink: Any                # SSE callback (delegation events)
    companion_mode: bool           # True = Atlas uses "Ava" persona
    response_style: str            # "concise" (chat) | "voice"
    stream: bool                   # True for main responses; False for delegates
    _delegation_depth: int         # Internal counter — do not set manually
    _max_delegation_depth: int     # Default: 2
```

### `SpecialistResponse`
Returned by every `specialist.handle()`.

```python
@dataclass
class SpecialistResponse:
    agent: str
    analysis: str | Generator      # Main answer; Generator in stream mode
    recommendation: str            # One-line follow-up suggestion
    data: dict                     # Optional structured data (chart, vendor list, etc.)
    contributors: list[str]        # Populated by Atlas during synthesis
```

`to_dict()` serializes to a JSON-safe dict. `analysis` is intentionally left as a generator when streaming — the view iterates over it to produce SSE chunks.
