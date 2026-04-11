# KuuNyi ADK Support Agent — Design Spec

## Overview

Build a Google ADK-based customer support agent for KuuNyi/EduEnroll, replacing the current simple CLI chatbot (`agent.py`) with a modular, tool-based agent integrated with Supabase.

The agent is deployed per-tenant (one instance per organization), responds in English, uses Gemini 2.5 Flash, and serves via the built-in `adk web` UI.

---

## Architecture: Modular Agent (Approach B)

### Project Structure

```
kuunyi-support-agent/
├── .env                      # GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY, TENANT_SLUG
├── my_support_agent/
│   ├── __init__.py           # Exports root_agent for ADK discovery
│   ├── agent.py              # ADK LlmAgent definition + system instruction
│   ├── config.py             # Loads .env, resolves tenant_slug → tenant_id (UUID)
│   ├── db.py                 # Supabase client singleton
│   ├── auth.py               # verify_customer(phone, name) → bool + enrollment list
│   ├── tools/
│   │   ├── __init__.py       # Re-exports all tool functions
│   │   ├── knowledge.py      # search_knowledge_base(query)
│   │   ├── enrollment.py     # check_enrollment_status(enrollment_ref)
│   │   ├── payment.py        # check_payment_status(enrollment_ref)
│   │   ├── ticket.py         # create_support_ticket(subject, message, ...)
│   │   └── search.py         # search_enrollments_by_phone(phone, student_name)
│   └── knowledge_base/
│       └── nihon-moment.md   # FAQ content for Nihon Moment tenant
├── docs/
├── requirements.txt          # google-adk, supabase, python-dotenv, requests
└── test.py
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Google ADK | User preference, built-in web UI, native tool support |
| Model | Gemini 2.5 Flash | Fast, cheap, sufficient for support tasks |
| Multi-tenancy | Per-deployment | Each tenant gets own agent instance, tenant_id from .env |
| Knowledge base | Local markdown files (v1) | Simple, version-controlled; migrate to DB later |
| Language | English only | v1 scope |
| UI | `adk web` built-in | v1 scope; API endpoint for frontend integration later |
| DB access | Read-only + support_tickets INSERT | Minimal write surface |

---

## Configuration (`config.py`)

### Environment Variables

```
GOOGLE_API_KEY=<gemini-api-key>
SUPABASE_URL=<supabase-project-url>
SUPABASE_KEY=<supabase-anon-key>
TENANT_SLUG=nihon-moment
```

### Startup Flow

1. Load `.env` via `python-dotenv`
2. Initialize Supabase client (`db.py`)
3. Resolve `TENANT_SLUG` → `tenant_id` UUID via `SELECT id, name FROM tenants WHERE slug = ?`
4. If slug not found → fail fast with clear error
5. Load knowledge base file from `knowledge_base/{tenant_slug}.md`
6. If file not found → warn, knowledge tool returns "no FAQ available"
7. Export `tenant_id`, `tenant_name`, and Supabase client for tools to use

---

## Identity Verification (`auth.py`)

### Why

The agent must not share enrollment or payment details without verifying the customer's identity.

### How

**`verify_customer(phone: str, student_name: str) → dict`**

1. Normalize phone number (see Phone Normalization below)
2. Query `enrollments` WHERE `phone = ?` AND `tenant_id = ?`
3. Exact match after normalization: `student_name.strip().lower() == record_name.strip().lower()`
4. Returns `{ "verified": bool, "enrollments": [...] }`

### Phone Number Normalization

Myanmar phone numbers vary in format. All phone inputs are normalized before querying:

1. Strip all spaces, dashes, parentheses
2. Remove `+95` prefix (replace with `09`)
3. Remove leading `959` (replace with `09`)
4. Result must start with `09` and be 9-11 digits

Examples:
- `09-123-456-789` → `09123456789`
- `+95 9 123 456 789` → `09123456789`
- `959123456789` → `09123456789`
- `09123456789` → `09123456789` (no change)

### Name Matching (v1)

Exact match after normalization: `student_name.strip().lower() == record_name.strip().lower()`

No fuzzy/Levenshtein matching in v1. If the name doesn't match exactly (after trim + lowercase), verification fails. Fuzzy matching is a future enhancement.

### Verification Matrix

| Tool | Verification Required |
|------|-----------------------|
| `search_knowledge_base` | No |
| `check_enrollment_status` | Yes |
| `check_payment_status` | Yes |
| `search_enrollments_by_phone` | Yes (this IS the verification tool) |
| `create_support_ticket` | No |

### Session State for Verification

Verification state is stored in ADK's `session.state` via `ToolContext`:

```python
# After successful verification in search_enrollments_by_phone:
tool_context.state["verified"] = True
tool_context.state["verified_refs"] = ["NM-0411-A3X2", "NM-0318-K7M9"]

