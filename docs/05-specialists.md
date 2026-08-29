# 05 — Specialists

All seven specialists are registered under `nexus/specialists/`. The six general-purpose specialists live in [`nexus/specialists/workforce.py`](../nexus/specialists/workforce.py), and Ledger lives in [`nexus/specialists/reconciliation.py`](../nexus/specialists/reconciliation.py). Each is a Python class that:

1. Inherits from `BaseSpecialist` and is decorated with `@register_specialist`.
2. Declares metadata (`name`, `domain`, `title`, `description`, `required_groups`, `suggested_prompts`).
3. Implements `handle(question: str, context: EchoContext) -> SpecialistResponse`.
4. Optionally declares `can_delegate_to()` for cross-specialist collaboration.

---

## BaseSpecialist Contract

```python
class BaseSpecialist(ABC):
    name: str                   # Unique identifier used by registry
    domain: str                 # Logical domain (e.g., "data_intelligence")
    model: str = "gemini"       # LLM stub — all use Gemini currently
    required_groups: list[str]  # Django groups required; [] = any authenticated user
    aliases: list[str]          # Alternate names for routing (e.g., ["financial advisor"])
    title: str                  # Human-readable title
    description: str            # Short description shown in the UI
    suggested_prompts: list[str]
    voice_enabled: bool = True
    collaboration_enabled: bool = True

    @abstractmethod
    def handle(self, question: str, context: EchoContext) -> SpecialistResponse: ...

    def can_delegate_to(self) -> list[str]: ...
    def delegate(self, to_specialist, question, context, summary="") -> SpecialistResponse | None: ...
```

`SpecialistResponse` fields:
- `agent: str` — specialist name
- `analysis: str | Generator` — the main answer (streaming generator in stream mode)
- `recommendation: str` — one-line follow-up suggestion
- `data: dict` — optional structured data (e.g., chart data from Vega)
- `contributors: list[str]` — specialists consulted (populated by Atlas synthesis)

---

## Atlas — AI Chief of Staff

**Domain:** `executive_intelligence`  
**Required groups:** `CFO`, `Finance Manager`  
**Delegates to:** Vega, Nova (on cross-functional questions)

### What Atlas does
- Provides executive summaries of financial health, KPI narration, and business performance assessments.
- Detects **cross-functional questions** (e.g., "Why are collections falling?") by checking for both data-analysis keywords and finance keywords simultaneously.
- When a cross-functional question is detected and `_delegation_depth == 0`, Atlas delegates to Vega (for trend analysis) and Nova (for cash context), then synthesizes their responses using `ask_synthesis()`.
- In **companion mode**, Atlas adopts the "Ava" persona with a warmer, more human tone.

### Synthesis trigger logic
```python
_SYNTHESIS_DATA_KEYWORDS = {"trend", "compare", "chart", "why", "falling", "rising", ...}
_SYNTHESIS_FINANCE_KEYWORDS = {"cash", "collection", "liquidity", "revenue", ...}

def _needs_synthesis(question):
    return has_data_keyword AND has_finance_keyword
```

### Fallback (no AI)
If Gemini fails, Atlas returns a template response using the latest month's revenue, EBITDA, and cash values with a month-on-month revenue change.

---

## Vega — AI Data Analyst

**Domain:** `data_intelligence`  
**Required groups:** `CFO`, `Finance Manager`  
**Delegates to:** Nova (declared; not yet triggered automatically)

### What Vega does
- Analyzes financial trends, comparisons, and drivers from `FinancialMetric` data.
- Automatically selects the most relevant metric (revenue, EBITDA, expenses, cash, budget) based on keyword matching in the question.
- Returns **chart data** alongside the text analysis in `SpecialistResponse.data`:
  ```json
  {
    "chart": {
      "type": "line",
      "title": "Revenue trend",
      "x_key": "month",
      "series": ["revenue"],
      "data": [{"month": "Jan-2026", "revenue": 1234567.0}, ...]
    }
  }
  ```
  The frontend Chat page renders this chart when present.

### Fallback (no AI)
Returns the latest period's metric value and a direction indicator versus the prior period.

---

## Nova — AI Financial Advisor

**Domain:** `financial_advisory`  
**Required groups:** `CFO`, `Finance Manager`

### What Nova does
- Analyzes cash flow, treasury position, payments, collections, and liquidity from `FinancialMetric` data.
- Is the **default voice specialist** (see [Voice Pipeline](./08-voice-pipeline.md)).
- Reuses `analyze_financial_data()` from `ai_service.py` for backward compatibility.

### Data used
Same `FinancialMetric` records as Atlas and Vega. Nova's persona prompt focuses specifically on cash, liquidity, and payments rather than executive summary or trend analysis.

