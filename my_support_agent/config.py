"""Agent configuration — loads .env, resolves tenant, caches knowledge base."""

import os
from pathlib import Path
from dotenv import load_dotenv
from my_support_agent.db import get_supabase

load_dotenv()

# Resolved at import time
_tenant_id: str | None = None
_tenant_name: str | None = None
_tenant_slug: str | None = None
_knowledge_base: str | None = None


def _resolve_tenant() -> None:
    """Resolve TENANT_SLUG from .env to tenant_id UUID via Supabase."""
    global _tenant_id, _tenant_name, _tenant_slug

    _tenant_slug = os.environ.get("TENANT_SLUG")
    if not _tenant_slug:
        raise RuntimeError("TENANT_SLUG environment variable must be set.")

    supabase = get_supabase()
    response = (
        supabase.table("tenants")
        .select("id, name")
        .eq("subdomain", _tenant_slug)
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"Tenant not found for slug: {_tenant_slug}")

    _tenant_id = response.data[0]["id"]
    _tenant_name = response.data[0]["name"]


def _load_knowledge_base() -> None:
    """Load FAQ markdown file for the current tenant."""
    global _knowledge_base

    kb_dir = Path(__file__).parent / "knowledge_base"
    kb_file = kb_dir / f"{_tenant_slug}.md"

    if kb_file.exists():
        _knowledge_base = kb_file.read_text(encoding="utf-8")
    else:
        print(f"Warning: Knowledge base file not found: {kb_file}")
        _knowledge_base = None


def init() -> None:
    """Initialize config — call once at startup."""
    _resolve_tenant()
    _load_knowledge_base()


def init_admin() -> None:
    """Lightweight init for admin agent — no Supabase required.

    Reads TENANT_SLUG and optionally TENANT_NAME from env, then
    initialises the shared API client (ADMIN_API_BASE_URL + AGENT_SECRET).
    """
    global _tenant_slug, _tenant_name

    _tenant_slug = os.environ.get("TENANT_SLUG")
    if not _tenant_slug:
        raise RuntimeError("TENANT_SLUG environment variable must be set.")

    _tenant_name = os.environ.get("TENANT_NAME", _tenant_slug)

    from my_support_agent.api_client import init_api_client
    init_api_client()


def get_tenant_id() -> str:
    if _tenant_id is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_id


def get_tenant_name() -> str:
    if _tenant_name is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_name


def get_tenant_slug() -> str:
    if _tenant_slug is None:
        raise RuntimeError("Config not initialized. Call config.init() first.")
    return _tenant_slug


def get_knowledge_base() -> str | None:
    return _knowledge_base
