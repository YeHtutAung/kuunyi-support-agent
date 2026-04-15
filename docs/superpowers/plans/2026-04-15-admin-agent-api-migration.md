# Admin Agent API Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `kuunyi_admin_agent` from direct Supabase queries to calling the KuuNyi Next.js admin API, and add new payment verification and student detail tools.

**Architecture:** A new `api_client.py` module provides a single `call_admin_api()` function used by all admin tools. `config.py` gains a lightweight `init_admin()` that skips Supabase. All existing admin tools are rewritten to call the API; two new tools (`payments.py`, `student_detail.py`) are added.

**Tech Stack:** Python 3.11+, `requests`, `google-adk`, `pytest`, `unittest.mock`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `my_support_agent/api_client.py` | **Create** | HTTP client: auth headers, timeout, error mapping |
| `my_support_agent/config.py` | **Modify** | Add `init_admin()` — no Supabase, reads `TENANT_NAME` + `AGENT_SECRET` + `ADMIN_API_BASE_URL` |
| `my_support_agent/tools/seats.py` | **Rewrite** | `get_seats_overview()` via `GET /api/intakes` + `/classes` |
| `my_support_agent/tools/summary.py` | **Rewrite** | `get_stats()` via `GET /api/admin/stats` (replaces `get_summary`) |
| `my_support_agent/tools/admin_enrollments.py` | **Rewrite** | `list_enrollments()` via `GET /api/admin/students` |
| `my_support_agent/tools/update_class.py` | **Rewrite** | Remove `get_class_details`; `confirm_update` calls `PATCH /api/classes/[id]` |
| `my_support_agent/tools/student_detail.py` | **Create** | `get_student_detail()` via `GET /api/admin/students/[id]` |
| `my_support_agent/tools/payments.py` | **Create** | `get_pending_payments`, `verify_payment`, `confirm_payment_action`, `cancel_payment_action` |
| `my_support_agent/tools/__init__.py` | **Modify** | Export new tools, remove `get_class_details` and `get_summary` |
| `my_support_agent/admin_agent.py` | **Modify** | Call `init_admin()`, update tool list and system instruction |
| `tests/test_api_client.py` | **Create** | Tests for `api_client.py` |
| `tests/test_seats.py` | **Rewrite** | Replace Supabase mocks with `call_admin_api` mocks |
| `tests/test_summary.py` | **Rewrite** | Replace Supabase mocks with `call_admin_api` mocks |
| `tests/test_update_class.py` | **Rewrite** | Replace Supabase mocks with `call_admin_api` mocks; remove `get_class_details` tests |
| `tests/test_admin_enrollments.py` | **Create** | Tests for migrated `list_enrollments` |
| `tests/test_student_detail.py` | **Create** | Tests for `get_student_detail` |
| `tests/test_payments.py` | **Create** | Tests for all four payment tools |

---

## Task 1: Create `api_client.py`

**Files:**
- Create: `my_support_agent/api_client.py`
- Create: `tests/test_api_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_client.py`:

```python
"""Tests for api_client."""

import os
import pytest
from unittest.mock import MagicMock, patch
import my_support_agent.api_client as api_client_module


def _reset():
    """Reset module-level state between tests."""
    api_client_module._base_url = None
    api_client_module._secret = None


# ---------------------------------------------------------------------------
# init_api_client
# ---------------------------------------------------------------------------

def test_init_raises_if_base_url_missing():
    _reset()
    with patch.dict(os.environ, {"AGENT_SECRET": "s3cr3t"}, clear=False):
        os.environ.pop("ADMIN_API_BASE_URL", None)
        with pytest.raises(RuntimeError, match="ADMIN_API_BASE_URL"):
            api_client_module.init_api_client()


def test_init_raises_if_secret_missing():
    _reset()
    with patch.dict(os.environ, {"ADMIN_API_BASE_URL": "https://example.com"}, clear=False):
        os.environ.pop("AGENT_SECRET", None)
        with pytest.raises(RuntimeError, match="AGENT_SECRET"):
            api_client_module.init_api_client()


def test_init_raises_if_url_not_https():
    _reset()
    with patch.dict(os.environ, {
        "ADMIN_API_BASE_URL": "http://example.com",
        "AGENT_SECRET": "s3cr3t",
    }):
        with pytest.raises(RuntimeError, match="HTTPS"):
            api_client_module.init_api_client()


def test_init_strips_trailing_slash():
    _reset()
    with patch.dict(os.environ, {
        "ADMIN_API_BASE_URL": "https://example.com/",
        "AGENT_SECRET": "s3cr3t",
    }):
        api_client_module.init_api_client()
    assert api_client_module._base_url == "https://example.com"


# ---------------------------------------------------------------------------
# call_admin_api
# ---------------------------------------------------------------------------

def _setup_client(base_url="https://example.com", secret="s3cr3t", tenant="test-tenant"):
    _reset()
    api_client_module._base_url = base_url
    api_client_module._secret = secret
    return tenant


def test_call_injects_auth_headers():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp) as mock_req:
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            api_client_module.call_admin_api("GET", "/api/admin/stats")

    headers = mock_req.call_args.kwargs["headers"]
    assert headers["x-agent-secret"] == "s3cr3t"
    assert headers["x-tenant-slug"] == "nihon-moment"


def test_call_wraps_list_response():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": "1"}, {"id": "2"}]

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/intakes")

    assert result == {"data": [{"id": "1"}, {"id": "2"}]}


def test_call_returns_dict_response_as_is():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"total": 5}

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")

    assert result == {"total": 5}


def test_call_returns_error_on_timeout():
    import requests as req_lib
    _setup_client()
    with patch("my_support_agent.api_client._requests.request", side_effect=req_lib.Timeout):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert result == {"error": "Request timed out. Please try again."}


def test_call_returns_error_on_network_failure():
    import requests as req_lib
    _setup_client()
    with patch("my_support_agent.api_client._requests.request", side_effect=req_lib.RequestException):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert result == {"error": "Unable to reach the API. Please try again shortly."}


def test_call_returns_error_on_401():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "Authentication failed" in result["error"]


def test_call_returns_error_on_403():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 403
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "Authentication failed" in result["error"]


def test_call_returns_error_on_404():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/students/bad-id")
    assert result == {"error": "Not found."}


def test_call_returns_error_on_500():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "500" in result["error"]


def test_secret_not_in_error_message():
    _setup_client(secret="super-secret-value")
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "super-secret-value" not in result.get("error", "")
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_api_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'my_support_agent.api_client'`

