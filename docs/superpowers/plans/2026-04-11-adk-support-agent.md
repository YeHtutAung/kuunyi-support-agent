# KuuNyi ADK Support Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Google ADK-based customer support agent with 5 tools, Supabase integration, identity verification, and per-tenant deployment.

**Architecture:** Modular agent with separate files for config, DB, auth, and each tool. Tools are plain Python functions registered with ADK's LlmAgent. Session state via ToolContext for verification flow.

**Tech Stack:** Google ADK (`google-adk>=1.19.0`), Supabase Python (`supabase>=2.4.0`), Gemini 2.5 Flash, python-dotenv

**Spec:** `docs/superpowers/specs/2026-04-11-adk-support-agent-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `my_support_agent/__init__.py` | Export `root_agent` for ADK discovery |
| `my_support_agent/agent.py` | LlmAgent definition + system instruction |
| `my_support_agent/config.py` | Load .env, resolve tenant_slug → tenant_id, cache knowledge base |
| `my_support_agent/db.py` | Supabase client singleton |
| `my_support_agent/phone_utils.py` | Phone number normalization |
| `my_support_agent/tools/__init__.py` | Re-export all tool functions |
| `my_support_agent/tools/knowledge.py` | search_knowledge_base tool |
| `my_support_agent/tools/enrollment.py` | check_enrollment_status tool |
| `my_support_agent/tools/payment.py` | check_payment_status tool |
| `my_support_agent/tools/ticket.py` | create_support_ticket tool |
| `my_support_agent/tools/search.py` | search_enrollments_by_phone tool |
| `my_support_agent/knowledge_base/nihon-moment.md` | FAQ content for Nihon Moment |
| `tests/test_phone_utils.py` | Phone normalization tests |
| `tests/test_knowledge.py` | Knowledge base search tests |
| `tests/test_config.py` | Config loading tests |

---

## Task 1: Project Setup & Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `my_support_agent/__init__.py`
- Create: `my_support_agent/tools/__init__.py`
- Create: `my_support_agent/knowledge_base/` (directory)
- Create: `tests/__init__.py`

- [ ] **Step 1: Update requirements.txt in project root**

```
google-adk>=1.19.0
supabase>=2.4.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.0.0
```

- [ ] **Step 2: Create directory structure**

Run:
```bash
mkdir -p my_support_agent/tools
mkdir -p my_support_agent/knowledge_base
mkdir -p tests
```

- [ ] **Step 3: Create empty __init__.py files**

`my_support_agent/tools/__init__.py`:
```python
"""KuuNyi Support Agent Tools."""
```

`tests/__init__.py`:
```python
```

- [ ] **Step 4: Create .env.example**

`.env.example`:
```
GOOGLE_API_KEY=your-gemini-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
TENANT_SLUG=nihon-moment
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully, `adk --version` shows a version number.

- [ ] **Step 6: Verify ADK ToolContext import path**

Run: `python -c "from google.adk.tools import ToolContext; print('tools import OK')" 2>/dev/null || python -c "from google.adk.tools import ToolContext; print('agents import OK')"`

Whichever path works, use it consistently in all tool files. If `google.adk.tools` works, use that. If only `google.adk.agents` works, use that.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt my_support_agent/ tests/
git commit -m "chore: set up project structure for ADK agent"
```

---

## Task 2: Phone Number Normalization

**Files:**
- Create: `my_support_agent/phone_utils.py`
- Create: `tests/test_phone_utils.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_phone_utils.py`:
```python
from my_support_agent.phone_utils import normalize_phone


def test_already_normalized():
    assert normalize_phone("09123456789") == "09123456789"


def test_strip_dashes():
    assert normalize_phone("09-123-456-789") == "09123456789"


def test_strip_spaces():
    assert normalize_phone("09 123 456 789") == "09123456789"


def test_plus95_prefix():
    assert normalize_phone("+95 9 123 456 789") == "09123456789"


def test_959_prefix():
    assert normalize_phone("959123456789") == "09123456789"


def test_strip_parentheses():
    assert normalize_phone("(09) 123-456-789") == "09123456789"


def test_invalid_too_short():
    assert normalize_phone("0912") is None


def test_invalid_wrong_prefix():
    assert normalize_phone("12345678901") is None


def test_empty_string():
    assert normalize_phone("") is None


