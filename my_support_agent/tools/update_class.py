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