- [ ] **Step 3: Create `my_support_agent/api_client.py`**

```python
"""Shared HTTP client for KuuNyi admin API."""

import os
import requests as _requests

_base_url: str | None = None
_secret: str | None = None


def init_api_client() -> None:
    """Initialize the API client. Called once at startup via init_admin()."""
    global _base_url, _secret

    base_url = os.environ.get("ADMIN_API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("AGENT_SECRET")

    if not base_url:
        raise RuntimeError("ADMIN_API_BASE_URL environment variable must be set.")
    if not secret:
        raise RuntimeError("AGENT_SECRET environment variable must be set.")
    if not base_url.startswith("https://"):
        raise RuntimeError("ADMIN_API_BASE_URL must use HTTPS.")

    _base_url = base_url
    _secret = secret


def call_admin_api(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Make an authenticated request to the KuuNyi admin API.

    Returns a dict on success. Returns {"error": "..."} on any failure.
    List responses are wrapped as {"data": [...]}.
    The AGENT_SECRET is never included in error output.
    """
    if not _base_url or not _secret:
        raise RuntimeError("API client not initialized. Call init_api_client() first.")

    tenant_slug = os.environ.get("TENANT_SLUG", "")
    headers = {
        "x-agent-secret": _secret,
        "x-tenant-slug": tenant_slug,
    }

    try:
        response = _requests.request(
            method.upper(),
            f"{_base_url}{path}",
            headers=headers,
            params=params,
            json=json,
            timeout=10,
        )
    except _requests.Timeout:
        return {"error": "Request timed out. Please try again."}
    except _requests.RequestException:
        return {"error": "Unable to reach the API. Please try again shortly."}

    if response.status_code in (401, 403):
        return {"error": "Authentication failed. Check AGENT_SECRET configuration."}
    if response.status_code == 404:
        return {"error": "Not found."}
    if not response.ok:
        return {"error": f"API request failed: {response.status_code}."}

    data = response.json()
    if isinstance(data, list):
        return {"data": data}
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_api_client.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/api_client.py tests/test_api_client.py
git commit -m "feat: add shared api_client module for admin API calls"
```

---

## Task 2: Update `config.py` — add `init_admin()`

**Files:**
- Modify: `my_support_agent/config.py`

- [ ] **Step 1: Read the current file**

Read `my_support_agent/config.py` to see current state before editing.

- [ ] **Step 2: Add `init_admin()` to `config.py`**

Add after the existing `init()` function:

```python
def init_admin() -> None:
    """Lightweight init for admin agent — no Supabase required.

    Reads TENANT_SLUG and optionally TENANT_NAME from env, then
    initialises the shared API client (ADMIN_API_BASE_URL + AGENT_SECRET).
    """
    global _tenant_slug, _tenant_name

    _tenant_slug = os.environ.get("TENANT_SLUG")
    if not _tenant_slug:
        raise RuntimeError("TENANT_SLUG environment variable must be set.")

    _tenant_name = os.environ.get("TENANT_NAME", _tenant_slug)

    from my_support_agent.api_client import init_api_client
    init_api_client()
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```
pytest tests/ -v
```

Expected: all existing tests PASS (test_api_client, test_knowledge, test_phone_utils pass; Supabase-dependent tests may be skipped or still pass via mocks)

- [ ] **Step 4: Commit**

```bash
git add my_support_agent/config.py
git commit -m "feat: add init_admin() to config for Supabase-free admin agent startup"
```

---

## Task 3: Migrate `seats.py`

**Files:**
- Rewrite: `my_support_agent/tools/seats.py`
- Rewrite: `tests/test_seats.py`

- [ ] **Step 1: Rewrite the tests**

Replace `tests/test_seats.py` entirely:

```python
"""Tests for get_seats_overview (API-backed)."""

from unittest.mock import patch, call


def _intakes_response(intake_id="intake-1"):
    return {"data": [{"id": intake_id, "status": "open", "name": "April 2026"}]}


def _classes_response(rows):
    return {"data": rows}


def _patch_api(side_effects):
    return patch(
        "my_support_agent.tools.seats.call_admin_api",
        side_effect=side_effects,
    )


# ---------------------------------------------------------------------------
# Status labelling
# ---------------------------------------------------------------------------

def test_status_available():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 20, "seat_remaining": 10,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "available"
    assert result["classes"][0]["enrolled"] == 10
    assert result["classes"][0]["class_id"] == "c1"


def test_status_critical():
    # 17/20 = 85% → critical
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N4", "seat_total": 20, "seat_remaining": 3,
             "fee_mmk": 60000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "critical"


def test_status_full():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N3", "seat_total": 15, "seat_remaining": 0,
             "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "full"


