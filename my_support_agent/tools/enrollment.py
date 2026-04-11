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
            .select("enrollment_ref, student_name_en, phone, status, enrolled_at, classes(level, fee_mmk)")
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
        "student_name": row["student_name_en"],
        "status": row["status"],
        "enrolled_date": row.get("enrolled_at"),
    }
    if row.get("classes"):
        result["level"] = row["classes"].get("level")
        result["fee_mmk"] = row["classes"].get("fee_mmk")

    return result
