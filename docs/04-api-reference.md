# 04 — API Reference

All endpoints are prefixed with `/api/`. Authentication is JWT Bearer unless noted.

**Base URL (dev):** `http://127.0.0.1:8000/api/`

---

## Authentication

### `POST /api/token/`
Obtain a JWT access + refresh token pair.

**No auth required.**

**Request body:**
```json
{ "username": "user@example.com", "password": "secret" }
```

**Response:**
```json
{
  "access": "<JWT access token>",
  "refresh": "<JWT refresh token>"
}
```

The access token payload includes a `groups` array (e.g., `["CFO"]`) injected by the custom serializer in `agents/auth.py`. The frontend uses this to determine which specialists and routes are visible.

### `POST /api/token/refresh/`
Refresh an expired access token.

**Request body:** `{ "refresh": "<refresh_token>" }`

---

## Chat

### `POST /api/ask/`
Main endpoint for text-based queries. Returns a **Server-Sent Events (SSE)** stream.

**Auth required:** Yes (IsAuthenticated)

**Request body:**
```json
{
  "question": "Why are collections falling?",
  "specialist": "Atlas",          // optional — Nexus classifies if omitted
  "conversation_id": 42,          // optional — loads/continues a session
  "companion_mode": false         // optional — enables Ava persona on Atlas
}
```

**Response (SSE stream):**
```
event: metadata
data: {"agent": "Atlas", "conversation_id": 42, "contributors": ["Vega", "Nova"]}

event: chunk
data: {"text": "Revenue declined 12% month-over-month..."}

event: chunk
data: {"text": " Cash collections dropped following..."}

event: end
data: {}
```

**Delegation events** (emitted when Atlas delegates):
```
event: delegation_started
data: {"from": "Atlas", "to": "Vega", "activity": "Analyzing trends..."}

event: delegation_completed
data: {"from": "Atlas", "to": "Vega"}
```

---

### `POST /api/voice/ask/`
Submit audio for STT → specialist → TTS processing.

**Auth required:** Yes (IsAuthenticated)

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `audio` | file | Yes | Audio file (WebM, WAV, OGG, etc.) |
| `mime_type` | string | No | MIME type of audio (default: `audio/webm`) |
| `specialist` | string | No | Target specialist (default: `Nova`) |
| `voice_id` | string | No | Google TTS voice ID override |

**Response:**
```json
{
  "transcript": "What is our cash position this month?",
  "result": {
    "agent": "Nova",
    "analysis": "Cash position is INR 12,45,000 as of October...",
    "recommendation": "Liquidity is healthy. No immediate action needed."
  },
  "specialist": "Nova",
  "audio_base64": "<base64-encoded WAV>",  // null if server TTS disabled
  "audio_mime": "audio/wav",
  "tts_fallback": false,   // true = client should use browser TTS
  "tts_error": null
}
```

---

## Specialists

### `GET /api/specialists/`
List all registered specialists the authenticated user can access.

**Auth required:** Yes (IsAuthenticated)

**Response:**
```json
[
  {
    "name": "Atlas",
    "title": "AI Chief of Staff",
    "domain": "executive_intelligence",
    "description": "Executive summaries, business health, and KPI narration.",
    "voice_enabled": true,
    "suggested_prompts": [
      "Give me an executive financial summary.",
      "Why are collections falling?",
      "How is the business performing this month?"
    ]
  },
  ...
]
```

---

## Conversations (Echo History)

### `GET /api/conversations/`
List the authenticated user's active (non-archived) conversations, newest first.

### `POST /api/conversations/`
Create a new conversation session.

**Request body:**
```json
{ "title": "Q3 Cash Review" }  // optional title
```

**Response:** `{ "id": 42, "title": "Q3 Cash Review", "started_at": "...", "last_active_at": "..." }`

### `GET /api/conversations/<id>/`
Retrieve a conversation and its turns.

**Response:**
```json
{
  "id": 42,
  "title": "Q3 Cash Review",
  "turns": [
    { "role": "user", "specialist_name": "Nova", "content": "What is our cash position?", "created_at": "..." },
    { "role": "specialist", "specialist_name": "Nova", "content": "Cash is INR 12,45,000...", "created_at": "..." }
  ]
}
```

### `POST /api/conversations/<id>/archive/`
Archive a conversation (removes it from the active list).

---

## Dashboard & KPIs

### `GET /api/dashboard/`
Returns summary KPI cards and recent activity for the authenticated user's organization.

### `GET /api/kpis/`
Returns structured KPI data (revenue, expenses, EBITDA, cash position) for chart rendering.

### `GET /api/financial-data/`
Returns all financial metric rows for the user's organization.

### `GET /api/financial-data/months/`
Returns the list of available months for the organization.

---

## Finance Uploads

### `POST /api/upload/`
Upload a CSV or XLSX file containing financial metrics.

**Auth required:** Yes  
**Content-Type:** `multipart/form-data`  
**Field:** `file` — the CSV/XLSX file

Columns expected: `month`, `revenue`, `expenses`, `ebitda`, `cash_position`, `budget`

---

## Reports & Tasks

### `GET /api/reports/`
List AI-generated reports for the user's organization.

### `GET /api/tasks/`
List tasks for the user's organization.

### `POST /api/tasks/update/`
Update the status of a task.

**Request body:** `{ "task_id": 1, "status": "Completed" }`

---

## History (Legacy)

### `GET /api/query-history/`
Returns recent `QueryLog` entries. **Legacy** — will be superseded by the conversations API.

---

## Error Responses

All endpoints return standard DRF error shapes:

```json
{ "detail": "Authentication credentials were not provided." }
```

or validation errors:

```json
{ "question": ["This field is required."] }
```

Specialist-level errors (permission denied, no data, Gemini failure) are returned inside the normal response shape:

```json
{
  "agent": "Atlas",
  "analysis": "You do not have permission to use this specialist.",
  "recommendation": "Contact an admin if you need access."
}
```