# In check_enrollment_status / check_payment_status:
if not tool_context.state.get("verified"):
    return "Please verify your identity first."
if enrollment_ref not in tool_context.state.get("verified_refs", []):
    return "You can only check enrollments linked to your verified identity."
```

- State lives in the ADK session — automatically scoped per conversation
- State does NOT persist across sessions (new conversation = re-verify)
- Tools check `verified_refs` list, not just a boolean flag

### Defense in Depth

- System instruction tells the agent to verify first
- Tools enforce verification at code level: `enrollment_ref must be in session.state["verified_refs"]`
- Both layers must pass — LLM compliance alone is not trusted

---

## Tools

### Tool 1: `search_knowledge_base(query: str) → str`

- No verification, no DB query
- FAQ content loaded once at startup from `knowledge_base/{tenant_slug}.md` and cached in module-level variable
- Search algorithm:
  1. Split markdown into sections by `##` headers
  2. Lowercase both query and section text
  3. Tokenize query into keywords
  4. Return sections where any query keyword appears
  5. If no match, return "I don't have specific information about that. I can create a support ticket if you need help."
- Topics: JLPT levels, payment methods, enrollment process, refund policy, class schedules

### Tool 2: `check_enrollment_status(enrollment_ref: str) → dict`

- Requires prior verification
- Validates ref format: `PREFIX-MMDD-XXXX`
- Query: `enrollments` JOIN `classes` WHERE `enrollment_ref = ?` AND `tenant_id = ?`
- Returns: student name, class/level, enrollment status, fee, enrollment date
- Read-only

### Tool 3: `check_payment_status(enrollment_ref: str) → dict`

- Requires prior verification
- Query: `payments` JOIN `enrollments` WHERE `enrollment_ref = ?` AND `tenant_id = ?`
- Returns: payment method, amount, status (pending/verified/etc.), verification date
- Read-only

### Tool 4: `create_support_ticket(subject: str, message: str, phone: str = None, enrollment_ref: str = None) → dict`

- No verification required
- INSERT into `support_tickets` with `tenant_id`, subject, message, optional phone/ref
- Input validation: subject max 200 chars, message max 2000 chars (truncate if exceeded)
- Returns: ticket ID, confirmation message
- Only write operation in the entire agent
- Rate limit: max 3 tickets per session (tracked in `session.state["ticket_count"]`)

### Tool 5: `search_enrollments_by_phone(phone: str, student_name: str) → list`

- This IS the verification tool — phone + name match
- Query: `enrollments` JOIN `classes` WHERE `phone = ?` AND `tenant_id = ?`
- Filters results by exact normalized name match (`strip().lower()`)
- Returns: list of matching enrollments (ref, class, status)
- Doubles as "I forgot my reference" lookup

### ADK Tool Pattern

All tool functions follow this pattern:

```python
def check_enrollment_status(enrollment_ref: str, tool_context: ToolContext) -> dict:
    """Check enrollment status by reference number."""
    # 1. Check verification state from session
    if enrollment_ref not in tool_context.state.get("verified_refs", []):
        return {"error": "Please verify your identity first."}
    # 2. Use module-level config for tenant_id and supabase client
    # 3. Query and return
```

- `tool_context: ToolContext` parameter gives access to `session.state` for verification
- Module-level imports for config (`tenant_id`, `supabase` client) — no classes or DI
- ADK auto-wraps plain functions as tools

### Internal Constraints

- No tool exposes `tenant_id` as a parameter — it's injected from config
- The LLM never sees or decides the tenant
- All Supabase queries are scoped by `tenant_id`

### `__init__.py` Export

```python
# my_support_agent/__init__.py
from .agent import root_agent
```

