"""Tests for get_seats_overview."""

from unittest.mock import MagicMock, patch


TENANT_ID = "tenant-abc"


def _make_supabase(rows):
    resp = MagicMock()
    resp.data = rows

    chain = MagicMock()
    chain.execute.return_value = resp
    chain.eq.return_value = chain
    chain.select.return_value = chain

    client = MagicMock()
    client.table.return_value = chain
    return client


@patch("my_support_agent.tools.seats.get_supabase")
@patch("my_support_agent.tools.seats.get_tenant_id", return_value=TENANT_ID)
def test_status_available(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase([
        {"id": "c1", "level": "N5 Morning", "seat_total": 20, "seat_remaining": 10, "fee_mmk": 50000},
    ])
    from my_support_agent.tools.seats import get_seats_overview
    result = get_seats_overview()
    assert result["classes"][0]["status"] == "available"
    assert result["classes"][0]["enrolled"] == 10
    assert result["classes"][0]["seats_remaining"] == 10


@patch("my_support_agent.tools.seats.get_supabase")
@patch("my_support_agent.tools.seats.get_tenant_id", return_value=TENANT_ID)
def test_status_critical(mock_tenant, mock_supabase):
    # 17/20 enrolled = 85% → critical
    mock_supabase.return_value = _make_supabase([
        {"id": "c1", "level": "N4 Evening", "seat_total": 20, "seat_remaining": 3, "fee_mmk": 60000},
    ])
    from my_support_agent.tools.seats import get_seats_overview
    result = get_seats_overview()
    assert result["classes"][0]["status"] == "critical"


@patch("my_support_agent.tools.seats.get_supabase")
@patch("my_support_agent.tools.seats.get_tenant_id", return_value=TENANT_ID)
def test_status_full(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase([
        {"id": "c1", "level": "N3 Weekend", "seat_total": 15, "seat_remaining": 0, "fee_mmk": 70000},
    ])
    from my_support_agent.tools.seats import get_seats_overview
    result = get_seats_overview()
    assert result["classes"][0]["status"] == "full"


@patch("my_support_agent.tools.seats.get_supabase")
@patch("my_support_agent.tools.seats.get_tenant_id", return_value=TENANT_ID)
def test_multiple_classes_mixed_status(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase([
        {"id": "c1", "level": "N5", "seat_total": 10, "seat_remaining": 10, "fee_mmk": 50000},
        {"id": "c2", "level": "N4", "seat_total": 10, "seat_remaining": 1,  "fee_mmk": 60000},
        {"id": "c3", "level": "N3", "seat_total": 10, "seat_remaining": 0,  "fee_mmk": 70000},
    ])
    from my_support_agent.tools.seats import get_seats_overview
    result = get_seats_overview()
    statuses = {c["class_name"]: c["status"] for c in result["classes"]}
    assert statuses["N5"] == "available"
    assert statuses["N4"] == "critical"
    assert statuses["N3"] == "full"
    assert result["total"] == 3


@patch("my_support_agent.tools.seats.get_supabase")
@patch("my_support_agent.tools.seats.get_tenant_id", return_value=TENANT_ID)
def test_supabase_error_returns_error_dict(mock_tenant, mock_supabase):
    mock_supabase.return_value.table.side_effect = Exception("DB down")
    from my_support_agent.tools.seats import get_seats_overview
    result = get_seats_overview()
    assert "error" in result
