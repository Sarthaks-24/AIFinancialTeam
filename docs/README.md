# AI Financial Workforce — Documentation

Welcome to the developer documentation for **AI Financial Workforce**, an intelligent multi-agent platform built on top of a Django + React foundation. If you're new here, start with the guides in the order listed below.

---

## 📚 Table of Contents

| Guide | What You'll Learn |
|---|---|
| [01 — Project Overview](./01-project-overview.md) | What this system is, the vision, and the current state |
| [02 — Architecture](./02-architecture.md) | How the three layers (Nexus, Echo, Specialists) fit together |
| [03 — Getting Started](./03-getting-started.md) | Local dev setup: backend, database, frontend, env vars |
| [04 — API Reference](./04-api-reference.md) | All REST endpoints, request/response shapes, auth |
| [05 — Specialists](./05-specialists.md) | Each AI specialist: domain, persona, permissions, data |
| [06 — Echo Memory](./06-echo-memory.md) | How conversation memory and MemoryFacts work |
| [07 — Nexus Orchestration](./07-nexus-orchestration.md) | Routing, delegation, permissions, registry |
| [08 — Voice Pipeline](./08-voice-pipeline.md) | STT → Specialist → TTS round-trip |
| [09 — Frontend Guide](./09-frontend-guide.md) | React app structure, chat flow, companion UI |
| [10 — Data Models](./10-data-models.md) | All Django models documented with field-level detail |
| [11 — Roadmap](./11-roadmap.md) | Phase 0–5 plan, what's built vs. what's next |

---

## Quick Reference

```
ai-financial-team-working/
├── agents/          # Django app: models, views, API endpoints, auth
├── backend/         # Django project settings, URLs, WSGI/ASGI
├── echo/            # Shared memory engine (conversations, turns, facts)
├── nexus/           # Orchestration: registry, router, delegation, permissions
│   └── specialists/ # All six AI specialist implementations
├── voice/           # STT + TTS pipeline
├── frontend/        # React + Vite application
└── docs/            # ← You are here
```

> **New developer?** Start with [01 — Project Overview](./01-project-overview.md), then [03 — Getting Started](./03-getting-started.md) to get your local environment running.
