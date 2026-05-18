import pytest

from tests.helpers import API_PREFIX, api_post_json, assert_ok

pytestmark = [pytest.mark.django_db(transaction=True)]


@pytest.mark.asyncio
async def test_login_success(api_client, test_agent):
    _, _ = test_agent
    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/auth/login",
        {
            "email": "integration@test.gbb",
            "password": "IntegrationTest123!",
        },
    )
    assert_ok(response, 200)
    data = response.json()
    assert data["email"] == "integration@test.gbb"
    assert data["agent_name"] == "GBB Integration Test"
    assert data["api_key"].startswith("b2b_live_")
    assert data["rate_limit"] == 1000


@pytest.mark.asyncio
async def test_login_invalid_credentials(api_client, test_agent):
    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/auth/login",
        {"email": "integration@test.gbb", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_unknown_user(api_client):
    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/auth/login",
        {"email": "nobody@test.gbb", "password": "nope"},
    )
    assert response.status_code == 401
