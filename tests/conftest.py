import pytest
import my_support_agent.api_client as api_client_module


@pytest.fixture(autouse=True)
def reset_api_client():
    api_client_module._base_url = None
    api_client_module._secret = None
    yield
    api_client_module._base_url = None
    api_client_module._secret = None
