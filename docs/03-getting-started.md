# 03 — Getting Started

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 recommended |
| Node.js | 18+ | For the React frontend |
| PostgreSQL | 14+ | Must be running before starting Django |
| Google Gemini API key | — | From [Google AI Studio](https://aistudio.google.com/) |
| Google Cloud TTS key | — | **Optional** — only for server-side TTS; browser fallback works without it |

---

## 1. Clone and orient yourself

```bash
git clone <repo-url>
cd ai-financial-team-working
```

The root contains two independently configured halves:
- **Backend** — Python/Django, run from the repo root.
- **Frontend** — React/Vite, run from the `frontend/` directory.

---

## 2. Backend — Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set these variables:

```env
# Django
Django_KEY=<generate a random secret — see below>
Django_DEBUG=True
Django_ENV=development
Django_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
Django_ENGINE=django.db.backends.postgresql
Django_NAME=ai_financial_team_db
Django_USER=postgres
Django_PASSWORD=your_password
Django_HOST=localhost
Django_PORT=5432

# CORS (must match your Vite dev server URL)
Django_CORS_ALLOWED_ORIGINS=http://localhost:5173

# Google AI
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# Voice (optional — leave as false to use browser TTS)
VOICE_SERVER_TTS=false
# GOOGLE_CLOUD_TTS_KEY=path/to/service-account.json  # only if VOICE_SERVER_TTS=true
```

**Generate a Django secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 3. Backend — Python Environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Database Setup

Make sure PostgreSQL is running and the database exists:

```sql
-- In psql:
CREATE DATABASE ai_financial_team_db;
```

Then apply migrations:

```bash
python manage.py migrate
```

Create a superuser (needed for Django Admin and initial login):

```bash
python manage.py createsuperuser
```

---

## 5. Assign User Groups (Required for Specialist Access)

Log in to Django Admin at `http://127.0.0.1:8000/admin/` and:

1. Go to **Authentication → Groups** and create these groups if they don't exist:
   - `CFO`
   - `Finance Manager`
   - `Auditor`
   - `Admin`
2. Go to **Users** and assign your superuser or test users to the appropriate groups.
3. Also create an **Organization** (under **Agents → Organizations**) and assign a **UserProfile** to link the user to their org — this scopes all financial data.

> **Without a group assignment**, specialist permission checks will deny access.  
> **Without an Organization**, financial data queries return empty results.

---

## 6. Start the Backend

```bash
python manage.py runserver
```

The backend runs on `http://127.0.0.1:8000/`.

- **API base:** `http://127.0.0.1:8000/api/`
- **Admin panel:** `http://127.0.0.1:8000/admin/`
- **API schema (Swagger):** `http://127.0.0.1:8000/api/schema/swagger-ui/`

---

## 7. Frontend — Environment Variables

```bash
cd frontend
cp .env.example .env
```

Open `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_COMPANION_EXPERIENCE=false   # set to true to enable Ava companion UI
```

---

## 8. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173/`.

---

## 9. First Login

1. Navigate to `http://localhost:5173/`
2. Log in with the superuser credentials you created in step 4.
3. You'll be routed to the **Chat** page.
4. Select a specialist from the panel (or ask any question — Nexus will classify it).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `django.db.OperationalError` on migrate | Check PostgreSQL is running; verify `.env` DB credentials |
| `No specialist is registered` error | Ensure `nexus` is in `INSTALLED_APPS` and `nexus/specialists/__init__.py` imports `workforce` |
| Specialist returns "You do not have permission" | Assign the user to a Django group (CFO, Finance Manager, etc.) |
| Gemini API errors | Verify `GEMINI_API_KEY` is set and valid; check `GEMINI_MODEL` is a valid model ID |
| CORS errors in browser | Ensure `VITE_API_BASE_URL` and `Django_CORS_ALLOWED_ORIGINS` match |
| No financial data in responses | Upload data via the Finance Data page, or add `FinancialMetric` rows in Admin linked to the user's Organization |
| Voice not working | Check browser microphone permissions; `VOICE_SERVER_TTS=false` uses browser speech synthesis |
