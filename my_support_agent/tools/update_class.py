"""Admin tool to update class capacity and price with a confirmation gate."""

from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def get_class_details(class_id: str) -> dict:
    """Fetch current capacity and price for a class, scoped to the current tenant.

    Args:
        class_id: The class UUID.
    """
    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("classes")
            .select("id, level, seat_total, fee_mmk")
            .eq("tenant_id", tenant_id)
            .eq("id", class_id)
            .execute()
        )
    except Exception:
        return {"error": "Unable to retrieve class details. Please try again shortly."}

    if not response.data:
        return {"error": f"No class found with ID {class_id}."}

    row = response.data[0]
    return {
        "class_id": row["id"],
        "class_name": row.get("level"),
        "capacity": row.get("seat_total"),
        "price_mmk": row.get("fee_mmk"),
    }


def update_class(
    class_id: str,
    tool_context: ToolContext,
    capacity: int = None,
    price_mmk: int = None,
) -> dict:
    """Stage a class update for admin confirmation.

    Does NOT write to the database. Stores the proposed change in
    tool_context.state['pending_update'] and returns a summary for the
    agent to show the admin before they confirm.

    Args:
        class_id: The class UUID to update.
        capacity: New capacity value (optional).
        price_mmk: New price in MMK (optional).
    """
    if capacity is None and price_mmk is None:
        return {"error": "Provide at least one field to update: capacity or price_mmk."}

    current = get_class_details(class_id)
    if "error" in current:
        return current

    pending = {
        "class_id": class_id,
        "class_name": current["class_name"],
        "current_capacity": current["capacity"],
        "current_price": current["price_mmk"],
        "capacity": capacity,
        "price_mmk": price_mmk,
    }
    tool_context.state["pending_update"] = pending

    lines = [f"Proposed update for class **{current['class_name']}** ({class_id}):"]
    if capacity is not None:
        lines.append(f"  • Capacity: {current['capacity']} → {capacity}")
    if price_mmk is not None:
        lines.append(f"  • Price: {current['price_mmk']} MMK → {price_mmk} MMK")
    lines.append("Reply **confirm** to apply or **cancel** to discard.")

    return {"confirmation_required": True, "summary": "\n".join(lines)}


def confirm_update(tool_context: ToolContext) -> dict:
    """Apply the staged class update to the database.

    Reads pending_update from session state, executes the PATCH, then
    clears the pending state.
    """
    pending = tool_context.state.get("pending_update")
    if not pending:
        return {"error": "No pending update to confirm."}

    class_id = pending["class_id"]
    patch: dict = {}
    if pending.get("capacity") is not None:
        patch["seat_total"] = pending["capacity"]
    if pending.get("price_mmk") is not None:
        patch["fee_mmk"] = pending["price_mmk"]

    if not patch:
        tool_context.state["pending_update"] = None
        return {"error": "Pending update had no fields to apply."}

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("classes")
            .update(patch)
            .eq("tenant_id", tenant_id)
            .eq("id", class_id)
            .execute()
        )
    except Exception:
        return {"error": "Failed to apply update. Please try again shortly."}

    if not response.data:
        return {"error": "Update failed — class not found or no rows affected."}

    tool_context.state["pending_update"] = None

    applied = []
    if "seat_total" in patch:
        applied.append(f"capacity → {patch['seat_total']}")
    if "fee_mmk" in patch:
        applied.append(f"price → {patch['fee_mmk']} MMK")

    return {
        "success": True,
        "class_id": class_id,
        "class_name": pending.get("class_name"),
        "updated": applied,
        "message": f"Class '{pending.get('class_name')}' updated successfully: {', '.join(applied)}.",
    }


def cancel_update(tool_context: ToolContext) -> dict:
    """Discard the staged class update without writing to the database."""
    pending = tool_context.state.get("pending_update")
    if not pending:
        return {"message": "No pending update to cancel."}

    tool_context.state["pending_update"] = None

    return {
        "cancelled": True,
        "message": f"Update for class '{pending.get('class_name')}' has been cancelled. No changes were made.",
    }
