"""Tests for get_pending_payments, verify_payment, confirm/cancel payment action."""

from unittest.mock import MagicMock, patch

from my_support_agent.tools.payments import (
    get_pending_payments,
    verify_payment,
    confirm_payment_action,
    cancel_payment_action,
)

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
        get_pending_payments()
    mock_api.assert_called_once_with("GET", "/api/admin/payments/pending")


def test_get_pending_payments_returns_response():
    payload = {"data": [{"enrollment": {"student_name_en": "Mg Mg"}, "payment": {"amount_mmk": 350000}}]}
    with patch("my_support_agent.tools.payments.call_admin_api", return_value=payload):
        result = get_pending_payments()
    assert result["data"][0]["payment"]["amount_mmk"] == 350000


def test_get_pending_payments_forwards_error():
    with patch("my_support_agent.tools.payments.call_admin_api",
               return_value={"error": "Authentication failed."}):
        result = get_pending_payments()
    assert "error" in result


# ---------------------------------------------------------------------------
# verify_payment — validation and staging
# ---------------------------------------------------------------------------

def test_verify_payment_invalid_action_returns_error():
    ctx = _make_context()
    result = verify_payment(PAYMENT_ID, "refund", ctx)
    assert "error" in result
    assert not ctx.state.get("pending_payment_action")


def test_verify_payment_reject_requires_rejection_reason():
    ctx = _make_context()
    result = verify_payment(PAYMENT_ID, "reject", ctx)
    assert "error" in result
    assert "rejection_reason" in result["error"]


def test_verify_payment_request_remaining_requires_admin_note():
    ctx = _make_context()
    result = verify_payment(PAYMENT_ID, "request_remaining", ctx)
    assert "error" in result
    assert "admin_note" in result["error"]


def test_verify_payment_approve_stages_action():
    ctx = _make_context()
    result = verify_payment(PAYMENT_ID, "approve", ctx)

    assert result["confirmation_required"] is True
    assert "approve" in result["summary"]
    pending = ctx.state["pending_payment_action"]
    assert pending["payment_id"] == PAYMENT_ID
    assert pending["action"] == "approve"


def test_verify_payment_reject_stages_with_reason():
    ctx = _make_context()
    result = verify_payment(PAYMENT_ID, "reject", ctx, rejection_reason="Wrong amount")

    pending = ctx.state["pending_payment_action"]
    assert pending["rejection_reason"] == "Wrong amount"
    assert result["confirmation_required"] is True


def test_verify_payment_request_remaining_stages_with_note_and_amount():
    ctx = _make_context()
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
        confirm_payment_action(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body["rejection_reason"] == "Duplicate"


def test_confirm_payment_action_no_pending_returns_error():
    ctx = _make_context()
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
    result = cancel_payment_action(ctx)
    assert result["cancelled"] is True
    assert not ctx.state.get("pending_payment_action")


def test_cancel_payment_action_no_pending_is_graceful():
    ctx = _make_context()
    result = cancel_payment_action(ctx)
    assert "message" in result
    assert "error" not in result