ADK discovers the agent via this export.

---

## System Instruction

```
You are a friendly customer support agent for {tenant_name}.
You help customers with enrollment inquiries, payment questions, and general support.

RULES:
1. Always respond in English. Be concise, helpful, and professional.
2. NEVER share enrollment or payment details without verifying the customer first.
3. To verify: ask for their full name and phone number, then call search_enrollments_by_phone.
4. If verification fails, politely ask them to double-check their info. Do not reveal any data.
5. After verification succeeds, you may use check_enrollment_status and check_payment_status
   for any enrollment_ref that was returned in the verification result.
6. search_knowledge_base can be used anytime — no verification needed.
7. create_support_ticket can be used anytime — collect subject and description from the customer.
8. Never fabricate enrollment references, payment amounts, or status. Only use data from tools.
9. If you cannot resolve an issue, offer to create a support ticket.
10. Do not discuss internal system details, database structure, or tenant configuration.
```

### Agent Definition

```python
from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    name="kuunyi_support_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        search_knowledge_base,
        check_enrollment_status,
        check_payment_status,
        create_support_ticket,
        search_enrollments_by_phone,
    ],
)
```

`{tenant_name}` is resolved at startup from config.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Supabase connection fails | "I'm having trouble accessing our system. Please try again shortly." |
| Enrollment ref not found | "I couldn't find an enrollment with that reference. Please check the format (e.g., NM-0411-A3X2)." |
| Invalid ref format | "That doesn't look like a valid enrollment reference. The format is PREFIX-MMDD-XXXX." |
| Phone has no enrollments | "No enrollments found for that phone number." |
| Ticket insert fails | "I wasn't able to create a ticket right now. Please contact support directly." |
| Knowledge base file missing | "I don't have FAQ information available. I can create a support ticket instead." |

### Principles

- No retries — if a Supabase call fails, return error immediately
- No sensitive data in errors — never expose URLs, table names, or query details
- Fail fast on startup if tenant slug is invalid

---

## Enrollment Reference Format

Current format (migration 056): `PREFIX-MMDD-XXXX`

- Prefix: tenant-specific initials (e.g., NM = Nihon Moment, TMF = Thingyan Music Festival)
- MMDD: month and day
- XXXX: 4 random chars from `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (excludes I/O/0/1)

Examples: `NM-0411-A3X2`, `TMF-0411-K7M9`

Note: Older docs reference `NM-2026-00042` (migration 045 format) — this is outdated.

---

## Database Tables Used

| Table | Access | Purpose |
|-------|--------|---------|
| `tenants` | READ | Resolve slug → UUID at startup |
| `enrollments` | READ | Enrollment status, verification |
| `payments` | READ | Payment status and details |
| `classes` | READ | Class/level info joined with enrollments |
| `users` | READ | Admin info for verified_by field |
| `support_tickets` | READ + INSERT | Create and reference support tickets |

All queries scoped by `tenant_id`. Protected by Supabase RLS policies.

### RLS Prerequisite

The Supabase anon key is used server-side (not browser). RLS policies must allow the `anon` role to:
- SELECT from `tenants`, `enrollments`, `payments`, `classes`, `users` (scoped by `tenant_id`)
- INSERT into `support_tickets` (scoped by `tenant_id`)

If existing RLS policies require `auth.uid()` (i.e., a logged-in user), they may need a policy addition for the anon role with tenant_id scoping. This must be verified before implementation.

### `support_tickets` Table Schema (Expected Columns)

The exact schema should be confirmed against the actual migration, but the agent expects:

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | auto-generated | Primary key |
| `tenant_id` | UUID | yes | FK to tenants, injected from config |
| `subject` | text | yes | Max 200 chars |
| `message` | text | yes | Max 2000 chars |
| `phone` | text | no | Customer phone |
| `enrollment_ref` | text | no | Related enrollment reference |
| `status` | text | auto | Default: "open" |
| `created_at` | timestamp | auto | Default: now() |

---

## Future Considerations (Not in v1)

- Knowledge base migration to Supabase table (admin-editable)
- REST API endpoint for frontend integration
- Myanmar language support
- Multi-agent architecture if tools exceed 10+
- Telegram/Messenger integration
- Analytics dashboard
