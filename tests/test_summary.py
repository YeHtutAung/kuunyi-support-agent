"""Tests for get_summary."""

from unittest.mock import MagicMock, patch


TENANT_ID = "tenant-abc"


def _make_supabase(enrollment_rows, payment_rows=None):
    """Return a mock client that serves enrollments then payments."""
    enroll_resp = MagicMock()
    enroll_resp.data = enrollment_rows

    pay_resp = MagicMock()
    pay_resp.data = payment_rows or []

    call_count = {"n": 0}

    def make_chain(resp):
        chain = MagicMock()
        chain.execute.return_value = resp
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.select.return_value = chain
        chain.in_.return_value = chain
        return chain

    client = MagicMock()
    client.table.side_effect = lambda name: (
        make_chain(enroll_resp) if name == "enrollments" else make_chain(pay_resp)
    )
    return client


def _enrollment(eid, status):
    return {"id": eid, "status": status}


def _payment(enrollment_id, amount, status="verified"):
    return {"enrollment_id": enrollment_id, "amount_mmk": amount, "status": status}


@patch("my_support_agent.tools.summary.get_supabase")
@patch("my_support_agent.tools.summary.get_tenant_id", return_value=TENANT_ID)
def test_counts_by_status(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase(
        enrollment_rows=[
            _enrollment("e1", "confirmed"),
            _enrollment("e2", "confirmed"),
            _enrollment("e3", "pending"),
            _enrollment("e4", "cancelled"),
        ],
        payment_rows=[
            _payment("e1", 50000),
            _payment("e2", 60000),
        ],
    )
    from my_support_agent.tools.summary import get_summary
    result = get_summary("day")
    assert result["total_enrollments"] == 4
    assert result["confirmed"] == 2
    assert result["pending"] == 1
    assert result["cancelled"] == 1


@patch("my_support_agent.tools.summary.get_supabase")
@patch("my_support_agent.tools.summary.get_tenant_id", return_value=TENANT_ID)
def test_revenue_sums_verified_payments_only(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase(
        enrollment_rows=[
            _enrollment("e1", "confirmed"),
            _enrollment("e2", "confirmed"),
            _enrollment("e3", "confirmed"),
        ],
        payment_rows=[
            _payment("e1", 50000, "verified"),
            _payment("e2", 30000, "pending"),   # excluded
            _payment("e3", 20000, "verified"),
        ],
    )
    from my_support_agent.tools.summary import get_summary
    result = get_summary("week")
    assert result["total_revenue_mmk"] == 70000


@patch("my_support_agent.tools.summary.get_supabase")
@patch("my_support_agent.tools.summary.get_tenant_id", return_value=TENANT_ID)
def test_empty_period(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase(enrollment_rows=[], payment_rows=[])
    from my_support_agent.tools.summary import get_summary
    result = get_summary("day")
    assert result["total_enrollments"] == 0
    assert result["total_revenue_mmk"] == 0


@patch("my_support_agent.tools.summary.get_supabase")
@patch("my_support_agent.tools.summary.get_tenant_id", return_value=TENANT_ID)
def test_invalid_period(mock_tenant, mock_supabase):
    from my_support_agent.tools.summary import get_summary
    result = get_summary("month")
    assert "error" in result


@patch("my_support_agent.tools.summary.get_supabase")
@patch("my_support_agent.tools.summary.get_tenant_id", return_value=TENANT_ID)
def test_week_period_accepted(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase(
        enrollment_rows=[_enrollment("e1", "confirmed")],
        payment_rows=[_payment("e1", 40000)],
    )
    from my_support_agent.tools.summary import get_summary
    result = get_summary("week")
    assert result["period"] == "week"
    assert "since" in result
