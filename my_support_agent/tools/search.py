"""Search enrollments by phone — also serves as identity verification."""

from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase
from my_support_agent.phone_utils import normalize_phone


def search_enrollments_by_phone(
    phone: str, student_name: str, tool_context: ToolContext
) -> dict:
    """Search for enrollments by phone number and student name.

    This tool verifies the customer's identity by matching their phone
    number and full name against enrollment records. It must be called
    before accessing enrollment or payment details.

    Args:
        phone: Customer's phone number (any Myanmar format accepted)
        student_name: Customer's full name as registered
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return {
            "verified": False,
            "message": "Invalid phone number format. Please provide a Myanmar phone number starting with 09.",
            "enrollments": [],
        }

    if not student_name or not student_name.strip():
        return {
            "verified": False,
            "message": "Please provide your full name.",
            "enrollments": [],
        }

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        response = (
            supabase.table("enrollments")
            .select("enrollment_ref, student_name_en, phone, status, classes(level, fee_mmk)")
            .eq("tenant_id", tenant_id)
            .eq("phone", normalized)
            .execute()
        )
    except Exception:
        return {
            "verified": False,
            "message": "I'm having trouble accessing our system. Please try again shortly.",
            "enrollments": [],
        }

    if not response.data:
        return {
            "verified": False,
            "message": "No enrollments found for that phone number.",
            "enrollments": [],
        }

    # Exact normalized name match
    name_lower = student_name.strip().lower()
    matched = [
        row for row in response.data
        if row.get("student_name_en", "").strip().lower() == name_lower
    ]

    if not matched:
        return {
            "verified": False,
            "message": "The name doesn't match our records for that phone number. Please double-check your full name.",
            "enrollments": [],
        }

    # Store verified refs in session state
    verified_refs = [row["enrollment_ref"] for row in matched]
    tool_context.state["verified"] = True
    tool_context.state["verified_refs"] = verified_refs

    enrollments = []
    for row in matched:
        enrollment = {
            "enrollment_ref": row["enrollment_ref"],
            "student_name": row["student_name_en"],
            "status": row["status"],
        }
        if row.get("classes"):
            enrollment["level"] = row["classes"].get("level")
            enrollment["fee"] = row["classes"].get("fee_mmk")
        enrollments.append(enrollment)

    return {
        "verified": True,
        "message": f"Identity verified. Found {len(enrollments)} enrollment(s).",
        "enrollments": enrollments,
    }
