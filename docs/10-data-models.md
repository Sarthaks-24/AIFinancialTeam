# 10 — Data Models

All Django models live in [`agents/models.py`](../agents/models.py) (business domain) and [`echo/models.py`](../echo/models.py) (memory layer).

---

## Multi-Tenancy via `Organization`

Almost every model has a `ForeignKey` to `Organization`. This is the **tenant boundary** — data for one organization is never visible to another. The `Organization` FK is resolved through the authenticated user's `UserProfile`.

```python
# How specialists scope their queries:
org = user.profile.organization
records = FinancialMetric.objects.filter(organization=org)
```

---

## `agents` App Models

### `Organization`

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(255) | Unique |
| `created_at` | DateTimeField | Auto |

### `UserProfile`

One-to-one extension of Django's `User`. Links a user to their organization.

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOneField → User | `related_name="profile"` |
| `organization` | FK → Organization (nullable) | Nullable for admin/superuser accounts |

### `FinancialMetric`

Core financial data table. Each row represents one reporting period for one organization.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | Tenant scope |
| `month` | CharField(50) | e.g., `"Jan-2026"` |
| `revenue` | DecimalField(15,2) | |
| `expenses` | DecimalField(15,2) | |
| `ebitda` | DecimalField(15,2) | |
| `cash_position` | DecimalField(15,2) | |
| `budget` | DecimalField(15,2) | Default 0 |
| `created_at` | DateTimeField | Auto |

**Unique together:** `(organization, month)` — one row per period per org.

### `QueryLog`

Legacy write-only audit log. Kept for backward compatibility; will be deprecated once `echo.Turn` covers all history.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `question` | TextField | |
| `agent_name` | CharField(100) | |
| `response` | TextField | |
| `created_at` | DateTimeField | Auto |

### `Task`

Operational task tracking.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `title` | CharField(255) | |
| `description` | TextField | |
| `status` | CharField(50) | Default: `"Pending"` |
| `priority` | CharField(50) | Default: `"Medium"` |
| `created_at` | DateTimeField | Auto |

### `Report`

AI-generated reports.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `report_type` | CharField(100) | e.g., `"Financial Health"` |
| `summary` | TextField | The generated report text |
| `created_at` | DateTimeField | Auto |

### `FinancialUpload`

Tracks uploaded CSV/XLSX files.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `file_name` | CharField(255) | Original filename |
| `uploaded_file` | FileField | Stored under `financial_uploads/` |
| `uploaded_at` | DateTimeField | Auto |

### `Vendor`

Vendor / supplier records (used by Aria).

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `name` | CharField(255) | Unique per org |
| `category` | CharField(100) | Optional category label |
| `annual_spend` | DecimalField(15,2) | Default 0 |
| `risk_level` | CharField(20) | `Low` / `Medium` / `High` |
| `contract_renewal_date` | DateField (nullable) | |
| `is_active` | BooleanField | Default `True` |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

**Unique together:** `(organization, name)`

### `Contract`

Contracts linked to vendors (used by Aria).

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `vendor` | FK → Vendor | `related_name="contracts"` |
| `title` | CharField(255) | |
| `start_date` | DateField (nullable) | |
| `end_date` | DateField (nullable) | |
| `total_value` | DecimalField(15,2) | Default 0 |
| `terms` | TextField | Optional |
| `created_at` | DateTimeField | Auto |

### `ComplianceRecord`

Compliance obligation tracking (used by Orion).

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `name` | CharField(255) | Obligation name |
| `jurisdiction` | CharField(100) | Optional |
| `status` | CharField(20) | `Compliant` / `Attention` / `Overdue` |
| `due_date` | DateField (nullable) | |
| `evidence_reference` | CharField(500) | Link or reference to evidence |
| `notes` | TextField | |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

**Ordering:** `["due_date", "name"]`

### `PolicyDocument`

Policy documents linked to compliance records (used by Orion).

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `compliance_record` | FK → ComplianceRecord (nullable) | `related_name="policies"` |
| `title` | CharField(255) | |
| `last_updated` | DateTimeField | Auto |