def test_multiple_classes_mixed_status():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 10, "fee_mmk": 50000, "mode": "offline"},
            {"id": "c2", "level": "N4", "seat_total": 10, "seat_remaining": 1,  "fee_mmk": 60000, "mode": "offline"},
            {"id": "c3", "level": "N3", "seat_total": 10, "seat_remaining": 0,  "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    statuses = {c["class_name"]: c["status"] for c in result["classes"]}
    assert statuses["N5"] == "available"
    assert statuses["N4"] == "critical"
    assert statuses["N3"] == "full"
    assert result["total"] == 3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_no_open_intake_returns_error():
    with _patch_api([{"data": [{"id": "i1", "status": "closed"}]}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result
    assert "No open intake" in result["error"]


def test_intakes_api_error_propagates():
    with _patch_api([{"error": "Authentication failed. Check AGENT_SECRET configuration."}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_classes_api_error_propagates():
    with _patch_api([
        _intakes_response(),
        {"error": "API request failed: 500."},
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_calls_correct_endpoints():
    with _patch_api([
        _intakes_response("intake-xyz"),
        _classes_response([]),
    ]) as mock_api:
        from my_support_agent.tools.seats import get_seats_overview
        get_seats_overview()
    assert mock_api.call_args_list[0] == call("GET", "/api/intakes")
    assert mock_api.call_args_list[1] == call("GET", "/api/intakes/intake-xyz/classes")
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_seats.py -v
```

Expected: FAIL — tests import old function that still uses Supabase

- [ ] **Step 3: Rewrite `my_support_agent/tools/seats.py`**

```python
"""Seats overview tool — class capacity and fill status."""

from my_support_agent.api_client import call_admin_api


def get_seats_overview() -> dict:
    """Get seat availability across all classes for the current open intake.

    Makes two API calls: one to find the open intake, one to list its classes.
    Returns each class with enrolled count, capacity, price, mode, and a status
    label: 'full' (seat_remaining == 0), 'critical' (>= 85% full), or 'available'.
    """
    intakes_resp = call_admin_api("GET", "/api/intakes")
    if "error" in intakes_resp:
        return intakes_resp

    open_intakes = [i for i in intakes_resp.get("data", []) if i.get("status") == "open"]
    if not open_intakes:
        return {"error": "No open intake found."}

    intake_id = open_intakes[0]["id"]

    classes_resp = call_admin_api("GET", f"/api/intakes/{intake_id}/classes")
    if "error" in classes_resp:
        return classes_resp

    classes = []
    for row in classes_resp.get("data", []):
        seat_total = row.get("seat_total") or 0
        seat_remaining = row.get("seat_remaining") or 0
        enrolled = seat_total - seat_remaining

        if seat_total > 0 and seat_remaining == 0:
            status = "full"
        elif seat_total > 0 and enrolled / seat_total >= 0.85:
            status = "critical"
        else:
            status = "available"

        classes.append({
            "class_id": row["id"],
            "class_name": row.get("level"),
            "enrolled": enrolled,
            "capacity": seat_total,
            "seats_remaining": seat_remaining,
            "price_mmk": row.get("fee_mmk"),
            "status": status,
            "mode": row.get("mode"),
        })

    return {"classes": classes, "total": len(classes)}
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_seats.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/seats.py tests/test_seats.py
git commit -m "feat: migrate get_seats_overview to admin API"
```

---

## Task 4: Migrate `summary.py` → `get_stats()`

**Files:**
- Rewrite: `my_support_agent/tools/summary.py`
- Rewrite: `tests/test_summary.py`

- [ ] **Step 1: Rewrite the tests**

Replace `tests/test_summary.py` entirely:

```python
"""Tests for get_stats (API-backed)."""

from unittest.mock import patch


STATS_RESPONSE = {
    "total_enrollments": 50,
    "confirmed_count": 30,
    "pending_payment_count": 10,
    "payment_submitted_count": 5,
    "total_revenue_mmk": 15000000,
    "seats_by_class": [
        {"level": "N5", "seat_remaining": 12, "seat_total": 30},
    ],
}


def test_get_stats_calls_correct_endpoint():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value=STATS_RESPONSE) as mock_api:
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    mock_api.assert_called_once_with("GET", "/api/admin/stats")
    assert result["total_enrollments"] == 50


def test_get_stats_returns_full_response():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value=STATS_RESPONSE):
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    assert result["confirmed_count"] == 30
    assert result["total_revenue_mmk"] == 15000000
    assert len(result["seats_by_class"]) == 1


def test_get_stats_forwards_error():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value={"error": "Authentication failed."}):
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_summary.py -v
```

Expected: FAIL — old `get_summary` function still present

- [ ] **Step 3: Rewrite `my_support_agent/tools/summary.py`**

```python
"""Stats tool — admin dashboard snapshot."""

from my_support_agent.api_client import call_admin_api


def get_stats() -> dict:
    """Get current enrollment and revenue statistics for the tenant.

    Returns a real-time snapshot: total enrollments, counts by status
    (confirmed, pending_payment, payment_submitted), total revenue, and
    seat availability across all classes.
    """
    return call_admin_api("GET", "/api/admin/stats")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_summary.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/summary.py tests/test_summary.py
git commit -m "feat: migrate summary tool to get_stats via admin API"
```

---

## Task 5: Migrate `admin_enrollments.py`

**Files:**
- Rewrite: `my_support_agent/tools/admin_enrollments.py`
- Create: `tests/test_admin_enrollments.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_admin_enrollments.py`:

```python
"""Tests for list_enrollments (API-backed)."""

from unittest.mock import patch, call


ENROLLMENTS_RESPONSE = {
    "data": [
        {
            "enrollment_id": "uuid-1",
            "enrollment_ref": "NM-0411-A3X2",
            "student_name_en": "Mg Mg",
            "phone": "09123456789",
            "class_level": "N4",
            "status": "confirmed",
            "enrolled_at": "2026-04-01T10:00:00Z",
            "intake_name": "April 2026 Intake",
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
}


def test_no_filters_calls_with_defaults():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments()
    mock_api.assert_called_once_with(
        "GET", "/api/admin/students", params={"page": 1, "page_size": 20}
    )


def test_status_filter_included_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(status="confirmed")
    params = mock_api.call_args.kwargs["params"]
    assert params["status"] == "confirmed"


def test_search_filter_included_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(search="Mg Mg")
    params = mock_api.call_args.kwargs["params"]
    assert params["search"] == "Mg Mg"


def test_page_param_forwarded():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(page=3)
    params = mock_api.call_args.kwargs["params"]
    assert params["page"] == 3


def test_no_status_not_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments()
    params = mock_api.call_args.kwargs["params"]
    assert "status" not in params
    assert "search" not in params


def test_returns_api_response():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE):
        from my_support_agent.tools.admin_enrollments import list_enrollments
        result = list_enrollments()
    assert result["total"] == 1
    assert result["data"][0]["student_name_en"] == "Mg Mg"


def test_forwards_api_error():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value={"error": "Authentication failed."}):
        from my_support_agent.tools.admin_enrollments import list_enrollments
        result = list_enrollments()
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_admin_enrollments.py -v
```

Expected: FAIL — old function uses Supabase, not `call_admin_api`

- [ ] **Step 3: Rewrite `my_support_agent/tools/admin_enrollments.py`**

```python
"""Admin enrollment listing tool."""

from my_support_agent.api_client import call_admin_api


def list_enrollments(
    status: str = None,
    search: str = None,
    page: int = 1,
) -> dict:
    """List enrollments for the current tenant.

    Args:
        status: Optional filter — 'pending_payment', 'payment_submitted',
                'partial_payment', 'confirmed', 'rejected'.
        search: Optional partial match on student name or phone.
        page: Page number, 1-based (default 1). Page size is fixed at 20.
    """
    params: dict = {"page": page, "page_size": 20}
    if status:
        params["status"] = status
    if search:
        params["search"] = search

    return call_admin_api("GET", "/api/admin/students", params=params)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_admin_enrollments.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/admin_enrollments.py tests/test_admin_enrollments.py
git commit -m "feat: migrate list_enrollments to admin API with search support"
```

---

## Task 6: Migrate `update_class.py`

**Files:**
- Rewrite: `my_support_agent/tools/update_class.py`
- Rewrite: `tests/test_update_class.py`

- [ ] **Step 1: Rewrite the tests**

Replace `tests/test_update_class.py` entirely:

```python
"""Tests for update_class, confirm_update, cancel_update (API-backed)."""

from unittest.mock import MagicMock, patch


CLASS_ID = "class-uuid-001"


def _make_context(initial_state=None):
    ctx = MagicMock()
    ctx.state = initial_state or {}
    return ctx


# ---------------------------------------------------------------------------
# update_class — stages to state, does NOT call API
# ---------------------------------------------------------------------------

def test_update_class_stages_capacity():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, capacity=25)

    assert result["confirmation_required"] is True
    assert "25" in result["summary"]
    pending = ctx.state["pending_update"]
    assert pending["class_id"] == CLASS_ID
    assert pending["capacity"] == 25


def test_update_class_stages_price():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, price_mmk=75000)

    assert ctx.state["pending_update"]["price_mmk"] == 75000
    assert "75000" in result["summary"]


def test_update_class_stages_status():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, status="closed")

    assert ctx.state["pending_update"]["status"] == "closed"
    assert "closed" in result["summary"]


def test_update_class_no_fields_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx)

    assert "error" in result
    assert not ctx.state.get("pending_update")