---

## Aria — AI Operations Manager

**Domain:** `operations`  
**Required groups:** `CFO`, `Finance Manager`  
**Delegates to:** Nova (declared)

### What Aria does
- Reviews vendor risk exposure, contract renewals, and operational spend.
- Reads from `Vendor` and `Contract` models (all active vendors for the user's organization).
- Returns **structured vendor data** alongside the text:
  ```json
  {
    "vendors": [
      {
        "name": "Acme Corp",
        "risk_level": "High",
        "annual_spend": 5000000.0,
        "days_to_renewal": 14,
        "expiring_soon": true
      }
    ]
  }
  ```
- Flags contracts expiring within 30 days as `expiring_soon: true`.

### Populating Aria's data
Add `Vendor` and `Contract` records via Django Admin, linked to the relevant `Organization`.

---

## Orion — AI Compliance Officer

**Domain:** `compliance`  
**Required groups:** `CFO`, `Finance Manager`, `Auditor`

### What Orion does
- Reviews compliance status, audit obligations, and policy documents.
- Reads from `ComplianceRecord` and `PolicyDocument` models.
- Returns **compliance summary data**:
  ```json
  {
    "compliance_summary": {
      "total": 10,
      "compliant": 6,
      "attention": 3,
      "overdue": 1,
      "overdue_items": ["GDPR Annual Review", ...]
    }
  }
  ```

### Populating Orion's data
Add `ComplianceRecord` and `PolicyDocument` rows via Django Admin, linked to the relevant `Organization`.

---

## Luna — AI Product Specialist

**Domain:** `product_knowledge`  
**Required groups:** `[]` (any authenticated user)

### What Luna does
- Helps users onboard, troubleshoot, and understand the AI Financial Team platform itself.
- Unlike other specialists, Luna does **not** query financial data — her "data context" is a curated product knowledge base built into the specialist.
- Returns a `capabilities` list in her structured data:
  ```json
  {
    "capabilities": [
      "Chat with any of the six specialists",
      "Upload CSV/XLSX financial data",
      ...
    ]
  }
  ```

### Note
Luna's knowledge base is currently embedded in `workforce.py`. In a future phase, this will be replaced by a proper knowledge-base retrieval system (RAG).

---

## Ledger — AI Reconciliation Controller

**Domain:** `reconciliation`
**Required groups:** `CFO`, `Finance Manager`
**Aliases:** `Reconciliation`, `Recon`, `Reconciliation Engine`

### What Ledger does
- Runs the deterministic settlement-to-ledger matching pipeline.
- Sends unresolved records to Gemini for exception classification and reasoning.
- Returns match rate, exception details, runtime accuracy metrics, throughput, and an executive summary.
- Persists each run to the organization attached to the authenticated user.

Ledger is registered with `@register_specialist` and is reachable through the normal `POST /api/ask/` Nexus route. Nexus loads the user's Echo context before handling the request and writes both the user question and Ledger summary to Echo afterward. The dedicated `POST /api/reconcile/` endpoint remains available for the reconciliation dashboard.

---

## Routing — How Nexus Picks a Specialist

If the user does not explicitly select a specialist, `nexus/router.py` follows this logic:

1. **Follow-up detection** — if the question looks like a follow-up (e.g., starts with "what about", "and", "compared to") AND has no explicit intent keyword, use the last active specialist from Echo.
2. **Classification** — `classify_specialist(question)` in `nexus/specialists/classify.py` sends a Gemini classification prompt with the list of registered specialists and their descriptions. Returns the specialist name.
3. **Fallback** — if classification fails or the name is unrecognized, defaults to `Atlas`.

---

## Adding a New Specialist

1. Create a new class in `nexus/specialists/workforce.py` (or a new file imported from `__init__.py`).
2. Inherit from `BaseSpecialist`, decorate with `@register_specialist`.
3. Implement `handle(question, context) -> SpecialistResponse`.
4. That's it — Nexus auto-discovers it at startup via the `@register_specialist` decorator.

```python
@register_specialist
class MySpecialist(BaseSpecialist):
    name = "MySpecialist"
    domain = "my_domain"
    title = "AI My Specialist"
    description = "Short description shown in UI and used for routing."
    required_groups = ["CFO"]

    def handle(self, question: str, context: EchoContext) -> SpecialistResponse:
        data_ctx = "... build domain data string ..."
        ai_response = ask_specialist(
            data_context=data_ctx,
            question=question,
            specialist_name=self.name,
            persona_prompt="You are ...",
            conversation_context=context.format_for_prompt() or None,
            style=context.response_style,
            stream=context.stream,
        )
        return SpecialistResponse(self.name, ai_response or "No data available.")
```
