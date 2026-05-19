import pytest

from tests.support import API_PREFIX, api_get, api_post_json, assert_ok, future_stay

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(transaction=True),
]


@pytest.mark.asyncio
async def test_list_countries_unauthorized(api_client):
    response = await api_get(api_client, f"{API_PREFIX}/countries")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_currencies_unauthorized(api_client):
    response = await api_get(api_client, f"{API_PREFIX}/currencies")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_currencies(api_client, auth_headers, nuitee_required):
    response = await api_get(
        api_client, f"{API_PREFIX}/currencies", headers=auth_headers
    )
    assert_ok(response, 200)
    data = response.json()
    assert data["total"] >= 1
    codes = {c["code"] for c in data["currencies"]}
    assert "FJD" in codes
    assert "USD" in codes


@pytest.mark.asyncio
async def test_list_countries(api_client, auth_headers, nuitee_required):
    response = await api_get(
        api_client, f"{API_PREFIX}/countries", headers=auth_headers
    )
    assert_ok(response, 200)
    data = response.json()
    assert data["total"] >= 1
    assert any(c["code"] == "US" for c in data["countries"])


@pytest.mark.asyncio
async def test_list_hotels(api_client, auth_headers, nuitee_required):
    response = await api_get(
        api_client,
        f"{API_PREFIX}/hotels",
        query={"country_code": "US", "limit": 5},
        headers=auth_headers,
    )
    assert_ok(response, 200)
    data = response.json()
    assert data["country_code"] == "US"
    assert data["total"] >= 1
    assert data["hotels"][0]["hotel_id"]


@pytest.mark.asyncio
async def test_hotel_min_rates(api_client, auth_headers, nuitee_required):
    hotels = (
        await api_get(
            api_client,
            f"{API_PREFIX}/hotels",
            query={"country_code": "US", "limit": 3},
            headers=auth_headers,
        )
    ).json()["hotels"]
    hotel_ids = [h["hotel_id"] for h in hotels[:3]]
    check_in, check_out = future_stay()

    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/hotel-min-rates",
        {
            "hotel_ids": hotel_ids,
            "check_in": check_in,
            "check_out": check_out,
            "guests": 2,
            "currency": "USD",
            "guest_nationality": "US",
            "commission": 10.0,
        },
        headers=auth_headers,
    )
    assert_ok(response, 200)
    data = response.json()
    for rate in data["rates"]:
        assert rate["hotel_id"] in hotel_ids
        assert rate["price"] > 0
        assert rate["offer_id"]


@pytest.mark.asyncio
async def test_hotel_rates(api_client, auth_headers, nuitee_required):
    hotels = (
        await api_get(
            api_client,
            f"{API_PREFIX}/hotels",
            query={"country_code": "US", "limit": 1},
            headers=auth_headers,
        )
    ).json()["hotels"]
    hotel_id = hotels[0]["hotel_id"]
    check_in, check_out = future_stay()

    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/hotel-rates",
        {
            "hotel_id": hotel_id,
            "check_in": check_in,
            "check_out": check_out,
            "guests": 2,
            "currency": "USD",
            "guest_nationality": "US",
            "commission": 5.0,
        },
        headers=auth_headers,
    )
    assert_ok(response, 200)
    data = response.json()
    assert data["hotel"]["hotel_id"] == hotel_id
    assert data["nights"] >= 1
    assert data["rooms"]
    room_with_rates = next(r for r in data["rooms"] if r["rates"])
    assert room_with_rates["room_name"]
    assert "payment_types" not in room_with_rates["rates"][0]