def test_update_class_does_not_call_api():
    ctx = _make_context()
    with patch("my_support_agent.tools.update_class.call_admin_api") as mock_api:
        from my_support_agent.tools.update_class import update_class
        update_class(CLASS_ID, ctx, capacity=25)
    mock_api.assert_not_called()


# ---------------------------------------------------------------------------
# confirm_update — calls PATCH API
# ---------------------------------------------------------------------------

def test_confirm_update_calls_patch_api():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": 25,
            "price_mmk": None,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID, "seat_total": 25}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        result = confirm_update(ctx)

    mock_api.assert_called_once_with(
        "PATCH", f"/api/classes/{CLASS_ID}", json={"seat_total": 25}
    )
    assert result["success"] is True
    assert not ctx.state.get("pending_update")


def test_confirm_update_sends_price():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": None,
            "price_mmk": 80000,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        confirm_update(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body == {"fee_mmk": 80000}


def test_confirm_update_sends_status():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": None,
            "price_mmk": None,
            "status": "closed",
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        confirm_update(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body == {"status": "closed"}


def test_confirm_update_no_pending_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.update_class import confirm_update
    result = confirm_update(ctx)
    assert "error" in result


def test_confirm_update_forwards_api_error():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": 25,
            "price_mmk": None,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"error": "Not found."}):
        from my_support_agent.tools.update_class import confirm_update
        result = confirm_update(ctx)
    assert "error" in result


# ---------------------------------------------------------------------------
# cancel_update — clears state
# ---------------------------------------------------------------------------

def test_cancel_update_clears_state():
    ctx = _make_context({
        "pending_update": {"class_id": CLASS_ID, "capacity": 25, "price_mmk": None, "status": None}
    })
    from my_support_agent.tools.update_class import cancel_update
    result = cancel_update(ctx)
    assert result["cancelled"] is True
    assert not ctx.state.get("pending_update")


def test_cancel_update_no_pending_is_graceful():
    ctx = _make_context()
    from my_support_agent.tools.update_class import cancel_update
    result = cancel_update(ctx)
    assert "message" in result
    assert "error" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_update_class.py -v