def test_none_input():
    assert normalize_phone(None) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_phone_utils.py -v`
Expected: FAIL — `ImportError: cannot import name 'normalize_phone'`

- [ ] **Step 3: Implement normalize_phone**

`my_support_agent/phone_utils.py`:
```python
"""Myanmar phone number normalization."""

import re


def normalize_phone(phone: str | None) -> str | None:
    """Normalize a Myanmar phone number to 09XXXXXXXXX format.

    Returns None if the input is invalid.
    """
    if not phone:
        return None

    # Strip spaces, dashes, parentheses
    cleaned = re.sub(r"[\s\-\(\)]+", "", phone)

    # Remove +95 country code prefix → prepend 0
    if cleaned.startswith("+95"):
        cleaned = "0" + cleaned[3:]

    # Remove 959 prefix (country code without +) → replace with 09
    if cleaned.startswith("959") and len(cleaned) > 9:
        cleaned = "0" + cleaned[2:]

    # Validate: must start with 09, be 9-11 digits
    if not cleaned.startswith("09"):
        return None
    if not cleaned.isdigit():
        return None
    if len(cleaned) < 9 or len(cleaned) > 11:
        return None

    return cleaned
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_phone_utils.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/phone_utils.py tests/test_phone_utils.py
git commit -m "feat: add Myanmar phone number normalization"
```

---

## Task 3: Supabase Client & Config

**Files:**
- Create: `my_support_agent/db.py`
- Create: `my_support_agent/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write db.py — Supabase client singleton**

`my_support_agent/db.py`:
```python
"""Supabase client singleton."""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
            )
        _client = create_client(url, key)
    return _client
```

- [ ] **Step 2: Write config.py — tenant resolution and knowledge base loading**

`my_support_agent/config.py`:
```python
"""Agent configuration — loads .env, resolves tenant, caches knowledge base."""

import os
from pathlib import Path
from dotenv import load_dotenv
from my_support_agent.db import get_supabase

load_dotenv()

# Resolved at import time
_tenant_id: str | None = None
_tenant_name: str | None = None
_tenant_slug: str | None = None
_knowledge_base: str | None = None


def _resolve_tenant() -> None:
    """Resolve TENANT_SLUG from .env to tenant_id UUID via Supabase."""
    global _tenant_id, _tenant_name, _tenant_slug

    _tenant_slug = os.environ.get("TENANT_SLUG")
    if not _tenant_slug:
        raise RuntimeError("TENANT_SLUG environment variable must be set.")

    supabase = get_supabase()
    response = (
        supabase.table("tenants")
        .select("id, name")
        .eq("slug", _tenant_slug)
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"Tenant not found for slug: {_tenant_slug}")

    _tenant_id = response.data[0]["id"]
    _tenant_name = response.data[0]["name"]


def _load_knowledge_base() -> None:
    """Load FAQ markdown file for the current tenant."""
    global _knowledge_base

    kb_dir = Path(__file__).parent / "knowledge_base"
    kb_file = kb_dir / f"{_tenant_slug}.md"

    if kb_file.exists():
        _knowledge_base = kb_file.read_text(encoding="utf-8")
    else:
        print(f"Warning: Knowledge base file not found: {kb_file}")
        _knowledge_base = None


def init() -> None:
    """Initialize config — call once at startup."""
    _resolve_tenant()
    _load_knowledge_base()


def get_tenant_id() -> str:
    if _tenant_id is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_id


def get_tenant_name() -> str:
    if _tenant_name is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_name


def get_tenant_slug() -> str:
    if _tenant_slug is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_slug


def get_knowledge_base() -> str | None:
    return _knowledge_base
```

- [ ] **Step 3: Write config test**

`tests/test_config.py`:
```python
from pathlib import Path


def test_knowledge_base_file_exists():
    """Verify the nihon-moment knowledge base file exists."""
    kb_file = (
        Path(__file__).parent.parent
        / "my_support_agent"
        / "knowledge_base"
        / "nihon-moment.md"
    )
    assert kb_file.exists(), f"Knowledge base file not found: {kb_file}"
```

Note: Full integration tests for config.init() require Supabase credentials and will be tested manually via `adk web`.

