# AI-Financial-Team: Track 04 (AI Finance Controller)

AI-Financial-Team is a powerful, multi-agent AI financial workforce engineered specifically to solve the manual bottleneck of financial reconciliation and settlement forecasting.

Built for the **Razorpay AI Buildathon (Track 04: AI Finance Controller)**, this system runs the books and matches a large batch of synthetic data (Razorpay settlements vs Internal Ledger), reporting its accuracy and surfacing an honest exception list.

## 🏆 Tackling Track 04: The Bar
The 2026 builder consensus is that *verification capacity*, not generation speed, is the bottleneck. The Track 04 "bar" demands: **Throughput plus measured accuracy plus an honest exception list.** Here is how we meet it:

1. **Measured Accuracy (Precision/Recall/F1)**: Our system doesn't just guess. It compares its AI classifications against a deterministic "ground truth" manifest generated alongside the synthetic data, computes overall and per-category metrics at runtime, and persists the overall F1 score.
2. **Honest Exception List**: Discrepancies and fallback classifications are surfaced directly on the dashboard for review. The engine does not force a match when the input is ambiguous or invalid.
3. **Persistent Audit Trail**: Every reconciliation run, overall F1 score, and AI rationale is persisted securely to a Postgres database, viewable via the Run History UI. Per-category metrics are computed at runtime.

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

### Running the Reconciliation
1. Generate the synthetic test data:
   ```bash
   python generate_synthetic_data.py
   ```
   This generates 60 synthetic records and intentionally injects 10 discrepancies (amount mismatches, date mismatches, missing records). 
2. Start the Backend and Frontend.
3. Navigate to the **Reconciliation Engine** page in the dashboard and click *Run Reconciliation*.

## 📂 Project Structure
- `frontend/` - React UI (Reconciliation Dashboard, KPIs).
- `backend/` - Django configuration.
- `agents/` - REST API endpoints, AI service logic, and the Reconciliation Engine pipeline.
- `nexus/` - Orchestration registry, routing, and registered specialists including Ledger.
- `echo/` - Context and shared memory engine.