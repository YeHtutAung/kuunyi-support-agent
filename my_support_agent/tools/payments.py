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

    if "error" in result:
        return result   # preserve pending_payment_action so admin can retry

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
