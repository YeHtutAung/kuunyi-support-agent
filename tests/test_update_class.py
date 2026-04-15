"""Tests for update_class, confirm_update, cancel_update (API-backed)."""

from unittest.mock import MagicMock, patch


CLASS_ID = "class-uuid-001"


def _make_context(initial_state=None):
    ctx = MagicMock()
    ctx.state = initial_state or {}
    return ctx


# ---------------------------------------------------------------------------
# update_class — stages to state, does NOT call API
# ---------------------------------------------------------------------------

def test_update_class_stages_capacity():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, capacity=25)

    assert result["confirmation_required"] is True
    assert "25" in result["summary"]
    pending = ctx.state["pending_update"]
    assert pending["class_id"] == CLASS_ID
    assert pending["capacity"] == 25


def test_update_class_stages_price():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, price_mmk=75000)

    assert ctx.state["pending_update"]["price_mmk"] == 75000
    assert "75000" in result["summary"]


def test_update_class_stages_status():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx, status="closed")

    assert ctx.state["pending_update"]["status"] == "closed"
    assert "closed" in result["summary"]


def test_update_class_no_fields_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.update_class import update_class
    result = update_class(CLASS_ID, ctx)

    assert "error" in result
    assert not ctx.state.get("pending_update")


def test_update_class_does_not_call_api():
    ctx = _make_context()
    with patch("my_support_agent.tools.update_class.call_admin_api") as mock_api:
        from my_support_agent.tools.update_class import update_class
        update_class(CLASS_ID, ctx, capacity=25)
    mock_api.assert_not_called()


# ---------------------------------------------------------------------------
# confirm_update — calls PATCH API
# ---------------------------------------------------------------------------

def test_confirm_update_calls_patch_api():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": 25,
            "price_mmk": None,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID, "seat_total": 25}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        result = confirm_update(ctx)

    mock_api.assert_called_once_with(
        "PATCH", f"/api/classes/{CLASS_ID}", json={"seat_total": 25}
    )
    assert result["success"] is True
    assert not ctx.state.get("pending_update")


def test_confirm_update_sends_price():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": None,
            "price_mmk": 80000,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        confirm_update(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body == {"fee_mmk": 80000}


def test_confirm_update_sends_status():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": None,
            "price_mmk": None,
            "status": "closed",
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"id": CLASS_ID}) as mock_api:
        from my_support_agent.tools.update_class import confirm_update
        confirm_update(ctx)

    body = mock_api.call_args.kwargs["json"]
    assert body == {"status": "closed"}


def test_confirm_update_no_pending_returns_error():
    ctx = _make_context()
    from my_support_agent.tools.update_class import confirm_update
    result = confirm_update(ctx)
    assert "error" in result


def test_confirm_update_forwards_api_error():
    ctx = _make_context({
        "pending_update": {
            "class_id": CLASS_ID,
            "capacity": 25,
            "price_mmk": None,
            "status": None,
        }
    })
    with patch("my_support_agent.tools.update_class.call_admin_api",
               return_value={"error": "Not found."}):
        from my_support_agent.tools.update_class import confirm_update
        result = confirm_update(ctx)
    assert "error" in result
    assert ctx.state.get("pending_update") is not None  # state preserved so admin can retry


# ---------------------------------------------------------------------------
# cancel_update — clears state
# ---------------------------------------------------------------------------

def test_cancel_update_clears_state():
    ctx = _make_context({
        "pending_update": {"class_id": CLASS_ID, "capacity": 25, "price_mmk": None, "status": None}
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
