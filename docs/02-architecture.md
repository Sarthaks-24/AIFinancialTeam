# 02 — Architecture

## High-Level System Diagram

```
Browser (React + Vite)
        │
        │  HTTPS / SSE streaming
        ▼
Django REST API  (agents/views.py)
        │
        │  POST /api/ask/         (text chat)
        │  POST /api/voice/ask/   (voice)
        ▼
┌───────────────────────────────────────────────────────┐
│  Nexus — Orchestration Layer                          │
│                                                       │
│  nexus/router.py ──► classify_specialist()            │
│                      │                               │
│                      ▼                               │
│  nexus/registry.py ──► get_specialist(name)           │
│                      │                               │
│                      ▼                               │
│  nexus/permissions.py ──► user_can_access()           │
│                      │                               │
│                      ▼                               │
│  Echo context load (echo/service.py)                 │
│  get_context() + get_relevant_facts()                │
│                      │                               │
│                      ▼                               │
│  specialist.handle(question, EchoContext)            │
│         │                                            │
│         │  (Atlas only, cross-functional questions)  │
│         ▼                                            │
│  nexus/delegation.py ──► delegate(to="Vega"/"Nova")  │
│                                                       │
└───────────────────────────────────────────────────────┘
        │
        ▼
Echo — Write turn (echo/service.py)
Google Gemini (agents/services/ai_service.py)
        │
        ▼
StreamingHttpResponse / JSON response
```

---

## Directory Layout

```
ai-financial-team-working/
│
├── manage.py                    # Django management entry point
├── requirements.txt             # Python dependencies
├── .env / .env.example          # Backend environment variables
│
├── backend/                     # Django project package
│   ├── settings.py              # All settings (env-aware, no hardcoded secrets)
│   ├── urls.py                  # Root URL dispatcher
│   └── asgi.py / wsgi.py
│
├── agents/                      # Core Django app
│   ├── models.py                # Organization, FinancialMetric, Task, Report,
│   │                            #   FinancialUpload, Vendor, Contract,
│   │                            #   ComplianceRecord, PolicyDocument, QueryLog
│   ├── views.py                 # All API view functions
│   ├── urls.py                  # API URL patterns
│   ├── serializers.py           # DRF serializers
│   ├── auth.py                  # Custom JWT serializer (injects 'groups')
│   ├── permissions.py           # Custom DRF permission classes
│   └── services/
│       ├── ai_service.py        # ask_gemini(), ask_specialist(), ask_synthesis()
│       ├── dashboard_service.py # Dashboard KPI aggregation
│       ├── reporting_agent.py   # Report generation logic
│       ├── treasury_agent.py    # Cash/treasury analysis (used by Nova)
│       ├── fpna_agent.py        # FP&A analysis (used by Nova/Atlas)
│       ├── budget_agent.py      # Budget analysis
│       ├── financial_health_agent.py
│       ├── kpi_service.py
│       └── ...
│
├── echo/                        # Shared memory engine
│   ├── models.py                # Conversation, Turn, MemoryFact
│   └── service.py               # get_context(), write_turn(), get_relevant_facts(),
│                                #   write_fact(), create_conversation(), etc.
│
├── nexus/                       # Orchestration layer
│   ├── base.py                  # EchoContext, SpecialistResponse (data classes)
│   ├── specialist.py            # BaseSpecialist ABC
│   ├── registry.py              # @register_specialist decorator + get/list functions
│   ├── router.py                # route_query() — main entry point for all queries
│   ├── delegation.py            # delegate() — cross-specialist handoffs
│   ├── permissions.py           # user_can_access() — specialist-level RBAC
│   └── specialists/
│       ├── __init__.py          # Imports workforce and reconciliation to trigger registration
│       ├── classify.py          # classify_specialist(), is_follow_up(), has_explicit_intent()
│       ├── workforce.py         # Six general-purpose specialists (Atlas, Vega, Nova, Aria, Orion, Luna)
│       └── reconciliation.py    # Ledger specialist (Reconciliation Controller)
│
├── voice/                       # Voice pipeline
│   ├── service.py               # ask_with_voice() — full STT→specialist→TTS orchestration
│   ├── stt.py                   # speech_to_text() via Gemini multimodal
│   └── tts.py                   # text_to_speech() via Google Cloud TTS
│
└── frontend/                    # React + Vite SPA
    ├── src/
    │   ├── App.jsx              # Root component + routing
    │   ├── main.jsx             # Entry point
    │   ├── api/                 # API client functions (chatApi.js, etc.)
    │   ├── context/             # ChatContext, AuthContext
    │   ├── components/
    │   │   ├── chat/            # AssistantPresence, ExpertTeamPanel,
    │   │   │                    #   DelegationTimeline, ConversationHistoryDrawer,
    │   │   │                    #   AgentOrb
    │   │   ├── dashboard/       # Dashboard widgets
    │   │   ├── Navbar/
    │   │   └── Sidebar/
    │   ├── pages/
    │   │   ├── Chat/            # Main chat page
    │   │   ├── Dashboard/
    │   │   ├── FinanceData/
    │   │   ├── KPI/
    │   │   ├── Reports/
    │   │   ├── Tasks/
    │   │   └── Login/
    │   └── theme/               # MUI theme configuration
    ├── index.html
    └── vite.config.js
```

