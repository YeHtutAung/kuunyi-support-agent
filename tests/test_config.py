from pathlib import Path
import os
import pytest
from unittest.mock import patch
import my_support_agent.config as config_module


def test_knowledge_base_file_exists():
    """Verify the nihon-moment knowledge base file exists."""
    kb_file = (
        Path(__file__).parent.parent
        / "my_support_agent"
        / "knowledge_base"
        / "nihon-moment.md"
    )
    assert kb_file.exists(), f"Knowledge base file not found: {kb_file}"


# Helper function to reset module state
def _reset_config():
    config_module._tenant_slug = None
    config_module._tenant_name = None


# Tests for config.init_admin()
def test_init_admin_sets_tenant_slug():
    """Test that init_admin() sets _tenant_slug from TENANT_SLUG env var."""
    _reset_config()
    with patch("my_support_agent.api_client.init_api_client"):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment", "TENANT_NAME": "Nihon Moment"}, clear=True):
            config_module.init_admin()
    assert config_module._tenant_slug == "nihon-moment"


def test_init_admin_sets_tenant_name_from_env():
    """Test that init_admin() sets _tenant_name from TENANT_NAME env var."""
    _reset_config()
    with patch("my_support_agent.api_client.init_api_client"):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment", "TENANT_NAME": "Nihon Moment"}, clear=True):
            config_module.init_admin()
    assert config_module._tenant_name == "Nihon Moment"


def test_init_admin_falls_back_tenant_name_to_slug():
    """Test that init_admin() falls back to TENANT_SLUG when TENANT_NAME is missing."""
    _reset_config()
    with patch("my_support_agent.api_client.init_api_client"):
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}, clear=True):
            config_module.init_admin()
    assert config_module._tenant_name == "nihon-moment"


def test_init_admin_raises_if_tenant_slug_missing():
    """Test that init_admin() raises RuntimeError when TENANT_SLUG is missing."""
    _reset_config()
    with patch("my_support_agent.api_client.init_api_client"):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="TENANT_SLUG"):
                config_module.init_admin()


def test_init_admin_calls_init_api_client():
    """Test that init_admin() calls init_api_client()."""
    _reset_config()
    with patch("my_support_agent.api_client.init_api_client") as mock_init:
        with patch.dict(os.environ, {"TENANT_SLUG": "nihon-moment"}, clear=True):
            config_module.init_admin()
    mock_init.assert_called_once()
