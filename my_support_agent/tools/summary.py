"""Enrollment summary tool — period-based stats and revenue."""

from datetime import datetime, timedelta, timezone
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def get_summary(period: str) -> dict:
    """Get enrollment summary for the current tenant over a given period.

    Args:
        period: 'day' for the last 24 hours, 'week' for the last 7 days.

    Returns total enrollments, counts by status, and confirmed revenue.
    """
    if period not in ("day", "week"):
        return {"error": "period must be 'day' or 'week'."}

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    now = datetime.now(timezone.utc)
    delta = timedelta(days=1) if period == "day" else timedelta(days=7)
    since = (now - delta).isoformat()

    try:
        enroll_resp = (
            supabase.table("enrollments")
            .select("id, status")
            .eq("tenant_id", tenant_id)
            .gte("enrolled_at", since)
            .execute()
        )

        rows = enroll_resp.data or []
        enrollment_ids = [r["id"] for r in rows if r.get("id")]

        # Fetch payments for these enrollments in one query
        payment_map: dict = {}
        if enrollment_ids:
            pay_resp = (
                supabase.table("payments")
                .select("enrollment_id, amount_mmk, status")
                .eq("tenant_id", tenant_id)
                .in_("enrollment_id", enrollment_ids)
                .execute()
            )
            for p in pay_resp.data or []:
                eid = p.get("enrollment_id")
                if eid:
                    payment_map.setdefault(eid, []).append(p)

    except Exception as e:
        return {"error": f"Unable to retrieve summary data: {e}"}

    confirmed = pending = cancelled = 0
    total_revenue = 0

    for row in rows:
        status = row.get("status")
        if status == "confirmed":
            confirmed += 1
            for payment in payment_map.get(row["id"], []):
                if payment.get("status") == "verified":
                    total_revenue += payment.get("amount_mmk") or 0
        elif status == "pending":
            pending += 1
        elif status == "cancelled":
            cancelled += 1

    return {
        "period": period,
        "since": since,
        "total_enrollments": len(rows),
        "confirmed": confirmed,
        "pending": pending,
        "cancelled": cancelled,
        "total_revenue_mmk": total_revenue,
    }
