"""Seats overview tool — class capacity and fill status."""

from my_support_agent.api_client import call_admin_api


def get_seats_overview() -> dict:
    """Get seat availability across all classes for all open intakes.

    Makes one API call to list intakes, then one per open intake to list its
    classes.  Returns classes grouped by intake with enrolled count, capacity,
    price, mode, and a status label: 'full' (seat_remaining == 0),
    'critical' (>= 85% full), or 'available'.
    """
    intakes_resp = call_admin_api("GET", "/api/intakes")
    if "error" in intakes_resp:
        return intakes_resp

    open_intakes = [i for i in intakes_resp.get("data", []) if i.get("status") == "open"]
    if not open_intakes:
        return {"error": "No open intake found."}

    intakes = []
    for intake in open_intakes:
        intake_id = intake["id"]
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

        intakes.append({
            "intake_id": intake_id,
            "intake_name": intake.get("name"),
            "classes": classes,
        })

    return {"intakes": intakes, "total_intakes": len(intakes)}
