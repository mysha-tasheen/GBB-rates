import os

import pytest
from django.contrib.auth.models import User
from django.test import AsyncClient

from apps.agents.models import Agent, AgentApiKey
from apps.core.models import Supplier


@pytest.fixture(autouse=True)
def seed_liteapi_supplier(db):
    Supplier.objects.update_or_create(
        name="liteapi",
        defaults={
            "display_name": "Nuitee / LiteAPI",
            "commission_percent": "3.00",
            "is_active": True,
        },
    )




@pytest.fixture
def api_client() -> AsyncClient:
    return AsyncClient()


@pytest.fixture
def test_agent(db):
    user = User.objects.create_user(
        username="integration@test.gbb",
        email="integration@test.gbb",
        password="IntegrationTest123!",
        first_name="GBB Test",
    )
    agent = Agent.objects.create(
        user=user,
        company_name="GBB Integration Test",
        phone="+10000000000",
        is_active=True,
    )
    api_key = AgentApiKey.objects.create(
        agent=agent,
        name="Integration Test Key",
        rate_limit=1000,
    )
    return agent, api_key


@pytest.fixture
def auth_headers(test_agent):
    _, api_key = test_agent
    return {"Authorization": f"ApiKey {api_key.key}"}


@pytest.fixture
def inactive_auth_headers(test_agent):
    agent, api_key = test_agent
    api_key.is_active = False
    api_key.save(update_fields=["is_active"])
    return {"Authorization": f"ApiKey {api_key.key}"}


@pytest.fixture
def nuitee_required():
    if not os.environ.get("NUITEE_API_KEY", "").strip():
        pytest.skip("NUITEE_API_KEY is required for this integration test")


@pytest.fixture
def booking_flow_required(nuitee_required):
    if os.environ.get("NUITEE_RUN_BOOKING_FLOW", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("Set NUITEE_RUN_BOOKING_FLOW=1 to run live book/confirm/cancel tests")
