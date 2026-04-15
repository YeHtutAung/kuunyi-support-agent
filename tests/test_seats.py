"""Tests for get_seats_overview (API-backed)."""

from unittest.mock import patch, call


def _intakes_response(intake_id="intake-1"):
    return {"data": [{"id": intake_id, "status": "open", "name": "April 2026"}]}


def _classes_response(rows):
    return {"data": rows}


def _patch_api(side_effects):
    return patch(
        "my_support_agent.tools.seats.call_admin_api",
        side_effect=side_effects,
    )


# ---------------------------------------------------------------------------
# Status labelling
# ---------------------------------------------------------------------------

def test_status_available():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 20, "seat_remaining": 10,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "available"
    assert result["classes"][0]["enrolled"] == 10
    assert result["classes"][0]["class_id"] == "c1"


def test_status_critical():
    # 17/20 = 85% → critical
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N4", "seat_total": 20, "seat_remaining": 3,
             "fee_mmk": 60000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "critical"


def test_status_full():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N3", "seat_total": 15, "seat_remaining": 0,
             "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["classes"][0]["status"] == "full"


def test_multiple_classes_mixed_status():
    with _patch_api([
        _intakes_response(),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 10, "fee_mmk": 50000, "mode": "offline"},
            {"id": "c2", "level": "N4", "seat_total": 10, "seat_remaining": 1,  "fee_mmk": 60000, "mode": "offline"},
            {"id": "c3", "level": "N3", "seat_total": 10, "seat_remaining": 0,  "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    statuses = {c["class_name"]: c["status"] for c in result["classes"]}
    assert statuses["N5"] == "available"
    assert statuses["N4"] == "critical"
    assert statuses["N3"] == "full"
    assert result["total"] == 3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_no_open_intake_returns_error():
    with _patch_api([{"data": [{"id": "i1", "status": "closed"}]}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result
    assert "No open intake" in result["error"]


def test_intakes_api_error_propagates():
    with _patch_api([{"error": "Authentication failed. Check AGENT_SECRET configuration."}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_classes_api_error_propagates():
    with _patch_api([
        _intakes_response(),
        {"error": "API request failed: 500."},
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_calls_correct_endpoints():
    with _patch_api([
        _intakes_response("intake-xyz"),
        _classes_response([]),
    ]) as mock_api:
        from my_support_agent.tools.seats import get_seats_overview
        get_seats_overview()
    assert mock_api.call_args_list[0] == call("GET", "/api/intakes")
    assert mock_api.call_args_list[1] == call("GET", "/api/intakes/intake-xyz/classes")
