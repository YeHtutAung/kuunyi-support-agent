"""Shared HTTP client for KuuNyi admin API."""

import os
import requests as _requests

_base_url: str | None = None
_secret: str | None = None


def init_api_client() -> None:
    """Initialize the API client. Called once at startup via init_admin()."""
    global _base_url, _secret

    base_url = os.environ.get("ADMIN_API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("AGENT_SECRET")

    if not base_url:
        raise RuntimeError("ADMIN_API_BASE_URL environment variable must be set.")
    if not secret:
        raise RuntimeError("AGENT_SECRET environment variable must be set.")
    if not base_url.startswith("https://"):
        raise RuntimeError("ADMIN_API_BASE_URL must use HTTPS.")

    _base_url = base_url
    _secret = secret


def call_admin_api(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Make an authenticated request to the KuuNyi admin API.

    Returns a dict on success. Returns {"error": "..."} on any failure.
    List responses are wrapped as {"data": [...]}.
    The AGENT_SECRET is never included in error output.
    """
    if not _base_url or not _secret:
        raise RuntimeError("API client not initialized. Call init_api_client() first.")

    tenant_slug = os.environ.get("TENANT_SLUG", "")
    headers = {
        "x-agent-secret": _secret,
        "x-tenant-slug": tenant_slug,
    }

    try:
        response = _requests.request(
            method.upper(),
            f"{_base_url}{path}",
            headers=headers,
            params=params,
            json=json,
            timeout=10,
        )
    except _requests.Timeout:
        return {"error": "Request timed out. Please try again."}
    except _requests.RequestException:
        return {"error": "Unable to reach the API. Please try again shortly."}

    if response.status_code in (401, 403):
        return {"error": "Authentication failed. Check AGENT_SECRET configuration."}
    if response.status_code == 404:
        return {"error": "Not found."}
    if not response.ok:
        return {"error": f"API request failed: {response.status_code}."}

    data = response.json()
    if isinstance(data, list):
        return {"data": data}
    return data