---

## Request Lifecycle — Text Chat

1. **User types** a question in `Chat/index.jsx`.
2. Frontend calls `askAgentStream(question, specialist, conversationId, companionMode)` from `api/chatApi.js`.
3. `POST /api/ask/` hits `ask_agent` view in `agents/views.py`.
4. View calls `route_query(question, user, specialist_name, stream=True, ...)` in `nexus/router.py`.
5. Router:
   - Classifies the specialist (or uses the explicitly selected one).
   - Checks `user_can_access()`.
   - Loads Echo context (`get_context()` + `get_relevant_facts()`).
   - Writes user turn to Echo.
   - Calls `specialist.handle(question, EchoContext)`.
6. Specialist gathers domain data from Django ORM, builds a data-context string, calls `ask_specialist()` (or `ask_synthesis()` for Atlas delegation).
7. `ask_specialist()` sends the composed prompt to Gemini and returns a **streaming generator**.
8. `SpecialistResponse` wraps the streaming generator in the `analysis` field.
9. View serializes the response as Server-Sent Events:
   - `event: metadata` — agent name, conversation_id, contributors
   - `event: chunk` — each text chunk from the generator
   - `event: end` — signals completion
10. Frontend receives the SSE stream, appends chunks to the message, renders delegation events in `DelegationTimeline`.

---

## Request Lifecycle — Voice

1. Frontend records audio blob and posts to `POST /api/voice/ask/`.
2. `voice_ask` view passes audio bytes to `voice.service.ask_with_voice()`.
3. `ask_with_voice()` calls `speech_to_text()` → gets transcript string.
4. Builds `EchoContext` with `response_style="voice"`.
5. Calls `specialist.handle(transcript, context)` (Nova by default).
6. Calls `text_to_speech()` (Google Cloud TTS or browser-TTS fallback).
7. Returns JSON with `transcript`, `result` (SpecialistResponse dict), `audio_base64`.

---

## Authentication Flow

```
POST /api/token/  →  CustomTokenObtainPairSerializer
                      ↓
                    Injects user.groups into JWT payload
                      ↓
                    Returns { access, refresh }

All protected endpoints:
    Authorization: Bearer <access_token>
    ↓
    JWTAuthentication validates token
    ↓
    IsAuthenticated + optional custom permission class
```

User groups driving access:
- `CFO` — full access to all specialists
- `Finance Manager` — access to Atlas, Vega, Nova, Aria, Orion
- `Auditor` — access to Orion only
- `Admin` — full access (bypasses specialist group checks)