```

Expected: FAIL — `get_class_details` tests removed and old impl still uses Supabase

- [ ] **Step 3: Rewrite `my_support_agent/tools/update_class.py`**

```python
"""Admin tool to update class capacity, price, or status with a confirmation gate."""

from google.adk.tools import ToolContext
from my_support_agent.api_client import call_admin_api


def update_class(
    class_id: str,
    tool_context: ToolContext,
    capacity: int = None,
    price_mmk: int = None,
    status: str = None,
) -> dict:
    """Stage a class update for admin confirmation.

    Does NOT write to the database. Stores the proposed change in
    tool_context.state['pending_update'] and returns a summary for
    the agent to show the admin before they confirm.

    Args:
        class_id: The class UUID to update.
        capacity: New seat capacity (optional).
        price_mmk: New price in MMK (optional).
        status: New class status — 'draft', 'open', 'closed' (optional).
    """
    if capacity is None and price_mmk is None and status is None:
        return {"error": "Provide at least one field to update: capacity, price_mmk, or status."}

    tool_context.state["pending_update"] = {
        "class_id": class_id,
        "capacity": capacity,
        "price_mmk": price_mmk,
        "status": status,
    }

    lines = [f"Proposed update for class ID {class_id}:"]
    if capacity is not None:
        lines.append(f"  • Capacity → {capacity}")
    if price_mmk is not None:
        lines.append(f"  • Price → {price_mmk} MMK")
    if status is not None:
        lines.append(f"  • Status → {status}")
    lines.append("Reply **confirm** to apply or **cancel** to discard.")

    return {"confirmation_required": True, "summary": "\n".join(lines)}


def confirm_update(tool_context: ToolContext) -> dict:
    """Apply the staged class update via the admin API."""
    pending = tool_context.state.get("pending_update")
    if not pending:
        return {"error": "No pending update to confirm."}

    patch_body: dict = {}
    if pending.get("capacity") is not None:
        patch_body["seat_total"] = pending["capacity"]
    if pending.get("price_mmk") is not None:
        patch_body["fee_mmk"] = pending["price_mmk"]
    if pending.get("status") is not None:
        patch_body["status"] = pending["status"]

    if not patch_body:
        tool_context.state["pending_update"] = None
        return {"error": "No fields to apply."}

    result = call_admin_api("PATCH", f"/api/classes/{pending['class_id']}", json=patch_body)
    tool_context.state["pending_update"] = None

    if "error" in result:
        return result

    applied = []
    if "seat_total" in patch_body:
        applied.append(f"capacity → {patch_body['seat_total']}")
    if "fee_mmk" in patch_body:
        applied.append(f"price → {patch_body['fee_mmk']} MMK")
    if "status" in patch_body:
        applied.append(f"status → {patch_body['status']}")

    return {
        "success": True,
        "class_id": pending["class_id"],
        "updated": applied,
        "message": f"Class updated successfully: {', '.join(applied)}.",
    }


def cancel_update(tool_context: ToolContext) -> dict:
    """Discard the staged class update without writing to the database."""
    pending = tool_context.state.get("pending_update")
    if not pending:
        return {"message": "No pending update to cancel."}

    tool_context.state["pending_update"] = None
    return {
        "cancelled": True,
        "message": f"Update for class {pending.get('class_id')} has been cancelled. No changes were made.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_update_class.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/update_class.py tests/test_update_class.py
git commit -m "feat: migrate update_class to admin API, remove get_class_details"
```

---

## Task 7: Create `student_detail.py`

**Files:**
- Create: `my_support_agent/tools/student_detail.py`
- Create: `tests/test_student_detail.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_student_detail.py`:

```python
"""Tests for get_student_detail."""

from unittest.mock import patch

STUDENT_RESPONSE = {
    "enrollment_id": "uuid-1",
    "enrollment_ref": "NM-0411-A3X2",
    "student_name_en": "Mg Mg",
    "student_name_mm": "မောင်မောင်",
    "phone": "09123456789",
    "email": "mg@example.com",
    "nrc_number": "12/MAMANA(N)123456",
    "class_level": "N4",
    "intake_name": "April 2026 Intake",
    "status": "confirmed",
    "fee_mmk": 350000,
    "payment": {
        "id": "pay-uuid-1",
        "status": "verified",
        "amount_mmk": 350000,
        "bank_reference": "TXN123",
        "payer_institution": "KBZ",
        "submitted_at": "2026-04-02T08:00:00Z",
        "verified_at": "2026-04-03T09:00:00Z",
        "proof_signed_url": "https://storage.example.com/proof.jpg",
    },
}


def test_calls_correct_endpoint():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value=STUDENT_RESPONSE) as mock_api:
        from my_support_agent.tools.student_detail import get_student_detail
        get_student_detail("uuid-1")
    mock_api.assert_called_once_with("GET", "/api/admin/students/uuid-1")


def test_returns_student_data():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value=STUDENT_RESPONSE):
        from my_support_agent.tools.student_detail import get_student_detail
        result = get_student_detail("uuid-1")
    assert result["student_name_en"] == "Mg Mg"
    assert result["payment"]["bank_reference"] == "TXN123"


def test_forwards_api_error():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value={"error": "Not found."}):
        from my_support_agent.tools.student_detail import get_student_detail
        result = get_student_detail("nonexistent-id")
    assert result == {"error": "Not found."}
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_student_detail.py -v
```

Expected: `ModuleNotFoundError: No module named 'my_support_agent.tools.student_detail'`

- [ ] **Step 3: Create `my_support_agent/tools/student_detail.py`**

```python
"""Student detail tool — full enrollment profile."""

from my_support_agent.api_client import call_admin_api


