import pytest

from tests.support import API_PREFIX, api_get, assert_ok

pytestmark = [pytest.mark.django_db(transaction=True)]


@pytest.mark.asyncio
async def test_me_authenticated(api_client, auth_headers, test_agent):
    agent, api_key = test_agent
    response = await api_get(api_client, f"{API_PREFIX}/me", headers=auth_headers)
    assert_ok(response, 200)
    data = response.json()
    assert data["agent_id"] == str(agent.id)
    assert data["company_name"] == "GBB Integration Test"
    assert data["api_key_name"] == api_key.name
    assert data["rate_limit"] == 1000


@pytest.mark.asyncio
async def test_me_missing_api_key(api_client):
    response = await api_get(api_client, f"{API_PREFIX}/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_api_key(api_client):
    response = await api_get(
        api_client,
        f"{API_PREFIX}/me",
        headers={"Authorization": "ApiKey invalid-key-000"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_inactive_api_key(api_client, inactive_auth_headers):
    response = await api_get(
        api_client, f"{API_PREFIX}/me", headers=inactive_auth_headers
    )
    assert response.status_code == 401
