"""Tests for get_seats_overview (API-backed)."""

from unittest.mock import patch, call


def _intakes_response(*intakes):
    """Build an intakes API response with one or more open intake dicts."""
    return {"data": list(intakes)}


def _open_intake(intake_id="intake-1", name="April 2026"):
    return {"id": intake_id, "status": "open", "name": name}


def _classes_response(rows):
    return {"data": rows}


def _patch_api(side_effects):
    return patch(
        "my_support_agent.tools.seats.call_admin_api",
        side_effect=side_effects,
    )


# ---------------------------------------------------------------------------
# Single open intake
# ---------------------------------------------------------------------------

def test_single_intake_returns_correct_structure():
    with _patch_api([
        _intakes_response(_open_intake("intake-1", "April 2026")),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 20, "seat_remaining": 10,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()

    assert "intakes" in result
    assert result["total_intakes"] == 1
    assert result["intakes"][0]["intake_id"] == "intake-1"
    assert result["intakes"][0]["intake_name"] == "April 2026"
    assert len(result["intakes"][0]["classes"]) == 1
    cls = result["intakes"][0]["classes"][0]
    assert cls["class_id"] == "c1"
    assert cls["enrolled"] == 10
    assert cls["capacity"] == 20
    assert cls["seats_remaining"] == 10


# ---------------------------------------------------------------------------
# Multiple open intakes
# ---------------------------------------------------------------------------

def test_multiple_intakes_loops_through_all():
    with _patch_api([
        _intakes_response(
            _open_intake("intake-1", "April 2026"),
            _open_intake("intake-2", "May 2026"),
        ),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 5,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
        _classes_response([
            {"id": "c2", "level": "N4", "seat_total": 10, "seat_remaining": 3,
             "fee_mmk": 60000, "mode": "online"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()

    assert result["total_intakes"] == 2
    assert result["intakes"][0]["intake_id"] == "intake-1"
    assert result["intakes"][1]["intake_id"] == "intake-2"
    assert result["intakes"][0]["classes"][0]["class_id"] == "c1"
    assert result["intakes"][1]["classes"][0]["class_id"] == "c2"


# ---------------------------------------------------------------------------
# No open intake
# ---------------------------------------------------------------------------

def test_no_open_intake_returns_error():
    with _patch_api([{"data": [{"id": "i1", "status": "closed"}]}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result
    assert "No open intake" in result["error"]


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

def test_intakes_api_error_propagates():
    with _patch_api([{"error": "Authentication failed. Check AGENT_SECRET configuration."}]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_classes_api_error_propagates():
    with _patch_api([
        _intakes_response(_open_intake("intake-1")),
        {"error": "API request failed: 500."},
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


def test_classes_api_error_on_second_intake_propagates():
    with _patch_api([
        _intakes_response(
            _open_intake("intake-1"),
            _open_intake("intake-2"),
        ),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 5,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
        {"error": "API request failed: 503."},
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert "error" in result


# ---------------------------------------------------------------------------
# Status labels
# ---------------------------------------------------------------------------

def test_status_available():
    with _patch_api([
        _intakes_response(_open_intake()),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 20, "seat_remaining": 10,
             "fee_mmk": 50000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["intakes"][0]["classes"][0]["status"] == "available"


def test_status_critical():
    # 17/20 = 85% → critical
    with _patch_api([
        _intakes_response(_open_intake()),
        _classes_response([
            {"id": "c1", "level": "N4", "seat_total": 20, "seat_remaining": 3,
             "fee_mmk": 60000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["intakes"][0]["classes"][0]["status"] == "critical"


def test_status_full():
    with _patch_api([
        _intakes_response(_open_intake()),
        _classes_response([
            {"id": "c1", "level": "N3", "seat_total": 15, "seat_remaining": 0,
             "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    assert result["intakes"][0]["classes"][0]["status"] == "full"


def test_multiple_classes_mixed_status():
    with _patch_api([
        _intakes_response(_open_intake()),
        _classes_response([
            {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 10, "fee_mmk": 50000, "mode": "offline"},
            {"id": "c2", "level": "N4", "seat_total": 10, "seat_remaining": 1,  "fee_mmk": 60000, "mode": "offline"},
            {"id": "c3", "level": "N3", "seat_total": 10, "seat_remaining": 0,  "fee_mmk": 70000, "mode": "offline"},
        ]),
    ]):
        from my_support_agent.tools.seats import get_seats_overview
        result = get_seats_overview()
    classes = result["intakes"][0]["classes"]
    statuses = {c["class_name"]: c["status"] for c in classes}
    assert statuses["N5"] == "available"
    assert statuses["N4"] == "critical"
    assert statuses["N3"] == "full"
    assert len(classes) == 3


# ---------------------------------------------------------------------------
# Correct endpoints
# ---------------------------------------------------------------------------

def test_calls_correct_endpoints_single_intake():
    with _patch_api([
        _intakes_response(_open_intake("intake-xyz")),
        _classes_response([]),
    ]) as mock_api:
        from my_support_agent.tools.seats import get_seats_overview
        get_seats_overview()
    assert mock_api.call_args_list[0] == call("GET", "/api/intakes")
    assert mock_api.call_args_list[1] == call("GET", "/api/intakes/intake-xyz/classes")


def test_calls_correct_endpoints_multiple_intakes():
    with _patch_api([
        _intakes_response(
            _open_intake("intake-1"),
            _open_intake("intake-2"),
        ),
        _classes_response([]),
        _classes_response([]),
    ]) as mock_api:
        from my_support_agent.tools.seats import get_seats_overview
        get_seats_overview()
    assert mock_api.call_args_list[0] == call("GET", "/api/intakes")
    assert mock_api.call_args_list[1] == call("GET", "/api/intakes/intake-1/classes")
    assert mock_api.call_args_list[2] == call("GET", "/api/intakes/intake-2/classes")