def get_student_detail(enrollment_id: str) -> dict:
    """Fetch full details for a single enrollment, including payment information.

    Args:
        enrollment_id: The enrollment UUID (not the enrollment_ref string).

    Returns student profile, class, intake, and payment details.
    Use list_enrollments first to find the enrollment_id if you only have a ref or name.
    """
    return call_admin_api("GET", f"/api/admin/students/{enrollment_id}")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_student_detail.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/student_detail.py tests/test_student_detail.py
git commit -m "feat: add get_student_detail tool"
```

---

## Task 8: Create `payments.py`

**Files:**
- Create: `my_support_agent/tools/payments.py`
- Create: `tests/test_payments.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_payments.py`:

```python
"""Tests for get_pending_payments, verify_payment, confirm/cancel payment action."""

from unittest.mock import MagicMock, patch


PAYMENT_ID = "pay-uuid-001"


def _make_context(initial_state=None):
    ctx = MagicMock()
    ctx.state = initial_state or {}
    return ctx


# ---------------------------------------------------------------------------
# get_pending_payments
# ---------------------------------------------------------------------------

def test_get_pending_payments_calls_correct_endpoint():
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={"data": []}) as mock_api:
        from my_support_agent.tools.payments import get_pending_payments
        get_pending_payments()
    mock_api.assert_called_once_with("GET", "/api/admin/payments/pending")


def test_get_pending_payments_returns_response():
    payload = {"data": [{"enrollment": {"student_name_en": "Mg Mg"}, "payment": {"amount_mmk": 350000}}]}
    with patch("my_support_agent.tools.payments.call_admin_api", return_value=payload):
        from my_support_agent.tools.payments import get_pending_payments
        result = get_pending_payments()
    assert result["data"][0]["payment"]["amount_mmk"] == 350000


def test_get_pending_payments_forwards_error():
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={"error": "Authentication failed."}):
        from my_support_agent.tools.payments import get_pending_payments
        result = get_pending_payments()
    assert "error" in result


# ---------------------------------------------------------------------------
# verify_payment — validation and staging
# ---------------------------------------------------------------------------

def test_verify_payment_invalid_action_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(PAYMENT_ID, "refund", ctx)
    assert "error" in result
    assert not ctx.state.get("pending_payment_action")


def test_verify_payment_reject_requires_rejection_reason():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(PAYMENT_ID, "reject", ctx)
    assert "error" in result
    assert "rejection_reason" in result["error"]


def test_verify_payment_request_remaining_requires_admin_note():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(PAYMENT_ID, "request_remaining", ctx)
    assert "error" in result
    assert "admin_note" in result["error"]


def test_verify_payment_approve_stages_action():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(PAYMENT_ID, "approve", ctx)

    assert result["confirmation_required"] is True
    assert "approve" in result["summary"]
    pending = ctx.state["pending_payment_action"]
    assert pending["payment_id"] == PAYMENT_ID
    assert pending["action"] == "approve"


def test_verify_payment_reject_stages_with_reason():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(PAYMENT_ID, "reject", ctx, rejection_reason="Wrong amount")

    pending = ctx.state["pending_payment_action"]
    assert pending["rejection_reason"] == "Wrong amount"
    assert result["confirmation_required"] is True


def test_verify_payment_request_remaining_stages_with_note_and_amount():
    ctx = _make_context()
    from my_support_agent.tools.payments import verify_payment
    result = verify_payment(
        PAYMENT_ID, "request_remaining", ctx,
        admin_note="Need 50,000 more", received_amount=300000
    )
    pending = ctx.state["pending_payment_action"]
    assert pending["admin_note"] == "Need 50,000 more"
    assert pending["received_amount"] == 300000


def test_verify_payment_does_not_call_api():
    ctx = _make_context()
    with patch("my_support_agent.tools.payments.call_admin_api") as mock_api:
        from my_support_agent.tools.payments import verify_payment
        verify_payment(PAYMENT_ID, "approve", ctx)
    mock_api.assert_not_called()


# ---------------------------------------------------------------------------
# confirm_payment_action — calls PATCH API
# ---------------------------------------------------------------------------

def test_confirm_payment_action_calls_patch():
    ctx = _make_context({
        "pending_payment_action": {
            "payment_id": PAYMENT_ID,
            "action": "approve",
            "rejection_reason": None,
            "admin_note": None,
            "received_amount": None,
        }
    })
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={"enrollment": {}, "payment": {}}) as mock_api:
        from my_support_agent.tools.payments import confirm_payment_action
        confirm_payment_action(ctx)

    mock_api.assert_called_once_with(
        "PATCH",
        f"/api/admin/payments/{PAYMENT_ID}/verify",
        json={"action": "approve"},
    )
    assert not ctx.state.get("pending_payment_action")


def test_confirm_payment_action_includes_rejection_reason():
    ctx = _make_context({
        "pending_payment_action": {
            "payment_id": PAYMENT_ID,
            "action": "reject",
            "rejection_reason": "Duplicate",
            "admin_note": None,
            "received_amount": None,
        }
    })
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={}) as mock_api:
        from my_support_agent.tools.payments import confirm_payment_action
        confirm_payment_action(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body["rejection_reason"] == "Duplicate"


def test_confirm_payment_action_no_pending_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.payments import confirm_payment_action
    result = confirm_payment_action(ctx)
    assert "error" in result


def test_confirm_payment_action_forwards_api_error():
    ctx = _make_context({
        "pending_payment_action": {
            "payment_id": PAYMENT_ID,
            "action": "approve",
            "rejection_reason": None,
            "admin_note": None,
            "received_amount": None,
        }
    })
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={"error": "Not found."}):
        from my_support_agent.tools.payments import confirm_payment_action
        result = confirm_payment_action(ctx)
    assert "error" in result


