# 09 — Frontend Guide

The frontend is a **React 18 + Vite** single-page application using **MUI (Material UI)** for components and a custom theme.

---

## Directory Structure

```
frontend/
├── .env / .env.example        # VITE_API_BASE_URL, VITE_COMPANION_EXPERIENCE
├── index.html
├── vite.config.js
├── package.json
└── src/
    ├── main.jsx               # Entry point — mounts <App />
    ├── App.jsx                # Router + AuthContext provider
    │
    ├── api/                   # API client layer
    │   └── chatApi.js         # askAgentStream(), voiceAsk(), fetchSpecialists(), etc.
    │
    ├── context/
    │   ├── AuthContext.jsx    # JWT token storage, login/logout, hasRole()
    │   └── ChatContext.jsx    # Active conversation, messages, active specialist
    │
    ├── theme/                 # MUI theme configuration (colors, typography, etc.)
    │
    ├── layout/                # App shell (sidebar + navbar wrapper)
    │
    ├── components/
    │   ├── chat/
    │   │   ├── AssistantPresence.jsx      # Companion face/avatar + voice controls
    │   │   ├── ExpertTeamPanel.jsx        # Specialist list + "Ask directly" actions
    │   │   ├── DelegationTimeline.jsx     # Live handoff animation during Atlas synthesis
    │   │   ├── ConversationHistoryDrawer.jsx  # History panel (sessions list)
    │   │   └── AgentOrb.jsx               # Animated orb for specialist visuals
    │   ├── dashboard/         # Dashboard widget components
    │   ├── Common/            # Shared UI primitives
    │   ├── Navbar/
    │   └── Sidebar/
    │
    └── pages/
        ├── Chat/              # Main conversation page
        ├── Dashboard/         # KPI dashboard
        ├── FinanceData/       # Financial data upload + table
        ├── KPI/               # KPI detail page
        ├── Reports/           # Generated reports
        ├── Tasks/             # Task list
        ├── History/           # Legacy query history
        ├── Settings/
        └── Login/
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api` | Backend API base URL |
| `VITE_COMPANION_EXPERIENCE` | `false` | Set to `true` to show Ava companion UI |

Set these in `frontend/.env`.

---

## Authentication (`AuthContext`)

- Stores JWT `access` and `refresh` tokens in `localStorage`.
- `login(username, password)` — calls `POST /api/token/`, stores tokens, decodes JWT payload to extract `username`, `groups`, and `user_id`.
- `logout()` — clears tokens and redirects to login.
- `hasRole(role)` — checks if the decoded JWT payload `groups` array contains the given role string.
- The Axios/fetch client in `chatApi.js` automatically attaches `Authorization: Bearer <token>` to all requests.

---

## Chat Flow (`pages/Chat/`)

### Sending a text message

1. User types in the input box and presses Enter / Send.
2. `handleSend()` calls `askAgentStream(question, selectedSpecialist, conversationId, companionMode)` from `chatApi.js`.
3. `askAgentStream()` opens an SSE fetch stream to `POST /api/ask/`.
4. As chunks arrive:
   - `event: metadata` → sets `agent`, `conversation_id`, `contributors` on the message.
   - `event: delegation_started` / `delegation_completed` → updates `DelegationTimeline` state.
   - `event: chunk` → appends `text` to the in-progress message.
   - `event: end` → marks the message as complete.
5. The streaming message is rendered in real time as chunks arrive.

### Specialist selection
- If `VITE_COMPANION_EXPERIENCE=false`: a specialist dropdown/tabs selector is shown in the chat header.
- If `VITE_COMPANION_EXPERIENCE=true`: the specialist selector is hidden; the user interacts with Ava (Atlas in companion mode). An **Ask an expert** button opens `ExpertTeamPanel` for direct specialist access.

### Chart rendering
When a Vega response contains `data.chart`, the Chat page renders a line/bar chart inline using MUI / a charting library with the provided `data`, `x_key`, and `series` fields.

---

## Key Components

### `AssistantPresence`
Displays the AI companion's visual presence (avatar, name, status indicator). In voice mode:
- Shows `listening` state while recording.
- Shows `thinking` state while waiting for the API response.
- Shows `speaking` state while playing audio.

### `ExpertTeamPanel`
A drawer/panel listing all specialists returned by `GET /api/specialists/`. Each entry shows:
- Name, title, description.
- Suggested prompts (chips that auto-fill the chat input).
- **Ask directly** button — sets `selectedSpecialist` in `ChatContext` and opens the chat.

### `DelegationTimeline`
An animated vertical timeline shown during Atlas synthesis queries. Renders `delegation_started` and `delegation_completed` events as they arrive, then collapses to a "Consulted Vega and Nova" summary after the answer is complete.

### `ConversationHistoryDrawer`
A slide-in drawer (opened from the history icon) showing the user's past conversations, each with title, date, and specialist attribution. Clicking a conversation loads it into the chat.

### `AgentOrb`
An animated SVG/CSS orb used as the visual indicator for each specialist in the expert panel and delegation timeline.

---

## Streaming SSE Parser (`chatApi.js`)

The SSE stream is parsed manually (not using `EventSource`) because the request is a `POST` with a body:

```javascript
const response = await fetch(`${API_BASE}/ask/`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
  body: JSON.stringify({ question, specialist, conversation_id, companion_mode }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // Parse SSE events from text
  for (const line of text.split("\n")) {
    if (line.startsWith("event: ")) currentEvent = line.slice(7).trim();
    if (line.startsWith("data: ")) {
      const payload = JSON.parse(line.slice(6));
      handleEvent(currentEvent, payload);
    }
  }
}
```

---

## Routing

`App.jsx` uses React Router v6. Protected routes require a valid JWT token (checked via `AuthContext`). Main routes:

| Path | Component | Auth Required |
|---|---|---|
| `/login` | Login page | No |
| `/` (redirect) | → `/chat` | — |
| `/chat` | Chat/index.jsx | Yes |
| `/dashboard` | Dashboard | Yes |
| `/finance-data` | FinanceData | Yes |
| `/kpis` | KPI | Yes |
| `/reports` | Reports | Yes |
| `/tasks` | Tasks | Yes |
| `/history` | History | Yes |
| `/settings` | Settings | Yes |

---

## Adding a New Page

1. Create `frontend/src/pages/MyPage/index.jsx`.
2. Add a route in `App.jsx`.
3. Add a nav link in `Sidebar`.
4. Add any necessary API calls to `chatApi.js` or a new file in `src/api/`.