- [ ] **Step 4: Run test (will fail — knowledge base file doesn't exist yet)**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AssertionError: Knowledge base file not found`

- [ ] **Step 5: Create placeholder knowledge base file**

`my_support_agent/knowledge_base/nihon-moment.md`:
```markdown
## JLPT Levels

The Japanese Language Proficiency Test (JLPT) has 5 levels:
- **N5** (Beginner): Basic Japanese, ~800 vocabulary words
- **N4** (Elementary): Basic Japanese, ~1,500 vocabulary words
- **N3** (Intermediate): Everyday Japanese, ~3,750 vocabulary words
- **N2** (Upper Intermediate): Business-level, ~6,000 vocabulary words
- **N1** (Advanced): Fluent-level, ~10,000+ vocabulary words

Nihon Moment offers classes for N5, N4, and N3 levels.

## Payment Methods

We accept the following payment methods:
- **MMQR**: Scan QR code with any Myanmar banking app (recommended)
- **Bank Transfer**: Transfer to our bank account (details provided after enrollment)
- **KBZ Pay / Wave Pay**: Mobile wallet transfer

After payment, your status will change to "payment_submitted". An admin will verify your payment within 24 hours, then your status changes to "confirmed".

## Enrollment Process

1. Visit our enrollment page and fill in your details
2. Select your desired JLPT level and class schedule
3. Submit your enrollment — you'll receive an enrollment reference (e.g., NM-0411-A3X2)
4. Make payment using one of our accepted methods
5. Wait for admin verification (usually within 24 hours)
6. Once confirmed, you'll receive class details via email/SMS

## Checking Your Status

You can check your enrollment status by providing:
- Your enrollment reference number (e.g., NM-0411-A3X2)
- Your full name and phone number (for identity verification)

Our support agent can look up your status, payment information, and class details.

## Refund Policy

- **Before class starts**: Full refund available (minus processing fee)
- **Within first week**: 50% refund
- **After first week**: No refund, but you may transfer to the next batch
- To request a refund, contact our support team with your enrollment reference

## Class Schedule

Classes are held at Nihon Moment Language School. Schedules vary by level:
- **N5 classes**: Monday, Wednesday, Friday
- **N4 classes**: Tuesday, Thursday, Saturday
- **N3 classes**: Monday, Wednesday, Friday (evening)

Exact times depend on the batch. Check your enrollment confirmation for details.

## Contact

For any issues not resolved by the support agent, you can:
- Create a support ticket through this chat
- Email: support@nihonmoment.com
- Phone: Available during business hours
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add my_support_agent/db.py my_support_agent/config.py my_support_agent/knowledge_base/ tests/test_config.py
git commit -m "feat: add Supabase client, config resolver, and knowledge base"
```

---

## Task 4: Knowledge Base Search Tool

**Files:**
- Create: `my_support_agent/tools/knowledge.py`
- Create: `tests/test_knowledge.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_knowledge.py`:
```python
from my_support_agent.tools.knowledge import _search_sections


SAMPLE_KB = """## Payment Methods

We accept MMQR and bank transfer.

## JLPT Levels

N5 is beginner. N1 is advanced.

## Refund Policy

Full refund before class starts.
"""


def test_search_finds_matching_section():
    results = _search_sections(SAMPLE_KB, "payment")
    assert len(results) == 1
    assert "MMQR" in results[0]


def test_search_finds_multiple_sections():
    results = _search_sections(SAMPLE_KB, "JLPT levels")
    assert len(results) >= 1
    assert any("N5" in r for r in results)


def test_search_case_insensitive():
    results = _search_sections(SAMPLE_KB, "REFUND")
    assert len(results) == 1
    assert "refund" in results[0].lower()


def test_search_no_match():
    results = _search_sections(SAMPLE_KB, "telegram")
    assert len(results) == 0


def test_search_empty_query():
    results = _search_sections(SAMPLE_KB, "")
    assert len(results) == 0


def test_search_none_kb():
    results = _search_sections(None, "payment")
    assert len(results) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_knowledge.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement knowledge.py**

`my_support_agent/tools/knowledge.py`:
```python
"""Knowledge base search tool."""

from my_support_agent.config import get_knowledge_base


# Stop words to filter from queries
_STOP_WORDS = {"what", "is", "the", "a", "an", "how", "do", "i", "can", "to", "my", "me", "are", "for", "of", "in", "and", "or"}


def _search_sections(kb_content: str | None, query: str) -> list[str]:
    """Split knowledge base into sections and return matching ones.

    Exported for testing. The tool function below wraps this.
    """
    if not kb_content or not query or not query.strip():
        return []

    # Split by ## headers
    sections: list[str] = []
    current_section = ""
    for line in kb_content.split("\n"):
        if line.startswith("## "):
            if current_section.strip():
                sections.append(current_section.strip())
            current_section = line + "\n"
        else:
            current_section += line + "\n"
    if current_section.strip():
        sections.append(current_section.strip())

    # Tokenize query, remove stop words
    keywords = [
        w for w in query.lower().split()
        if w not in _STOP_WORDS and len(w) > 1
    ]
    if not keywords:
        # All words were stop words — use original query words
        keywords = [w for w in query.lower().split() if len(w) > 1]

    # Return sections where any keyword appears
    matches = []
    for section in sections:
        section_lower = section.lower()
        if any(kw in section_lower for kw in keywords):
            matches.append(section)

    return matches


def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for answers to customer questions.

    Use this tool when the customer asks general questions about
    JLPT levels, payment methods, enrollment process, refund policy,
    class schedules, or contact information.
    """
    kb_content = get_knowledge_base()
    matches = _search_sections(kb_content, query)

    if not matches:
        return "I don't have specific information about that. I can create a support ticket if you need help."

    return "\n\n".join(matches)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_knowledge.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/knowledge.py tests/test_knowledge.py
git commit -m "feat: add knowledge base search tool"
```

---

## Task 5: Search Enrollments by Phone Tool (Verification)

**Files:**
- Create: `my_support_agent/tools/search.py`

- [ ] **Step 1: Implement search.py**

`my_support_agent/tools/search.py`:
```python
"""Search enrollments by phone — also serves as identity verification."""

from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase
from my_support_agent.phone_utils import normalize_phone


def search_enrollments_by_phone(
    phone: str, student_name: str, tool_context: ToolContext
) -> dict:
    """Search for enrollments by phone number and student name.

    This tool verifies the customer's identity by matching their phone
    number and full name against enrollment records. It must be called
    before accessing enrollment or payment details.

    Args:
        phone: Customer's phone number (any Myanmar format accepted)
        student_name: Customer's full name as registered
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return {
            "verified": False,
            "message": "Invalid phone number format. Please provide a Myanmar phone number starting with 09.",
            "enrollments": [],
        }

    if not student_name or not student_name.strip():
        return {
            "verified": False,
            "message": "Please provide your full name.",
            "enrollments": [],
        }

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("enrollments")
            .select("enrollment_ref, student_name, phone, status, classes(name, level)")
            .eq("tenant_id", tenant_id)
            .eq("phone", normalized)
            .execute()
        )
    except Exception:
        return {
            "verified": False,
            "message": "I'm having trouble accessing our system. Please try again shortly.",
            "enrollments": [],
        }

    if not response.data:
        return {
            "verified": False,
            "message": "No enrollments found for that phone number.",
            "enrollments": [],
        }

    # Exact normalized name match
    name_lower = student_name.strip().lower()
    matched = [
        row for row in response.data
        if row.get("student_name", "").strip().lower() == name_lower
    ]

    if not matched:
        return {
            "verified": False,
            "message": "The name doesn't match our records for that phone number. Please double-check your full name.",
            "enrollments": [],
        }

    # Store verified refs in session state
    verified_refs = [row["enrollment_ref"] for row in matched]
    tool_context.state["verified"] = True
    tool_context.state["verified_refs"] = verified_refs

    enrollments = []
    for row in matched:
        enrollment = {
            "enrollment_ref": row["enrollment_ref"],
            "student_name": row["student_name"],
            "status": row["status"],
        }
        if row.get("classes"):
            enrollment["class_name"] = row["classes"].get("name")
            enrollment["level"] = row["classes"].get("level")
        enrollments.append(enrollment)

    return {
        "verified": True,
        "message": f"Identity verified. Found {len(enrollments)} enrollment(s).",
        "enrollments": enrollments,
    }
