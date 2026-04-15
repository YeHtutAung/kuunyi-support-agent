"""Admin enrollment listing tool."""

from my_support_agent.api_client import call_admin_api


def list_enrollments(
    status: str = None,
    search: str = None,
    page: int = 1,
) -> dict:
    """List enrollments for the current tenant.

    Args:
        status: Optional filter — 'pending_payment', 'payment_submitted',
                'partial_payment', 'confirmed', 'rejected'.
        search: Optional partial match on student name or phone.
        page: Page number, 1-based (default 1). Page size is fixed at 20.
    """
    params: dict = {"page": page, "page_size": 20}
    if status:
        params["status"] = status
    if search:
        params["search"] = search

    return call_admin_api("GET", "/api/admin/students", params=params)
