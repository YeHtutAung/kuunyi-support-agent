"""Tests for api_client."""

import os
import pytest
from unittest.mock import MagicMock, patch
import my_support_agent.api_client as api_client_module


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _setup_client(base_url="https://example.com", secret="s3cr3t", tenant="test-tenant"):
    api_client_module._base_url = base_url
    api_client_module._secret = secret
    return tenant


# ---------------------------------------------------------------------------
# init_api_client
# ---------------------------------------------------------------------------

def test_init_raises_if_base_url_missing():
    with patch.dict(os.environ, {"AGENT_SECRET": "s3cr3t"}, clear=True):
        with pytest.raises(RuntimeError, match="ADMIN_API_BASE_URL"):
            api_client_module.init_api_client()


def test_init_raises_if_secret_missing():
    with patch.dict(os.environ, {"ADMIN_API_BASE_URL": "https://example.com"}, clear=True):
        with pytest.raises(RuntimeError, match="AGENT_SECRET"):
            api_client_module.init_api_client()


def test_init_raises_if_url_not_https():
    with patch.dict(os.environ, {
        "ADMIN_API_BASE_URL": "http://example.com",
        "AGENT_SECRET": "s3cr3t",
    }):
        with pytest.raises(RuntimeError, match="HTTPS"):
            api_client_module.init_api_client()


def test_init_strips_trailing_slash():
    with patch.dict(os.environ, {
        "ADMIN_API_BASE_URL": "https://example.com/",
        "AGENT_SECRET": "s3cr3t",
    }):
        api_client_module.init_api_client()
    assert api_client_module._base_url == "https://example.com"


# ---------------------------------------------------------------------------
# call_admin_api
# ---------------------------------------------------------------------------

def test_call_injects_auth_headers():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp) as mock_req:
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            api_client_module.call_admin_api("GET", "/api/admin/stats")

    headers = mock_req.call_args.kwargs["headers"]
    assert headers["x-agent-secret"] == "s3cr3t"
    assert headers["x-tenant-slug"] == "nihon-moment"


def test_call_wraps_list_response():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": "1"}, {"id": "2"}]

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/intakes")

    assert result == {"data": [{"id": "1"}, {"id": "2"}]}


def test_call_returns_dict_response_as_is():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"total": 5}

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")

    assert result == {"total": 5}


def test_call_returns_error_on_timeout():
    import requests as req_lib
    _setup_client()
    with patch("my_support_agent.api_client._requests.request", side_effect=req_lib.Timeout):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert result == {"error": "Request timed out. Please try again."}


def test_call_returns_error_on_network_failure():
    import requests as req_lib
    _setup_client()
    with patch("my_support_agent.api_client._requests.request", side_effect=req_lib.RequestException):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert result == {"error": "Unable to reach the API. Please try again shortly."}


def test_call_returns_error_on_401():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "Authentication failed" in result["error"]


def test_call_returns_error_on_403():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 403
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "Authentication failed" in result["error"]


def test_call_returns_error_on_404():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/students/bad-id")
    assert result == {"error": "Not found."}


def test_call_returns_error_on_500():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "500" in result["error"]


def test_secret_not_in_error_message():
    _setup_client(secret="super-secret-value")
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")
    assert "super-secret-value" not in result.get("error", "")


def test_call_returns_error_on_malformed_json():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")

    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}):
            result = api_client_module.call_admin_api("GET", "/api/admin/stats")

    assert result == {"error": "API returned an unexpected response format."}


def test_call_sends_empty_tenant_slug_when_unset():
    _setup_client()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}

    env_without_tenant = {k: v for k, v in os.environ.items() if k != "TENANT_SLUG"}
    with patch("my_support_agent.api_client._requests.request", return_value=mock_resp) as mock_req:
        with patch.dict(os.environ, env_without_tenant, clear=True):
            api_client_module.call_admin_api("GET", "/api/admin/stats")

    headers = mock_req.call_args.kwargs["headers"]
    assert headers["x-tenant-slug"] == ""