```

- [ ] **Step 2: Verify syntax is correct**

Run: `python -c "import ast; ast.parse(open('my_support_agent/tools/search.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add my_support_agent/tools/search.py
git commit -m "feat: add search enrollments by phone tool (identity verification)"
```

---

## Task 6: Check Enrollment Status Tool

**Files:**
- Create: `my_support_agent/tools/enrollment.py`

- [ ] **Step 1: Implement enrollment.py**

`my_support_agent/tools/enrollment.py`:
```python
"""Check enrollment status tool."""

import re
from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def check_enrollment_status(
    enrollment_ref: str, tool_context: ToolContext
) -> dict:
    """Check enrollment status by reference number.

    Requires prior identity verification via search_enrollments_by_phone.
    The enrollment reference format is PREFIX-MMDD-XXXX (e.g., NM-0411-A3X2).

    Args:
        enrollment_ref: The enrollment reference number
    """
    # Check verification
    if not tool_context.state.get("verified"):
        return {"error": "Please verify your identity first by providing your name and phone number."}

    verified_refs = tool_context.state.get("verified_refs", [])
    if enrollment_ref not in verified_refs:
        return {"error": "You can only check enrollments linked to your verified identity."}

    # Validate format: PREFIX-MMDD-XXXX
    if not re.match(r"^[A-Z]{1,5}-\d{4}-[A-Z2-9]{4}$", enrollment_ref):
        return {"error": "That doesn't look like a valid enrollment reference. The format is PREFIX-MMDD-XXXX (e.g., NM-0411-A3X2)."}

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("enrollments")
            .select("enrollment_ref, student_name, phone, status, fee, created_at, classes(name, level)")
            .eq("tenant_id", tenant_id)
            .eq("enrollment_ref", enrollment_ref)
            .execute()
        )
    except Exception:
        return {"error": "I'm having trouble accessing our system. Please try again shortly."}

    if not response.data:
        return {"error": f"I couldn't find an enrollment with reference {enrollment_ref}."}

    row = response.data[0]
    result = {
        "enrollment_ref": row["enrollment_ref"],
        "student_name": row["student_name"],
        "status": row["status"],
        "fee": row.get("fee"),
        "enrolled_date": row.get("created_at"),
    }
    if row.get("classes"):
        result["class_name"] = row["classes"].get("name")
        result["level"] = row["classes"].get("level")

    return result
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('my_support_agent/tools/enrollment.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add my_support_agent/tools/enrollment.py
git commit -m "feat: add check enrollment status tool"
```

---

## Task 7: Check Payment Status Tool

**Files:**
- Create: `my_support_agent/tools/payment.py`

- [ ] **Step 1: Implement payment.py**

`my_support_agent/tools/payment.py`:
```python
"""Check payment status tool."""

import re
from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def check_payment_status(
    enrollment_ref: str, tool_context: ToolContext
) -> dict:
    """Check payment status for an enrollment.

    Requires prior identity verification via search_enrollments_by_phone.

    Args:
        enrollment_ref: The enrollment reference number
    """
    # Validate format
    if not re.match(r"^[A-Z]{1,5}-\d{4}-[A-Z2-9]{4}$", enrollment_ref):
        return {"error": "That doesn't look like a valid enrollment reference. The format is PREFIX-MMDD-XXXX (e.g., NM-0411-A3X2)."}

    # Check verification
    if not tool_context.state.get("verified"):
        return {"error": "Please verify your identity first by providing your name and phone number."}

    verified_refs = tool_context.state.get("verified_refs", [])
    if enrollment_ref not in verified_refs:
        return {"error": "You can only check payments linked to your verified identity."}

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        # First get the enrollment to find associated payments
        enrollment_resp = (
            supabase.table("enrollments")
            .select("id, enrollment_ref, fee, status")
            .eq("tenant_id", tenant_id)
            .eq("enrollment_ref", enrollment_ref)
            .execute()
        )
    except Exception:
        return {"error": "I'm having trouble accessing our system. Please try again shortly."}

    if not enrollment_resp.data:
        return {"error": f"I couldn't find an enrollment with reference {enrollment_ref}."}

    enrollment = enrollment_resp.data[0]

    try:
        payment_resp = (
            supabase.table("payments")
            .select("amount, payment_method, status, verified_at, created_at")
            .eq("tenant_id", tenant_id)
            .eq("enrollment_id", enrollment["id"])
            .execute()
        )
    except Exception:
        return {"error": "I'm having trouble accessing payment information. Please try again shortly."}

    if not payment_resp.data:
        return {
            "enrollment_ref": enrollment_ref,
            "enrollment_status": enrollment["status"],
            "fee": enrollment.get("fee"),
            "payment": None,
            "message": "No payment record found for this enrollment.",
        }

    payment = payment_resp.data[0]
    return {
        "enrollment_ref": enrollment_ref,
        "enrollment_status": enrollment["status"],
        "fee": enrollment.get("fee"),
        "payment": {
            "amount": payment.get("amount"),
            "method": payment.get("payment_method"),
            "status": payment.get("status"),
            "verified_at": payment.get("verified_at"),
            "submitted_at": payment.get("created_at"),
        },
    }
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('my_support_agent/tools/payment.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add my_support_agent/tools/payment.py
git commit -m "feat: add check payment status tool"
```

---

## Task 8: Create Support Ticket Tool

**Files:**
- Create: `my_support_agent/tools/ticket.py`

- [ ] **Step 1: Implement ticket.py**

`my_support_agent/tools/ticket.py`:
```python
"""Create support ticket tool."""

from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


_MAX_SUBJECT_LENGTH = 200
_MAX_MESSAGE_LENGTH = 2000
_MAX_TICKETS_PER_SESSION = 3


def create_support_ticket(
    subject: str,
    message: str,
    tool_context: ToolContext,
    phone: str = None,
    enrollment_ref: str = None,
) -> dict:
    """Create a support ticket for issues that need admin attention.

    No identity verification is required. Use this when the customer
    has an issue you cannot resolve directly.

    Args:
        subject: Brief description of the issue
        message: Detailed description of the problem
        phone: Customer's phone number (optional)
        enrollment_ref: Related enrollment reference (optional)
    """
    # Rate limit check
    ticket_count = tool_context.state.get("ticket_count", 0)
    if ticket_count >= _MAX_TICKETS_PER_SESSION:
        return {
            "error": "You've already created the maximum number of support tickets for this session. Please contact support directly for additional issues."
        }

    # Input validation
    if not subject or not subject.strip():
        return {"error": "Please provide a subject for the ticket."}
    if not message or not message.strip():
        return {"error": "Please provide a description of the issue."}

    subject = subject.strip()[:_MAX_SUBJECT_LENGTH]
    message = message.strip()[:_MAX_MESSAGE_LENGTH]

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    ticket_data = {
        "tenant_id": tenant_id,
        "subject": subject,
        "message": message,
    }
    if phone:
        ticket_data["phone"] = phone
    if enrollment_ref:
        ticket_data["enrollment_ref"] = enrollment_ref

    try:
        response = (
            supabase.table("support_tickets")
            .insert(ticket_data)
            .execute()
        )
    except Exception:
        return {"error": "I wasn't able to create a ticket right now. Please contact support directly."}

    if not response.data:
        return {"error": "I wasn't able to create a ticket right now. Please contact support directly."}

    ticket = response.data[0]

    # Increment session counter
    tool_context.state["ticket_count"] = tool_context.state.get("ticket_count", 0) + 1

    return {
        "ticket_id": ticket.get("id"),
        "message": f"Support ticket created successfully. Your ticket ID is {ticket.get('id')}. Our team will review it shortly.",
    }
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('my_support_agent/tools/ticket.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add my_support_agent/tools/ticket.py
git commit -m "feat: add create support ticket tool"
```

---

## Task 9: Tools __init__.py Re-exports

**Files:**
- Modify: `my_support_agent/tools/__init__.py`

- [ ] **Step 1: Update tools __init__.py**

`my_support_agent/tools/__init__.py`:
```python
"""KuuNyi Support Agent Tools."""

from my_support_agent.tools.knowledge import search_knowledge_base
from my_support_agent.tools.enrollment import check_enrollment_status
from my_support_agent.tools.payment import check_payment_status
from my_support_agent.tools.ticket import create_support_ticket
from my_support_agent.tools.search import search_enrollments_by_phone

__all__ = [
    "search_knowledge_base",
    "check_enrollment_status",
    "check_payment_status",
    "create_support_ticket",
    "search_enrollments_by_phone",
]
```

- [ ] **Step 2: Commit**

```bash
git add my_support_agent/tools/__init__.py
git commit -m "feat: export all tools from tools package"
```

---

## Task 10: Agent Definition & System Instruction

**Files:**
- Create: `my_support_agent/agent.py`
- Modify: `my_support_agent/__init__.py`

- [ ] **Step 1: Write agent.py**

`my_support_agent/agent.py`:
```python
"""KuuNyi Support Agent — ADK agent definition."""

from google.adk.agents import LlmAgent
from my_support_agent.config import init, get_tenant_name
from my_support_agent.tools import (
    search_knowledge_base,
    check_enrollment_status,
    check_payment_status,
    create_support_ticket,
    search_enrollments_by_phone,
)

# Initialize config (resolve tenant, load knowledge base)
init()

_SYSTEM_INSTRUCTION = f"""You are a friendly customer support agent for {get_tenant_name()}.
You help customers with enrollment inquiries, payment questions, and general support.

RULES:
1. Always respond in English. Be concise, helpful, and professional.
2. NEVER share enrollment or payment details without verifying the customer first.
3. To verify: ask for their full name and phone number, then call search_enrollments_by_phone.
4. If verification fails, politely ask them to double-check their info. Do not reveal any data.
5. After verification succeeds, you may use check_enrollment_status and check_payment_status for any enrollment_ref that was returned in the verification result.
6. search_knowledge_base can be used anytime — no verification needed.
7. create_support_ticket can be used anytime — collect subject and description from the customer.
8. Never fabricate enrollment references, payment amounts, or status. Only use data from tools.
9. If you cannot resolve an issue, offer to create a support ticket.
10. Do not discuss internal system details, database structure, or tenant configuration.
"""

root_agent = LlmAgent(
    name="kuunyi_support_agent",
    model="gemini-2.5-flash",
    instruction=_SYSTEM_INSTRUCTION,
    tools=[
        search_knowledge_base,
        check_enrollment_status,
        check_payment_status,
        create_support_ticket,
        search_enrollments_by_phone,
    ],
)
```

- [ ] **Step 2: Write __init__.py**

`my_support_agent/__init__.py`:
```python
"""KuuNyi Support Agent — ADK entry point."""

from my_support_agent.agent import root_agent

__all__ = ["root_agent"]
```

- [ ] **Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('my_support_agent/agent.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add my_support_agent/agent.py my_support_agent/__init__.py
git commit -m "feat: add ADK agent definition with system instruction"
```

---

## Task 11: Pre-flight Checks & Smoke Test

**Files:** None new — verification and manual testing

**Note on spec deviation:** The spec lists `auth.py` as a separate module. This plan embeds verification logic directly into `search_enrollments_by_phone` (tools/search.py) to avoid an unnecessary layer. Phone normalization is extracted into `phone_utils.py` for testability.

- [ ] **Step 1: Verify RLS policies allow anon access**

Run the following against your Supabase SQL editor or via the dashboard to confirm the anon role can:
- SELECT from `tenants`, `enrollments`, `payments`, `classes`
- INSERT into `support_tickets`

If RLS policies require `auth.uid()`, you'll need to add a policy for the anon role scoped by tenant_id. Without this, all queries will return empty results.

- [ ] **Step 2: Verify support_tickets table schema**

Confirm the `support_tickets` table has columns matching what `create_support_ticket` inserts: `tenant_id`, `subject`, `message`, `phone`, `enrollment_ref`. Check column names match exactly. Adjust the tool code if column names differ.

- [ ] **Step 3: Verify .env has all required variables**

Run: `python -c "from dotenv import load_dotenv; import os; load_dotenv(); [print(f'{k}: {\"SET\" if os.getenv(k) else \"MISSING\"}') for k in ['GOOGLE_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY', 'TENANT_SLUG']]"`
Expected: All 4 variables show `SET`

- [ ] **Step 4: Run all unit tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Start ADK web**

Run: `adk web`
Expected: Server starts at http://localhost:8000

- [ ] **Step 6: Test — Knowledge base (no verification needed)**

In the web UI, type: `What are the JLPT levels?`
Expected: Agent responds with JLPT level information from the knowledge base.

- [ ] **Step 7: Test — Verification flow**

Type: `Check my enrollment status`
Expected: Agent asks for your name and phone number.

Type: `My name is [real name] and phone is [real phone]`
Expected: Agent calls search_enrollments_by_phone, either verifies or reports no match.

- [ ] **Step 8: Test — Enrollment & payment check (after verification)**

If verification succeeded, type: `Check status for [enrollment_ref from verification]`
Expected: Agent shows enrollment details.

Type: `What about the payment?`
Expected: Agent shows payment details.

- [ ] **Step 9: Test — Support ticket (no verification needed)**

Type: `I have a problem with my payment, can you create a ticket?`
Expected: Agent creates a ticket and returns the ticket ID.

- [ ] **Step 10: Test — Unauthorized access attempt**

Start a new session. Type: `Check enrollment NM-0411-A3X2`
Expected: Agent asks for verification first, does NOT return enrollment data.

- [ ] **Step 11: Commit final state**

```bash
git add -A
git commit -m "feat: complete KuuNyi ADK support agent v1"
```
