"""Admin enrollment listing tool."""

from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


def list_enrollments(status: str = None, limit: int = 20) -> dict:
    """List enrollments for the current tenant, optionally filtered by status.

    Args:
        status: Optional filter — e.g. 'confirmed', 'pending', 'cancelled'.
        limit: Maximum number of records to return (default 20).

    Returns a list of enrollments with class name included.
    """
    tenant_id = get_tenant_id()
    supabase = get_supabase()

    try:
        query = (
            supabase.table("enrollments")
            .select("enrollment_ref, student_name_en, phone, status, enrolled_at, class_id")
            .eq("tenant_id", tenant_id)
            .order("enrolled_at", desc=True)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)

        enroll_resp = query.execute()

        # Fetch class names for the returned rows
        class_ids = list({r["class_id"] for r in enroll_resp.data or [] if r.get("class_id")})
        class_map: dict = {}
        if class_ids:
            classes_resp = (
                supabase.table("classes")
                .select("id, level")
                .eq("tenant_id", tenant_id)
                .in_("id", class_ids)
                .execute()
            )
            class_map = {r["id"]: r.get("level") for r in classes_resp.data or []}

    except Exception as e:
        return {"error": f"Unable to retrieve enrollments: {e}"}

    enrollments = []
    for row in enroll_resp.data or []:
        enrollments.append({
            "enrollment_ref": row.get("enrollment_ref"),
            "student_name": row.get("student_name_en"),
            "phone": row.get("phone"),
            "class_name": class_map.get(row.get("class_id")),
            "status": row.get("status"),
            "enrolled_at": row.get("enrolled_at"),
        })

    return {"enrollments": enrollments, "count": len(enrollments)}