### `ReconciliationRun`

Tracks a batch execution of the deterministic + AI reconciliation engine.

| Field | Type | Notes |
|---|---|---|
| `organization` | FK → Organization | |
| `dataset_name` | CharField(100) | e.g. `canonical_60` |
| `total_records` | IntegerField | |
| `matched_records` | IntegerField | |
| `exceptions_count` | IntegerField | |
| `overall_f1_score` | FloatField (nullable) | Macro-averaged F1 score |
| `processing_time_ms` | IntegerField | |
| `run_at` | DateTimeField | Auto |

### `ReconciliationException`

Tracks individual unresolved records classified by the AI.

| Field | Type | Notes |
|---|---|---|
| `run` | FK → ReconciliationRun | `related_name="exceptions"` |
| `txn_id` | CharField(100) | |
| `exception_type` | CharField(50) | e.g., `amount_mismatch` |
| `confidence` | FloatField (nullable) | From Gemini |
| `settlement_amount` | DecimalField(15,2) (nullable) | |
| `ledger_amount` | DecimalField(15,2) (nullable) | |
| `settlement_date` | DateField (nullable) | |
| `ledger_date` | DateField (nullable) | |
| `delta` | DecimalField(15,2) (nullable) | |
| `ai_reasoning` | TextField | |
| `classification_source` | CharField(20) | `ai` or `deterministic` |
| `ground_truth_type` | CharField(50) (nullable) | Injected ground truth label |
| `is_correct` | BooleanField (nullable) | Eval: `exception_type == ground_truth_type` |

---

## `echo` App Models

### `Conversation`

A user-owned chat session.

| Field | Type | Notes |
|---|---|---|
| `user` | FK → User | `related_name="echo_conversations"` |
| `organization` | FK → Organization (nullable) | |
| `specialist` | CharField(100) | Legacy: originating specialist; blank for new multi-specialist sessions |
| `title` | CharField(255) | Auto-set from first user message (max 80 chars) |
| `started_at` | DateTimeField | Auto |
| `last_active_at` | DateTimeField | Auto-updated |
| `archived_at` | DateTimeField (nullable) | Non-null = archived |

**Index:** `(user, archived_at, -last_active_at)` for fast active-session queries.

### `Turn`

A single message within a conversation.

| Field | Type | Notes |
|---|---|---|
| `conversation` | FK → Conversation | `related_name="turns"` |
| `organization` | FK → Organization (nullable) | |
| `role` | CharField(20) | `user` or `specialist` |
| `specialist_name` | CharField(100) | Which specialist spoke |
| `content` | TextField | Message content |
| `created_at` | DateTimeField | Auto |

**Ordering:** `["created_at"]` (ascending)

### `MemoryFact`

A structured persistent fact.

| Field | Type | Notes |
|---|---|---|
| `user` | FK → User | `related_name="echo_facts"` |
| `organization` | FK → Organization (nullable) | |
| `category` | CharField(40) | `preference` / `org_context` / `prior_finding` |
| `key` | CharField(200) | Fact name |
| `value` | TextField | Fact value |
| `source_turn` | FK → Turn (nullable) | Turn that produced this fact |
| `created_at` | DateTimeField | Auto |
| `expires_at` | DateTimeField (nullable) | Null = never expires |
| `embedding` | JSONField (nullable) | Vector embedding (list of floats) |

**Index:** `(user, category, key)` for fast fact lookups.

---

## ER Diagram (simplified)

```
User ──────────── UserProfile ──── Organization
                                       │
              ┌────────────────────────┤
              │                        │
        FinancialMetric          Conversation (echo)
        FinancialUpload               │
        QueryLog                     Turn (echo)
        Task                    MemoryFact (echo)
        Report
        Vendor
          └── Contract
        ComplianceRecord
          └── PolicyDocument
        ReconciliationRun
          └── ReconciliationException
```

---

## Migrations

To create or apply migrations after model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

Both `agents` and `echo` apps have their own migration folders.
