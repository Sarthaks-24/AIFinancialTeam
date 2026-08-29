# 01 — Project Overview

## What Is This?

**AI Financial Workforce** is a multi-agent AI platform for enterprise finance and operations teams. Instead of a single chatbot, it provides a *coordinated workforce* of six specialized AI agents, each with a distinct domain, persona, and data scope.

The codebase started as a simpler "AI Financial Team" finance copilot (Django + React + stateless Gemini calls) and is being evolved into the full AI Financial Team workforce described in the product proposal.

---

## The Vision: Six AI Specialists

| Specialist | Title | Domain |
|---|---|---|
| **Atlas** | AI Chief of Staff | Executive summaries, KPI narration, cross-functional synthesis |
| **Vega** | AI Data Analyst | Trend analysis, comparisons, charts, data-driven explanations |
| **Nova** | AI Financial Advisor | Cash flow, treasury, payments, collections, liquidity |
| **Aria** | AI Operations Manager | Procurement, vendors, contracts, approvals |
| **Orion** | AI Compliance Officer | Audit, policy, governance, risk |
| **Luna** | AI Product Specialist | Onboarding, product knowledge, troubleshooting |

Users can talk directly to any specialist, or ask Atlas (or the **Ava** companion) a cross-functional question and have multiple specialists collaborate in real time.

---

## The Three Core Layers

```
┌─────────────────────────────────────────────────┐
│  Nexus — Orchestration Layer                    │
│  Routes queries → dispatches specialists        │
│  Enforces permissions, handles delegation       │
├─────────────────────────────────────────────────┤
│  Six Specialists (Atlas, Vega, Nova, Aria,      │
│  Orion, Luna) — each a BaseSpecialist subclass  │
│  Gathers domain data → calls Gemini → responds  │
├─────────────────────────────────────────────────┤
│  Echo — Shared Memory Engine                    │
│  Persists Conversations, Turns, MemoryFacts     │
│  Specialists read prior context before calling  │
│  Gemini, enabling genuine follow-up questions   │
└─────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| Web framework | Django 6 + Django REST Framework |
| Authentication | JWT via `djangorestframework-simplejwt` |
| Database | PostgreSQL |
| AI / LLM | Google Gemini (`google-genai` SDK) |
| Voice STT | Google Gemini (multimodal audio) |
| Voice TTS | Google Cloud Text-to-Speech |
| Async streaming | Django `StreamingHttpResponse` |
| API schema | `drf-spectacular` (OpenAPI) |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 18 + Vite |
| UI library | MUI (Material UI) |
| State | React Context API |
| HTTP client | `fetch` + custom streaming SSE parser |
| Styling | MUI theme + inline `sx` props |

---

## Current Status (as of Phase 3 / early Phase 5)

### What is fully built ✅
- **All six specialists** registered in Nexus (`AtlasAgent`, `VegaAgent`, `NovaAgent`, `AriaAgent`, `OrionAgent`, `LunaAgent`)
- **Echo memory** — `Conversation`, `Turn`, `MemoryFact` models; `get_context()` / `write_turn()` / `get_relevant_facts()` service functions
- **Nexus routing** — classify-then-dispatch via registry; no hardcoded if/elif
- **Delegation** — Atlas → Vega + Nova → Atlas synthesis with real-time SSE delegation events
- **Voice pipeline** — STT (Gemini multimodal) → Nova → TTS (Google Cloud or browser fallback)
- **JWT auth** with custom `groups` claim; role-based API and specialist access
- **Companion mode ("Ava")** — Atlas wraps with a warm human persona when `companion_mode=true`
- **Conversation history** — persistent sessions, archiving, history drawer in UI
- **Frontend chat** — streaming responses, delegation timeline, expert panel, presence indicator

### What is partial or deferred ⚠️
- **Orion** and **Luna** have minimal real data (stubs respond based on `ComplianceRecord` / `PolicyDocument` models but those need population)
- **Vector/embedding retrieval** in Echo is partially implemented; cosine similarity used for `MemoryFact` retrieval but embeddings must be pre-generated at `write_fact()` time
- **Proactive AI** (Phase 4 goal) — not started
- **Multi-tenancy hardening** (Phase 4) — scoping exists via `Organization` FK but not fully hardened across all endpoints

---

## Key Design Decisions

1. **`BaseSpecialist` ABC** — Every specialist implements a single `handle(question, context) -> SpecialistResponse` method. Nexus calls this; specialists never call each other directly (they use `self.delegate()`).
2. **Echo is always-on** — Context is loaded before every Gemini call, enabling follow-up questions across sessions.
3. **Delegation depth cap** — Max 2 hops (Atlas → Vega is depth 1; Atlas → Vega → Nova is depth 2) to prevent infinite loops.
4. **Streaming first** — All main chat responses stream via SSE. Delegated sub-calls are non-streaming (they return complete text for synthesis).
5. **Companion mode is additive** — `companion_mode=true` changes Atlas's persona to "Ava" but does not change any data retrieval or delegation logic.
