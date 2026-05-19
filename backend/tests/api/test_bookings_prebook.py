import pytest

from tests.support import API_PREFIX, api_get, api_post_json, assert_ok, future_stay

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(transaction=True),
]


@pytest.mark.asyncio
async def test_bookings_unauthorized(api_client):
    response = await api_get(api_client, f"{API_PREFIX}/bookings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_unknown_booking(api_client, auth_headers):
    response = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/confirm",
        {
            "booking_id": "00000000-0000-0000-0000-000000000000",
            "holder": {
                "first_name": "Test",
                "last_name": "Guest",
                "email": "integration@test.gbb",
            },
            "guests": [
                {
                    "first_name": "Test",
                    "last_name": "Guest",
                    "email": "integration@test.gbb",
                }
            ],
            "payment_method": "ACC_CREDIT_CARD",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_booking_not_found(api_client, auth_headers, nuitee_required):
    response = await api_get(
        api_client,
        f"{API_PREFIX}/bookings/00000000-0000-0000-0000-000000000099",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_prebook(
    api_client, auth_headers, nuitee_required, us_hotel_offer
):
    create = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/prebook",
        {
            "offer_id": us_hotel_offer["offer_id"],
            "use_payment_sdk": False,
            "commission": 15.0,
        },
        headers=auth_headers,
    )
    assert_ok(create, 200)
    prebook = create.json()
    assert prebook["prebook_id"]
    assert prebook["booking_id"]
    assert prebook["price"] > 0
    assert prebook["room"]["room_name"]

    get_resp = await api_get(
        api_client,
        f"{API_PREFIX}/bookings/prebook/{prebook['prebook_id']}",
        headers=auth_headers,
    )
    assert_ok(get_resp, 200)
    fetched = get_resp.json()
    assert fetched["prebook_id"] == prebook["prebook_id"]
    assert fetched["booking_id"] == prebook["booking_id"]


@pytest.mark.asyncio
async def test_list_bookings_inventory(api_client, auth_headers, nuitee_required):
    check_in, check_out = future_stay()
    response = await api_get(
        api_client,
        f"{API_PREFIX}/bookings",
        query={"start_date": check_in, "end_date": check_out},
        headers=auth_headers,
    )
    assert_ok(response, 200)
    data = response.json()
    assert "bookings" in data
    assert data["total"] == len(data["bookings"])
