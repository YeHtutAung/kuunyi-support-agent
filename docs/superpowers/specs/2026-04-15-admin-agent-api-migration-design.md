# Admin Agent — API Migration & New Tools Design

## Overview

Migrate the `kuunyi_admin_agent` from direct Supabase access to calling the KuuNyi Next.js admin API. Add new tools for payment verification and student detail lookup. This eliminates dual-maintenance of business logic across the agent and the web app.

**Before:**
```
Admin Agent → Supabase (direct DB queries)
Next.js App → Supabase (separate queries, separate logic)
```

**After:**
```
Admin Agent → Next.js Admin API → Supabase
Next.js App → Supabase
```

---

## Architecture

### File Changes

```
my_support_agent/
├── api_client.py              ← NEW: shared HTTP client
├── config.py                  ← UPDATED: add init_admin() path
├── admin_agent.py             ← UPDATED: use init_admin(), updated tool list
└── tools/
    ├── seats.py               ← MIGRATED: GET /api/intakes + /classes
    ├── summary.py             ← MIGRATED: GET /api/admin/stats (renamed get_stats)
    ├── admin_enrollments.py   ← MIGRATED: GET /api/admin/students
    ├── update_class.py        ← MIGRATED: PATCH /api/classes/[id] via API
    ├── payments.py            ← NEW: pending payments + verify with confirmation gate
    └── student_detail.py      ← NEW: GET /api/admin/students/[id]
```

**Removed:** `get_class_details` — redundant after `get_seats_overview` returns full class data including IDs.

---

## Environment Variables

### Added
```
ADMIN_API_BASE_URL=https://nihon-moment.kuunyi.com
AGENT_SECRET=<secret>
TENANT_NAME=Nihon Moment   ← optional, falls back to TENANT_SLUG if not set
```

### Removed from admin agent
```
SUPABASE_URL   ← no longer needed by admin agent
SUPABASE_KEY   ← no longer needed by admin agent
```

The support agent (`my_support_agent`) still uses Supabase and retains these vars.

**Note on `TENANT_NAME`:** The system instruction uses `{tenant_name}` to greet the admin. Previously this came from Supabase. After migration, `init_admin()` reads `TENANT_NAME` from env. If not set, it falls back to `TENANT_SLUG` (e.g. `nihon-moment`). This keeps Supabase out of the admin agent entirely.

---

## `api_client.py`

Shared HTTP client module. All tools import `call_admin_api` from here.

### Interface

```python
def init_api_client() -> None:
    """Initialize the API client. Called once at startup by init_admin()."""

def call_admin_api(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Make an authenticated request to the admin API."""
```

### Behaviour

- Reads `ADMIN_API_BASE_URL` and `AGENT_SECRET` from env at `init_api_client()`
- Raises `RuntimeError` at startup if either is missing or base URL is not `https://`
- Injects on every request:
  ```
  x-agent-secret: <AGENT_SECRET>
  x-tenant-slug:  <TENANT_SLUG>
  ```
- Hard 10s timeout on all requests
- Returns `{"error": "..."}` on all failure cases — **secret never appears in error output**
- No retry on `401`/`403` — surfaces immediately

### Error mapping

| Condition | Return value |
|-----------|-------------|
| Timeout | `{"error": "Request timed out. Please try again."}` |
| Network failure | `{"error": "Unable to reach the API. Please try again shortly."}` |
| `401` / `403` | `{"error": "Authentication failed. Check AGENT_SECRET configuration."}` |
| `404` | `{"error": "Not found."}` |
| Other non-2xx | `{"error": "API request failed: <status_code>."}` |

---

## `config.py` Changes

Add `init_admin()` alongside the existing `init()`.

```python
def init_admin() -> None:
    """Lightweight init for admin agent — no Supabase required."""
    _load_tenant_slug()   # reads TENANT_SLUG from env, sets _tenant_slug
    init_api_client()     # sets up api_client with base URL + secret
```

- `admin_agent.py` calls `init_admin()` instead of `init()`
- `init()` is unchanged — still used by the support agent
- `get_tenant_id()` and `get_tenant_name()` remain for support agent use only
- `init_admin()` sets `_tenant_name` from `TENANT_NAME` env var (falls back to `TENANT_SLUG`)

---

## Migrated Tools

### `get_seats_overview()` — `seats.py`

**API calls:**
1. `GET /api/intakes` — find the intake with `status=open`
2. `GET /api/intakes/[id]/classes` — get all classes for that intake

**Returns:** List of classes with `class_id`, `level`, `capacity`, `seats_remaining`, `price_mmk`, `status`, `mode`.

**Note:** Returns `class_id` so the agent can pass it directly to `update_class` — `get_class_details` is no longer needed.

**Error case:** If no open intake exists, returns `{"error": "No open intake found."}`.

---

### `get_stats()` — `summary.py`

Replaces `get_summary(period)`.

**API call:** `GET /api/admin/stats`

**Returns:** `total_enrollments`, `confirmed_count`, `pending_payment_count`, `payment_submitted_count`, `total_revenue_mmk`, `seats_by_class`.

**Note:** Period filtering (`day`/`week`) is dropped — the stats endpoint returns an all-time snapshot. The system instruction is updated to reflect this.

---

