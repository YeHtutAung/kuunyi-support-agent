"""Tests for get_stats (API-backed)."""

from unittest.mock import patch


STATS_RESPONSE = {
    "total_enrollments": 50,
    "confirmed_count": 30,
    "pending_payment_count": 10,
    "payment_submitted_count": 5,
    "total_revenue_mmk": 15000000,
    "seats_by_class": [
        {"level": "N5", "seat_remaining": 12, "seat_total": 30},
    ],
}


def test_get_stats_calls_correct_endpoint():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value=STATS_RESPONSE) as mock_api:
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    mock_api.assert_called_once_with("GET", "/api/admin/stats")
    assert result["total_enrollments"] == 50


def test_get_stats_returns_full_response():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value=STATS_RESPONSE):
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    assert result["confirmed_count"] == 30
    assert result["total_revenue_mmk"] == 15000000
    assert len(result["seats_by_class"]) == 1


def test_get_stats_forwards_error():
    with patch("my_support_agent.tools.summary.call_admin_api", return_value={"error": "Authentication failed."}):
        from my_support_agent.tools.summary import get_stats
        result = get_stats()
    assert "error" in result
