"""Student detail tool — full enrollment profile."""

from my_support_agent.api_client import call_admin_api


def get_student_detail(enrollment_id: str) -> dict:
    """Fetch full details for a single enrollment, including payment information.

    Args:
        enrollment_id: The enrollment UUID (not the enrollment_ref string).

    Returns student profile, class, intake, and payment details.
    Use list_enrollments first to find the enrollment_id if you only have a ref or name.
    """
    return call_admin_api("GET", f"/api/admin/students/{enrollment_id}")
