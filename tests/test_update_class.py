"""Tests for update_class, confirm_update, and cancel_update."""

from unittest.mock import MagicMock, patch


TENANT_ID = "tenant-abc"
CLASS_ID = "class-uuid-001"
CLASS_NAME = "N3 Evening"


def _make_context(initial_state=None):
    ctx = MagicMock()
    ctx.state = initial_state or {}
    return ctx


def _make_supabase_read(row):
    resp = MagicMock()
    resp.data = [row] if row else []

    chain = MagicMock()
    chain.execute.return_value = resp
    chain.eq.return_value = chain
    chain.select.return_value = chain
    chain.update.return_value = chain

    client = MagicMock()
    client.table.return_value = chain
    return client


# ---------------------------------------------------------------------------
# get_class_details
# ---------------------------------------------------------------------------

@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_get_class_details_returns_fields(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase_read(
        {"id": CLASS_ID, "level": CLASS_NAME, "seat_total": 20, "fee_mmk": 60000}
    )
    from my_support_agent.tools.update_class import get_class_details
    result = get_class_details(CLASS_ID)
    assert result["class_id"] == CLASS_ID
    assert result["class_name"] == CLASS_NAME
    assert result["capacity"] == 20
    assert result["price_mmk"] == 60000


@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_get_class_details_not_found(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase_read(None)
    from my_support_agent.tools.update_class import get_class_details
    result = get_class_details("nonexistent")
    assert "error" in result


# ---------------------------------------------------------------------------
# update_class — stages to state, does NOT write
# ---------------------------------------------------------------------------

@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_update_class_stages_pending(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase_read(
        {"id": CLASS_ID, "level": CLASS_NAME, "seat_total": 20, "fee_mmk": 60000}
    )
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, capacity=25)

    assert result["confirmation_required"] is True
    assert "summary" in result
    assert "25" in result["summary"]
    pending = ctx.state["pending_update"]
    assert pending["class_id"] == CLASS_ID
    assert pending["capacity"] == 25
    assert pending["current_capacity"] == 20
    # DB must NOT have been written
    mock_supabase.return_value.table.return_value.update.assert_not_called()


@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_update_class_stages_price(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase_read(
        {"id": CLASS_ID, "level": CLASS_NAME, "seat_total": 20, "fee_mmk": 60000}
    )
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, price_mmk=75000)
    assert ctx.state["pending_update"]["price_mmk"] == 75000
    assert ctx.state["pending_update"]["current_price"] == 60000


@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_update_class_no_fields_returns_error(mock_tenant, mock_supabase):
    mock_supabase.return_value = _make_supabase_read(
        {"id": CLASS_ID, "level": CLASS_NAME, "seat_total": 20, "fee_mmk": 60000}
    )
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx)
    assert "error" in result
    assert not ctx.state.get("pending_update")


# ---------------------------------------------------------------------------
# confirm_update — executes PATCH
# ---------------------------------------------------------------------------

@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_confirm_update_patches_supabase(mock_tenant, mock_supabase):
    update_resp = MagicMock()
    update_resp.data = [{"id": CLASS_ID}]

    chain = MagicMock()
    chain.execute.return_value = update_resp
    chain.eq.return_value = chain
    chain.update.return_value = chain

    mock_supabase.return_value.table.return_value = chain

    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "class_name": CLASS_NAME,
            "current_capacity": 20,
            "current_price": 60000,
            "capacity": 25,
            "price_mmk": None,
        }
    })
    from my_support_agent.tools.update_class import confirm_update
    result = confirm_update(ctx)

    assert result["success"] is True
    assert not ctx.state.get("pending_update")
    chain.update.assert_called_once_with({"seat_total": 25})


@patch("my_support_agent.tools.update_class.get_supabase")
@patch("my_support_agent.tools.update_class.get_tenant_id", return_value=TENANT_ID)
def test_confirm_update_no_pending_returns_error(mock_tenant, mock_supabase):
    ctx = _make_context()
    from my_support_agent.tools.update_class import confirm_update
    result = confirm_update(ctx)
    assert "error" in result


# ---------------------------------------------------------------------------
# cancel_update — clears state
# ---------------------------------------------------------------------------

def test_cancel_update_clears_state():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "class_name": CLASS_NAME,
            "capacity": 25,
            "price_mmk": None,
        }
    })
    from my_support_agent.tools.update_class import cancel_update
    result = cancel_update(ctx)
    assert result["cancelled"] is True
    assert not ctx.state.get("pending_update")


def test_cancel_update_no_pending_is_graceful():
    ctx = _make_context()
    from my_support_agent.tools.update_class import cancel_update
    result = cancel_update(ctx)
    assert "message" in result
    assert "error" not in result
