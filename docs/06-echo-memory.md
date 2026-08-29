# 06 — Echo Memory Engine

Echo is the **shared memory layer** of AI Financial Team. It persists every conversation turn and specialist-extracted facts so that specialists can provide genuine follow-up answers without the user re-explaining context.

---

## Models ([`echo/models.py`](../echo/models.py))

### `Conversation`
Represents a user-owned chat session. A user can have many conversations.

| Field | Type | Description |
|---|---|---|
| `user` | FK → User | Owner of the conversation |
| `organization` | FK → Organization | Tenant scoping |
| `specialist` | CharField | Legacy: originating specialist (blank for new sessions) |
| `title` | CharField | Auto-set from the first user message (max 80 chars) |
| `started_at` | DateTimeField | Auto-set on creation |
| `last_active_at` | DateTimeField | Auto-updated on every interaction |
| `archived_at` | DateTimeField (nullable) | Set when the user archives the conversation |

### `Turn`
A single message in a conversation (either user or specialist).

| Field | Type | Description |
|---|---|---|
| `conversation` | FK → Conversation | Parent session |
| `organization` | FK → Organization | Tenant scoping |
| `role` | CharField | `"user"` or `"specialist"` |
| `specialist_name` | CharField | Which specialist spoke (allows multi-specialist sessions) |
| `content` | TextField | Message content |
| `created_at` | DateTimeField | Timestamp (ordered ascending) |

### `MemoryFact`
A structured key-value fact extracted or written programmatically.

| Field | Type | Description |
|---|---|---|
| `user` | FK → User | Owner |
| `organization` | FK → Organization | Tenant scoping |
| `category` | CharField | `preference`, `org_context`, or `prior_finding` |
| `key` | CharField | Fact name (e.g., `"preferred_currency"`) |
| `value` | TextField | Fact value (e.g., `"INR"`) |
| `source_turn` | FK → Turn (nullable) | The turn that produced this fact |
| `created_at` | DateTimeField | Auto-set |
| `expires_at` | DateTimeField (nullable) | Auto-expiry; null = never expires |
| `embedding` | JSONField (nullable) | Vector embedding for semantic retrieval |

---

## Service Functions ([`echo/service.py`](../echo/service.py))

### Context Retrieval

#### `get_context(user_id, specialist_name, limit=10, conversation_id=None) -> list[dict]`
Returns the last `limit` turns from the user's active conversation with the given specialist (or from a specific `conversation_id`).

Each turn dict:
```python
{
    "role": "user" | "specialist",
    "specialist_name": "Nova",
    "content": "...",
    "created_at": "2026-08-17T10:00:00+00:00"
}
```

Called by `nexus/router.py` before every `specialist.handle()` call.

#### `get_relevant_facts(user_id, query, limit=5) -> list[dict]`
Retrieves up to `limit` `MemoryFact` records relevant to `query`.

**Retrieval strategy (current):**
1. Try to generate an embedding for `query` using Gemini `text-embedding-004`.
2. If successful, compute cosine similarity against all stored fact embeddings and return facts with similarity > 0.5.
3. If embedding fails (API error, etc.), fall back to simple keyword matching.
4. If no strong match either way, return the most recent facts.

#### `get_last_specialist(user_id) -> str | None`
Returns the specialist from the user's most recently active conversation. Used for follow-up detection in the router.

---

### Writing

#### `write_turn(user_id, specialist_name, role, content, conversation_id=None) -> Turn | None`
Persists a single turn. If `conversation_id` is provided, writes to that specific session; otherwise, finds or creates the user's conversation with that specialist.

Auto-sets the conversation title from the first user message if the title is blank.

#### `write_fact(user_id, category, key, value, source_turn_id=None, expires_at=None) -> MemoryFact | None`
Persists a `MemoryFact` and generates its embedding via Gemini at write time.

---

### Conversation Management

| Function | Description |
|---|---|
| `create_conversation(user_id, title="")` | Create a new explicit session |
| `get_conversation(user_id, conversation_id, include_archived=False)` | Fetch a specific session |
| `archive_conversation(user_id, conversation_id)` | Set `archived_at` timestamp |
| `get_or_create_conversation(user_id, specialist_name)` | Legacy: find or create the most recent session for a specialist |

---

## How Echo Fits into a Request

```
1. route_query() called with user, question, conversation_id
          |
          ▼
2. turns  = echo.get_context(user_id, specialist.name, conversation_id=...)
   facts  = echo.get_relevant_facts(user_id, question)
          |
          ▼
3. EchoContext(turns=turns, facts=facts, ...) built and passed to specialist
          |
          ▼
4. specialist.handle() calls context.format_for_prompt()
   → builds a string block:
     "Known facts:\n- [preference] preferred_currency: INR\n\nRecent conversation:\nUser: ...\nNova: ..."
          |
          ▼
5. This string is injected into the Gemini prompt as "Prior conversation"
          |
          ▼
6. After response: echo.write_turn(user_id, specialist, "specialist", response_text)
```

---

## `EchoContext.format_for_prompt()`

The `EchoContext.format_for_prompt()` method in [`nexus/base.py`](../nexus/base.py) formats the context for Gemini:

- **Handoff summary** (for delegated calls from Atlas) — shown first.
- **Known facts** — formatted as `[category] key: value` bullet lines.
- **Recent conversation** — last 6 turns, truncated to 400 chars each. Role labels: `"User"` or the specialist's name.

---

## Delegation and Echo

When Atlas delegates to Vega or Nova:
- The delegated `EchoContext` has **empty `turns`** (scoped context only, not the full conversation).
- Only `facts` are passed through (relevant to the delegated question).
- The delegation exchange is written to Echo after the call:
  ```python
  echo.write_turn(user_id, target.name, "specialist",
                  f"[Delegated by Atlas] {response.analysis[:300]}")
  ```
  This provides an audit trail but does not expose the internal delegation to the user's visible history.

---

## Future: Embeddings & Vector Store

The `embedding` field on `MemoryFact` is pre-positioned for a full vector store (Phase 4). Currently:
- Embeddings are generated at `write_fact()` time using `text-embedding-004`.
- Retrieval uses in-process cosine similarity (no external vector DB).
- Phase 4 will migrate this to a proper vector store (e.g., pgvector) for scale.
