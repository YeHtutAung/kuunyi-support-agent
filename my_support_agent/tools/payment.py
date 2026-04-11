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
