# AI-Financial-Team: Track 04 (AI Finance Controller)

AI-Financial-Team is an intelligent financial reconciliation system built specifically for the **Razorpay AI Buildathon (Track 04: AI Finance Controller)**.

## 🏆 Track 04: Closing the Finance-Ops Loop

The Track 04 challenge requires building an agent that **closes one finance-ops loop across a 50+ record batch of synthetic data, reporting its match rate and the exceptions it could not resolve.**

**This system meets the Track 04 evaluation bar with:**

1. **Throughput & Accuracy** — Processes batches of 60+ records with deterministic + AI classification, returning measured precision/recall/F1 scores
2. **Honest Exception List** — All unresolved discrepancies surface directly with classification reasoning, confidence scores, and audit trail
3. **Measurable Performance** — No fabricated metrics; accuracy is compared against generated ground truth; exceptions that resist classification are labeled "unresolvable"

## 🔄 The Finance Reconciliation Workflow

```
Razorpay Settlement Data + Internal Ledger
    ↓
Deterministic Matching (txn_id + amount + date)
    ↓
Unmatched Records → Gemini Classification
    ↓
Exception Report with Confidence Scores
    ↓
Accuracy Evaluation (Precision / Recall / F1)
    ↓
Persistent Audit Trail
```

### The Core Promise
- **Safety First (Deterministic Engine)**: Handles all exact matching and financial arithmetic. The LLM is never permitted to mutate financial state or compute balances.
- **AI Classification**: Resolves ambiguous cases (date offsets, amount mismatches) with explicit reasoning.
- **Honest Failure Modes**: Records that resist classification are marked as "unresolvable" — no hallucinatory guesses.
- **Rigorous Evaluation**: AI accuracy is continuously measured using proper macro-averaged Precision, Recall, and F1 scores against synthetic ground truth, not just simple accuracy.

## 🏗️ Architecture
The reconciliation capability is an AI-assisted finance-ops engine exposed through the same Django API and Nexus routing path as the rest of the application. The registered `Ledger` specialist uses the platform's Gemini integration: a deterministic matching engine catches exact matches, unresolved rows are classified by Gemini through the existing AI service, and Gemini produces an executive summary. Nexus loads and writes Ledger conversation turns through Echo. `POST /api/ask/` with Ledger and `POST /api/reconcile/` are two entry points to the same engine: the former provides conversational specialist routing, while the latter supports the dashboard's direct batch workflow, so neither is redundant.
👉 [View the Full Architecture Diagram](docs/architecture_diagram.md)
👉 [View the Hackathon Technical & Product Snapshot](docs/project_snapshot.md)

## ⚙️ Technology Stack
- **Frontend**: React, Vite, Material UI (MUI), Recharts
- **Backend**: Django REST Framework, PostgreSQL
- **AI Engine**: Google Generative AI (Gemini Flash)
- **Memory**: Embedded Shared Memory (Echo)

Reconciliation has dedicated run and exception persistence models, and Ledger requests are also recorded in the shared Echo conversation history.

## 🚀 Getting Started
Please refer to the [Project Setup Guide](setup.md) for detailed instructions on prerequisites, environment configuration, database migration, and running both the Django backend and the Vite React frontend locally.

### Validation commands
The project has been verified with these commands from the repo root using the virtual environment:

```bash
.\.venv\Scripts\python.exe manage.py spectacular --file schema.yml
.\.venv\Scripts\python.exe manage.py test
```

This generates the OpenAPI schema at [schema.yml](schema.yml) and runs the full backend test suite.

### 5-Minute Razorpay Hackathon Demo
1. Generate the synthetic test data:
   ```bash
   python generate_synthetic_data.py --batch canonical_60
   ```
   This generates 60 synthetic records with a clean distribution: 50 matched, 10 exceptions (2 per category). A ground truth file is strictly maintained for evaluation.
2. Start the Backend: `.\.venv\Scripts\python.exe manage.py runserver`
3. Start the Frontend: `cd frontend && npm run dev`
4. Navigate to the **Reconciliation Engine** page in the dashboard.
5. Click **Run Reconciliation** — observe throughput, AI classification (with confidence scoring), and the rigorous macro-averaged evaluation metrics.
6. Inspect the Exception Table to see deterministic vs. AI classifications side-by-side with ground-truth correctness validation.

## 📂 Project Structure
- `frontend/` - React UI (Reconciliation Dashboard, KPIs).
- `backend/` - Django configuration.
- `agents/` - REST API endpoints, AI service logic, and the Reconciliation Engine pipeline.
- `nexus/` - Orchestration registry, routing, and registered specialists including Ledger.
- `echo/` - Context and shared memory engine.