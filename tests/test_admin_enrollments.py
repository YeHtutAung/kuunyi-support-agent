"""Tests for list_enrollments (API-backed)."""

from unittest.mock import patch, call


ENROLLMENTS_RESPONSE = {
    "data": [
        {
            "enrollment_id": "uuid-1",
            "enrollment_ref": "NM-0411-A3X2",
            "student_name_en": "Mg Mg",
            "phone": "09123456789",
            "class_level": "N4",
            "status": "confirmed",
            "enrolled_at": "2026-04-01T10:00:00Z",
            "intake_name": "April 2026 Intake",
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
}


def test_no_filters_calls_with_defaults():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments()
    mock_api.assert_called_once_with(
        "GET", "/api/admin/students", params={"page": 1, "page_size": 20}
    )


def test_status_filter_included_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(status="confirmed")
    params = mock_api.call_args.kwargs["params"]
    assert params["status"] == "confirmed"


def test_search_filter_included_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(search="Mg Mg")
    params = mock_api.call_args.kwargs["params"]
    assert params["search"] == "Mg Mg"


def test_page_param_forwarded():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments(page=3)
    params = mock_api.call_args.kwargs["params"]
    assert params["page"] == 3


def test_no_status_not_in_params():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE) as mock_api:
        from my_support_agent.tools.admin_enrollments import list_enrollments
        list_enrollments()
    params = mock_api.call_args.kwargs["params"]
    assert "status" not in params
    assert "search" not in params


def test_returns_api_response():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value=ENROLLMENTS_RESPONSE):
        from my_support_agent.tools.admin_enrollments import list_enrollments
        result = list_enrollments()
    assert result["total"] == 1
    assert result["data"][0]["student_name_en"] == "Mg Mg"


def test_forwards_api_error():
    with patch("my_support_agent.tools.admin_enrollments.call_admin_api",
               return_value={"error": "Authentication failed."}):
        from my_support_agent.tools.admin_enrollments import list_enrollments
        result = list_enrollments()
    assert "error" in result