# ---------------------------------------------------------------------------
# cancel_payment_action — clears state
# ---------------------------------------------------------------------------

def test_cancel_payment_action_clears_state():
    ctx = _make_context({
        "pending_payment_action": {
            "payment_id": PAYMENT_ID,
            "action": "approve",
            "rejection_reason": None,
            "admin_note": None,
            "received_amount": None,
        }
    })
    from my_support_agent.tools.payments import cancel_payment_action
    result = cancel_payment_action(ctx)
    assert result["cancelled"] is True
    assert not ctx.state.get("pending_payment_action")


def test_cancel_payment_action_no_pending_is_graceful():
    ctx = _make_context()
    from my_support_agent.tools.payments import cancel_payment_action
    result = cancel_payment_action(ctx)
    assert "message" in result
    assert "error" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_payments.py -v
```

Expected: `ModuleNotFoundError: No module named 'my_support_agent.tools.payments'`

- [ ] **Step 3: Create `my_support_agent/tools/payments.py`**

```python
"""Payment tools — pending list and verification with confirmation gate."""

from google.adk.tools import ToolContext
from my_support_agent.api_client import call_admin_api

_VALID_ACTIONS = ("approve", "reject", "request_remaining")

_CONSEQUENCES = {
    "approve": "Will send confirmation notification + Telegram channel invite if eligible.",
    "reject": "Will send rejection notification. Seats will be restored.",
    "request_remaining": "Will send partial payment notification with remaining amount.",
}


def get_pending_payments() -> dict:
    """List all enrollments with payment_submitted status, oldest first.

    Returns enrollment details, payment amounts, bank references, and intake names.
    Use this to see which payments are waiting for admin verification.
    """
    return call_admin_api("GET", "/api/admin/payments/pending")


def verify_payment(
    payment_id: str,
    action: str,
    tool_context: ToolContext,
    rejection_reason: str = None,
    admin_note: str = None,
    received_amount: int = None,
) -> dict:
    """Stage a payment verification action for admin confirmation.

    Does NOT write to the database. Stores proposed action in
    tool_context.state['pending_payment_action'] and returns a summary.

    Args:
        payment_id: The payment UUID.
        action: 'approve', 'reject', or 'request_remaining'.
        rejection_reason: Required when action is 'reject'.
        admin_note: Required when action is 'request_remaining'.
        received_amount: MMK amount received so far (for 'request_remaining').
    """
    if action not in _VALID_ACTIONS:
        return {"error": f"action must be one of: {', '.join(_VALID_ACTIONS)}."}
    if action == "reject" and not rejection_reason:
        return {"error": "rejection_reason is required when action is 'reject'."}
    if action == "request_remaining" and not admin_note:
        return {"error": "admin_note is required when action is 'request_remaining'."}

    tool_context.state["pending_payment_action"] = {
        "payment_id": payment_id,
        "action": action,
        "rejection_reason": rejection_reason,
        "admin_note": admin_note,
        "received_amount": received_amount,
    }

    summary = (
        f"Proposed payment action for payment ID {payment_id}:\n"
        f"  • Action: {action}\n"
        f"  • {_CONSEQUENCES[action]}\n"
        "Reply **confirm** to apply or **cancel** to discard."
    )
    return {"confirmation_required": True, "summary": summary}


def confirm_payment_action(tool_context: ToolContext) -> dict:
    """Apply the staged payment action via the admin API.

    Calls PATCH /api/admin/payments/[id]/verify with the staged action.
    Triggers student notifications automatically on the server side.
    """
    pending = tool_context.state.get("pending_payment_action")
    if not pending:
        return {"error": "No pending payment action to confirm."}

    body: dict = {"action": pending["action"]}
    if pending.get("rejection_reason"):
        body["rejection_reason"] = pending["rejection_reason"]
    if pending.get("admin_note"):
        body["admin_note"] = pending["admin_note"]
    if pending.get("received_amount") is not None:
        body["received_amount"] = pending["received_amount"]

    result = call_admin_api(
        "PATCH",
        f"/api/admin/payments/{pending['payment_id']}/verify",
        json=body,
    )
    tool_context.state["pending_payment_action"] = None
    return result


