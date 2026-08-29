# 11 — Roadmap

This document maps the project's phase plan to the current implementation state.

---

## Phase 0 — Stabilize ✅ Complete

| Task | Status |
|---|---|
| Close 4 unauthenticated endpoints | ✅ Done |
| Fix JWT `groups` claim (custom serializer) | ✅ Done |
| Set `ALLOWED_HOSTS` from env | ✅ Done |
| Replace `print()` with `logging` | ✅ Done |
| Move frontend API URL to Vite env var | ✅ Done |
| Remove dead code (unused `Agent` model, empty components) | ✅ Done |
| Agree branch/PR workflow | ⚠️ Not tracked here |

---

## Phase 1 — Foundation ✅ Complete

### Echo — Shared Memory Engine ✅
- `Conversation`, `Turn`, `MemoryFact` models in `echo/models.py`
- `get_context()`, `write_turn()`, `get_relevant_facts()`, `write_fact()` in `echo/service.py`
- Echo is read before every Gemini call (enables follow-up questions)
- Embedding-based fact retrieval using `text-embedding-004`

### Nexus — Orchestration Skeleton ✅
- `BaseSpecialist` ABC in `nexus/specialist.py`
- `@register_specialist` decorator + registry in `nexus/registry.py`
- `EchoContext`, `SpecialistResponse` data classes in `nexus/base.py`
- `route_query()` dispatches via registry (no hardcoded if/elif)
- `nexus/permissions.py` — specialist-level RBAC
- LLM-based classification in `nexus/specialists/classify.py`

### Voice Pipeline ✅
- `voice/stt.py` — Gemini multimodal STT
- `voice/tts.py` — Google Cloud TTS + browser fallback
- `voice/service.py` — `ask_with_voice()` orchestration
- `POST /api/voice/ask/` endpoint

---

## Phase 2 — Core Assistants ✅ Complete

All six specialists implemented in `nexus/specialists/workforce.py`:

| Specialist | Status | Data Sources |
|---|---|---|
| Nova (Financial Advisor) | ✅ Full | FinancialMetric |
| Atlas (Chief of Staff) | ✅ Full + synthesis | FinancialMetric |
| Vega (Data Analyst) | ✅ Full + chart output | FinancialMetric |
| Aria (Operations Manager) | ✅ Full | Vendor, Contract |
| Orion (Compliance Officer) | ✅ Full | ComplianceRecord, PolicyDocument |
| Luna (Product Specialist) | ✅ Built-in knowledge | None (embedded knowledge) |

All six:
- Implement `BaseSpecialist`
- Are registered in Nexus via `@register_specialist`
- Read Echo context before Gemini calls
- Support both text and voice (`response_style`)
- Have fallback responses when Gemini fails or data is absent

---

## Phase 3 — Collaboration ✅ Complete

| Feature | Status |
|---|---|
| Atlas → Vega + Nova delegation | ✅ Done |
| `nexus/delegation.py` delegation engine | ✅ Done |
| Depth-limited delegation (max 2 hops) | ✅ Done |
| Scoped context transfer (not full conversation) | ✅ Done |
| Real-time SSE delegation events (`delegation_started`, `delegation_completed`, `delegation_failed`) | ✅ Done |
| `ask_synthesis()` for Atlas multi-specialist synthesis | ✅ Done |
| `contributors` list in response | ✅ Done |

---

## Phase 4 — Optimization ⚠️ Partial

| Feature | Status |
|---|---|
| Echo embeddings retrieval | ✅ Implemented (in-process cosine similarity) |
| Streaming responses | ✅ Done (SSE streaming) |
| Full vector store (pgvector) | ❌ Not started — Phase 4 goal |
| Proactive AI surfacing | ❌ Not started |
| Expand Orion/Aria data (document ingestion) | ⚠️ Models exist; no ingestion pipeline |
| Multi-tenancy hardening | ⚠️ `Organization` FK scoping exists; not fully audited |

---

## Phase 5 — Human Companion Experience ✅ Core Complete

| Feature | Status |
|---|---|
| `AssistantPresence` component (Ava avatar/face) | ✅ Built |
| `ExpertTeamPanel` (specialist list + direct access) | ✅ Built |
| `companion_mode` flag on `POST /api/ask/` | ✅ Built |
| Atlas → Ava persona in companion mode | ✅ Built |
| `VITE_COMPANION_EXPERIENCE` feature flag | ✅ Built |
| `ConversationHistoryDrawer` (session list) | ✅ Built |
| Persistent chat sessions (Conversation model + API) | ✅ Built |
| `conversation_id` threading in API | ✅ Built |
| `DelegationTimeline` (real-time handoff UI) | ✅ Built |
| Voice + presence state (listening/thinking/speaking) | ✅ Built |
| Companion-specific synthesis rules in `ai_service.py` | ✅ Built |
| Pilot gating + metrics | ❌ Not started |

---

## What's Left / What's Next

### Near-term
1. **Populate Orion and Aria data** — add `ComplianceRecord`, `PolicyDocument`, `Vendor`, `Contract` records via Admin or a data import script. Until then, these specialists return "no data" responses.
2. **Luna knowledge base** — replace the embedded knowledge strings in `workforce.py` with a proper retrieval-augmented approach (document store, chunking, embedding search).
3. **Write tests** — `nexus/tests/` directory exists but has minimal coverage. Priority: `route_query()` unit tests, delegation depth tests, Echo write/read round-trip.
4. **PR workflow** — document and enforce branching strategy.

### Medium-term (Phase 4 goals)
1. **pgvector** — migrate `MemoryFact.embedding` retrieval from in-process cosine similarity to a proper vector DB for scale.
2. **Proactive insights** — scheduled jobs that detect anomalies in financial data and surface them without the user asking.
3. **Document ingestion pipeline** — file upload → chunking → embedding storage → Orion/Aria can answer questions about uploaded policy PDFs and contracts.

### Long-term
1. **Model selection per specialist** — `BaseSpecialist.model` is a stub; route different specialists to different LLMs (e.g., a cheaper model for Luna, a reasoning model for Orion).
2. **Usage analytics** — track which specialists are used most, handoff success rates, latency.
3. **Deeper delegation** — currently only Atlas initiates delegation. Future: any specialist can delegate.

---

## Definition of Done

The AI Financial Workforce is complete when:

- [x] Six specialists, each with distinct domain and persona
- [x] Nexus routes, enforces permissions, transfers scoped context
- [x] Echo persists turns and facts; specialists use prior context
- [x] Voice — full STT → Nova → TTS path working
- [x] Collaboration — Atlas → Vega → Nova synthesis working
- [x] Security — no unauthenticated sensitive endpoints; JWT roles drive access
- [ ] Data — Aria/Orion have real domain data beyond stubs
- [ ] Proactive — at least one proactive insight path (Phase 4)