### `list_enrollments(status, search, page)` — `admin_enrollments.py`

**API call:** `GET /api/admin/students?status=...&search=...&page=...&page_size=20`

**Changes from current:**
- Gains `search` param (partial match on student name or phone)
- Status values updated to API enums: `pending_payment` · `payment_submitted` · `partial_payment` · `confirmed` · `rejected`

**Returns:** Paginated list with `enrollment_ref`, `student_name_en`, `phone`, `class_level`, `status`, `enrolled_at`, `intake_name`.

---

### `update_class` / `confirm_update` / `cancel_update` — `update_class.py`

Same confirmation gate pattern as today. Only the transport changes.

**Flow:**
1. `update_class(class_id, capacity, price_mmk, status)` — stages to `tool_context.state["pending_update"]`, returns summary for agent to show admin
2. Admin replies YES → `confirm_update()` → `PATCH /api/classes/[id]` with staged fields
3. Admin replies NO → `cancel_update()` → clears state

**`PATCH /api/classes/[id]` body:** any subset of `{ fee_mmk, seat_total, status }`

**Note:** `get_class_details` is removed. The agent uses `get_seats_overview` to find the class ID and current values before calling `update_class`.

---

## New Tools

### `get_student_detail(enrollment_id)` — `student_detail.py`

**API call:** `GET /api/admin/students/[enrollment_id]`

**Returns:** Full profile — `student_name_en`, `student_name_mm`, `phone`, `email`, `nrc_number`, `class_level`, `intake_name`, `status`, `fee_mmk`, and payment details (`amount_mmk`, `bank_reference`, `payer_institution`, `submitted_at`, `verified_at`, `proof_signed_url`).

Use when the admin needs full details on a specific student.

---

### `get_pending_payments()` — `payments.py`

**API call:** `GET /api/admin/payments/pending`

**Returns:** All enrollments with `payment_submitted` status, oldest first. Each record includes student name, class level, intake name, amount, bank reference.

---

### `verify_payment(payment_id, action, rejection_reason, admin_note, received_amount)` — `payments.py`

Confirmation gate — mirrors the `update_class` pattern.

**Arguments:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `payment_id` | str | yes | Payment UUID |
| `action` | str | yes | `approve` \| `reject` \| `request_remaining` |
| `rejection_reason` | str | no | Required when action is `reject` |
| `admin_note` | str | no | Required when action is `request_remaining` |
| `received_amount` | int | no | MMK amount received (for `request_remaining`) |

**Flow:**
1. `verify_payment(...)` — stages to `tool_context.state["pending_payment_action"]`, returns summary
2. Agent shows admin: student name, class, amount, action, and consequences:
   - `approve` → "Will send confirmation notification + Telegram channel invite if eligible"
   - `reject` → "Will send rejection notification. Seats will be restored."
   - `request_remaining` → "Will send partial payment notification with remaining amount."
3. Admin replies YES → `confirm_payment_action()` → `PATCH /api/admin/payments/[id]/verify`
4. Admin replies NO → `cancel_payment_action()` → clears state

**`confirm_payment_action` / `cancel_payment_action`** follow the exact same implementation pattern as `confirm_update` / `cancel_update`.

---

## Updated `admin_agent.py`

### Tool list

```python
tools=[
    # Read
    get_seats_overview,
    get_stats,
    list_enrollments,
    get_student_detail,
    get_pending_payments,
    # Write — class updates (staged)
    update_class,
    confirm_update,
    cancel_update,
    # Write — payment actions (staged)
    verify_payment,
    confirm_payment_action,
    cancel_payment_action,
]
```

### System instruction changes

1. Replace `get_summary` references with `get_stats` — no period parameter
2. Add payment workflow rules:
   - "To list payments awaiting verification, call `get_pending_payments`"
   - "To approve/reject a payment, call `verify_payment` → show summary → wait for YES/NO → call `confirm_payment_action` or `cancel_payment_action`"
   - "Never call `confirm_payment_action` unless the admin explicitly said YES in this conversation turn"
3. Add student detail rule: "To look up a specific student's full details, call `get_student_detail` with their enrollment UUID"

### `init_admin()` call

```python
# admin_agent.py
from my_support_agent.config import init_admin, get_tenant_name

init_admin()   # was: init()
```

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `AGENT_SECRET` or `ADMIN_API_BASE_URL` missing | `RuntimeError` at `init_admin()` — fail fast |
| Base URL is `http://` | `RuntimeError` at `init_admin()` — fail fast |
| No open intake found | `{"error": "No open intake found."}` |
| API timeout | `{"error": "Request timed out. Please try again."}` |
| `401` / `403` | `{"error": "Authentication failed. Check AGENT_SECRET configuration."}` |
| `404` | `{"error": "Not found."}` |
| Other non-2xx | `{"error": "API request failed: <status_code>."}` |
| Confirm with no pending state | `{"error": "No pending action to confirm."}` |

---

## Out of Scope

- Intake creation (`POST /api/intakes`) — infrequent, can be added separately
- Class creation (`POST /api/intakes/[id]/classes`) — infrequent, can be added separately
- Analytics time-series (`GET /api/admin/analytics`) — can be added as a separate `get_analytics(range)` tool
- Support agent changes — unaffected by this migration
