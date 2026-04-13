"""Seats overview tool — class capacity and fill status."""

from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def get_seats_overview() -> dict:
    """Get seat availability across all classes for the current tenant.

    Returns each class with enrolled count, capacity, price, and a status
    label: 'full' (seat_remaining == 0), 'critical' (>= 85% full), or
    'available'.
    """
    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("classes")
            .select("id, level, seat_total, seat_remaining, fee_mmk")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception as e:
        return {"error": f"Unable to retrieve class data: {e}"}

    classes = []
    for row in response.data or []:
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
        })

    return {"classes": classes, "total": len(classes)}