def cancel_payment_action(tool_context: ToolContext) -> dict:
    """Discard the staged payment action without writing to the database."""
    pending = tool_context.state.get("pending_payment_action")
    if not pending:
        return {"message": "No pending payment action to cancel."}

    tool_context.state["pending_payment_action"] = None
    return {
        "cancelled": True,
        "message": f"Payment action for payment {pending['payment_id']} has been cancelled. No changes were made.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_payments.py -v
```

Expected: all 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add my_support_agent/tools/payments.py tests/test_payments.py
git commit -m "feat: add payment tools with verify/confirm/cancel gate"
```

---

## Task 9: Wire everything up — `__init__.py` and `admin_agent.py`

**Files:**
- Modify: `my_support_agent/tools/__init__.py`
- Modify: `my_support_agent/admin_agent.py`

- [ ] **Step 1: Update `my_support_agent/tools/__init__.py`**

Replace the file contents with:

```python
"""KuuNyi Support Agent Tools."""

from my_support_agent.tools.knowledge import search_knowledge_base
from my_support_agent.tools.enrollment import check_enrollment_status
from my_support_agent.tools.payment import check_payment_status
from my_support_agent.tools.ticket import create_support_ticket
from my_support_agent.tools.search import search_enrollments_by_phone
from my_support_agent.tools.seats import get_seats_overview
from my_support_agent.tools.summary import get_stats
from my_support_agent.tools.admin_enrollments import list_enrollments
from my_support_agent.tools.update_class import (
    update_class,
    confirm_update,
    cancel_update,
)
from my_support_agent.tools.student_detail import get_student_detail
from my_support_agent.tools.payments import (
    get_pending_payments,
    verify_payment,
    confirm_payment_action,
    cancel_payment_action,
)

__all__ = [
    "search_knowledge_base",
    "check_enrollment_status",
    "check_payment_status",
    "create_support_ticket",
    "search_enrollments_by_phone",
    "get_seats_overview",
    "get_stats",
    "list_enrollments",
    "update_class",
    "confirm_update",
    "cancel_update",
    "get_student_detail",
    "get_pending_payments",
    "verify_payment",
    "confirm_payment_action",
    "cancel_payment_action",
]
```

- [ ] **Step 2: Update `my_support_agent/admin_agent.py`**

Replace the file contents with:

```python
"""KuuNyi Admin Agent — ADK agent definition for tenant admins."""

from google.adk.agents import LlmAgent
from my_support_agent.config import init_admin, get_tenant_name
from my_support_agent.tools import (
    get_seats_overview,
    get_stats,
    list_enrollments,
    get_student_detail,
    get_pending_payments,
    update_class,
    confirm_update,
    cancel_update,
    verify_payment,
    confirm_payment_action,
    cancel_payment_action,
)

init_admin()

_SYSTEM_INSTRUCTION = f"""You are a smart assistant for {get_tenant_name()} tenant admins. You help admins manage classes, review enrollments, and process payments.

RULES:
1. You are speaking to a verified tenant admin. No identity verification is needed.
2. Always scope all data to the current tenant — never show data from other tenants.
3. For read queries, call the appropriate tool and format results clearly with labels and numbers.

SEATS & CLASSES:
4. To view class fill rates and capacity, call get_seats_overview.
5. To update a class (capacity, price, or status):
   a. If the admin refers to a class by name, call get_seats_overview first to find the matching class ID — never ask the admin for the ID.
   b. Call update_class to stage the change — this does NOT update yet.
   c. Show the admin a clear summary of what will change.
   d. Ask: "Reply YES to confirm or NO to cancel."
   e. Wait for the admin's next message.
   f. If YES → call confirm_update. If NO → call cancel_update.
   g. Never call confirm_update unless the admin explicitly said YES in this conversation turn.

STATS & ENROLLMENTS:
6. To get an enrollment and revenue snapshot, call get_stats.
7. To list enrollments, call list_enrollments. You can filter by status or search by name/phone.
8. To view full details for a specific student, call get_student_detail with their enrollment UUID.

PAYMENTS:
9. To see all payments awaiting verification, call get_pending_payments.
10. To approve, reject, or request remaining payment:
    a. Call verify_payment with the payment_id and action — this does NOT write yet.
    b. Show the admin a clear summary including the action consequences.
    c. Ask: "Reply YES to confirm or NO to cancel."
    d. Wait for the admin's next message.
    e. If YES → call confirm_payment_action. If NO → call cancel_payment_action.
    f. Never call confirm_payment_action unless the admin explicitly said YES in this conversation turn.
    g. Consequences by action:
       - approve: sends confirmation notification + Telegram invite if eligible
       - reject: sends rejection notification, seats restored
       - request_remaining: sends partial payment notification with remaining amount

GENERAL:
11. Keep responses concise and well-formatted. Use plain text suitable for Telegram messages.
12. Never fabricate class IDs, enrollment counts, or prices. Only use data from tools.
13. If a tool returns an error, report it clearly and suggest the admin try again or check the input.
"""

admin_agent = LlmAgent(
    name="kuunyi_admin_agent",
    model="gemini-2.5-flash",
    instruction=_SYSTEM_INSTRUCTION,
    tools=[
        get_seats_overview,
        get_stats,
        list_enrollments,
        get_student_detail,
        get_pending_payments,
        update_class,
        confirm_update,
        cancel_update,
        verify_payment,
        confirm_payment_action,
        cancel_payment_action,
    ],
)
```

- [ ] **Step 3: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS. Note: `test_api_client.py` tests that directly manipulate module globals will still pass because each test calls `_reset()`.

- [ ] **Step 4: Commit**

```bash
git add my_support_agent/tools/__init__.py my_support_agent/admin_agent.py
git commit -m "feat: wire up admin agent with API-backed tools and payment verification"
```

---

## Task 10: Smoke test with `adk web`

- [ ] **Step 1: Add new env vars to `.env`**

Open `.env` and add:
```
ADMIN_API_BASE_URL=https://nihon-moment.kuunyi.com
AGENT_SECRET=<your-actual-secret>
TENANT_NAME=Nihon Moment
```

Remove (or comment out) from the admin agent's env if you have a separate `.env` for it:
```
# SUPABASE_URL and SUPABASE_KEY no longer needed by admin agent
```

- [ ] **Step 2: Start the dev server**

```
adk web
```

Expected: server starts without errors at `http://localhost:8000`

If you see `RuntimeError: ADMIN_API_BASE_URL environment variable must be set`, the env vars are not being loaded — check `.env` is in the working directory.

- [ ] **Step 3: Verify basic flows in the browser**

Open `http://localhost:8000`, select `kuunyi_admin_agent`, then test:

1. "Show me seat availability" → should call `get_seats_overview`, list classes with fill status
2. "What are the current stats?" → should call `get_stats`, show enrollment counts and revenue
3. "Show pending payments" → should call `get_pending_payments`, list payment_submitted enrollments
4. "Approve payment [a real payment ID from the list]" → should stage action, ask for YES/NO

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: complete admin agent API migration"
```

**Note:** Never commit `.env` to git — it contains secrets. Verify `.env` is in `.gitignore`:
```bash
grep "^\.env" .gitignore
```
If that line is missing, add it: `echo ".env" >> .gitignore && git add .gitignore && git commit -m "chore: ensure .env is gitignored"`
