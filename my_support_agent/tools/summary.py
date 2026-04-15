"""Stats tool — admin dashboard snapshot."""

from my_support_agent.api_client import call_admin_api


def get_stats() -> dict:
    """Get current enrollment and revenue statistics for the tenant.

    Returns a real-time snapshot: total enrollments, counts by status
    (confirmed, pending_payment, payment_submitted), total revenue, and
    seat availability across all classes.
    """
    return call_admin_api("GET", "/api/admin/stats")
