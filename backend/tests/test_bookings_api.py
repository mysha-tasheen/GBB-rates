"""Booking endpoints — live LiteAPI + real DB (no mocks)."""

import pytest

from tests.helpers import (
    API_PREFIX,
    api_get,
    api_post_json,
    api_put_json,
    assert_ok,
    future_stay,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(transaction=True),
]


async def _us_hotel_and_offer(api_client, auth_headers):
    hotels = (
        await api_get(
            api_client,
            f"{API_PREFIX}/hotels",
            query={"country_code": "US", "limit": 5},
            headers=auth_headers,
        )
    ).json()["hotels"]
    check_in, check_out = future_stay()
    min_rates = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/hotel-min-rates",
            {
                "hotel_ids": [h["hotel_id"] for h in hotels],
                "check_in": check_in,
                "check_out": check_out,
                "guests": 2,
                "guest_nationality": "US",
                "commission": 0,
            },
            headers=auth_headers,
        )
    ).json()["rates"]
    if not min_rates:
        pytest.skip("No min rates returned for test hotels — try different dates")
    rate = min_rates[0]
    return rate["hotel_id"], rate["offer_id"], check_in, check_out


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
        f"{API_PREFIX}/bookings/nonexistent-supplier-booking-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_prebook(api_client, auth_headers, nuitee_required):
    _, offer_id, _, _ = await _us_hotel_and_offer(api_client, auth_headers)

    create = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/prebook",
        {
            "offer_id": offer_id,
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
    response = await api_get(
        api_client, f"{API_PREFIX}/bookings", headers=auth_headers
    )
    assert_ok(response, 200)
    data = response.json()
    assert "bookings" in data
    assert data["total"] == len(data["bookings"])


@pytest.mark.booking_flow
@pytest.mark.asyncio
async def test_confirm_get_cancel_booking(api_client, auth_headers, booking_flow_required):
    """Live sandbox: prebook → confirm → get → cancel (costs sandbox credit)."""
    _, offer_id, _, _ = await _us_hotel_and_offer(api_client, auth_headers)

    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {"offer_id": offer_id, "use_payment_sdk": False, "commission": 0},
            headers=auth_headers,
        )
    ).json()

    confirm = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/confirm",
        {
            "booking_id": prebook["booking_id"],
            "holder": {
                "first_name": "Test",
                "last_name": "Agent",
                "email": "integration@test.gbb",
                "phone": "+10000000000",
            },
            "guests": [
                {
                    "occupancy_number": 1,
                    "first_name": "Test",
                    "last_name": "Guest",
                    "email": "integration@test.gbb",
                }
            ],
            "payment_method": "ACC_CREDIT_CARD",
        },
        headers=auth_headers,
    )
    assert_ok(confirm, 200)
    confirmed = confirm.json()
    assert confirmed["supplier_booking_id"]
    assert confirmed["status"]

    supplier_id = confirmed["supplier_booking_id"]

    detail = await api_get(
        api_client,
        f"{API_PREFIX}/bookings/{supplier_id}",
        headers=auth_headers,
    )
    assert_ok(detail, 200)
    assert detail.json()["supplier_booking_id"] == supplier_id

    cancel = await api_client.put(
        f"{API_PREFIX}/bookings/{supplier_id}",
        headers=auth_headers,
    )
    assert_ok(cancel, 200)
    assert cancel.json()["status"] in ("CANCELLED", "CANCELLED_WITH_CHARGES")


@pytest.mark.booking_flow
@pytest.mark.asyncio
async def test_amend_guest_name(api_client, auth_headers, booking_flow_required):
    """Amend holder on a confirmed sandbox booking."""
    _, offer_id, _, _ = await _us_hotel_and_offer(api_client, auth_headers)

    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {"offer_id": offer_id, "use_payment_sdk": False, "commission": 0},
            headers=auth_headers,
        )
    ).json()

    confirm = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/confirm",
            {
                "booking_id": prebook["booking_id"],
                "holder": {
                    "first_name": "Before",
                    "last_name": "Amend",
                    "email": "before@test.gbb",
                },
                "guests": [
                    {
                        "first_name": "Before",
                        "last_name": "Amend",
                        "email": "before@test.gbb",
                    }
                ],
                "payment_method": "ACC_CREDIT_CARD",
            },
            headers=auth_headers,
        )
    ).json()

    supplier_id = confirm["supplier_booking_id"]

    amend = await api_put_json(
        api_client,
        f"{API_PREFIX}/bookings/{supplier_id}/amend",
        {
            "holder": {
                "first_name": "After",
                "last_name": "Amend",
                "email": "after@test.gbb",
            },
            "remarks": "Integration test amend",
        },
        headers=auth_headers,
    )
    assert_ok(amend, 200)
    data = amend.json()
    assert data["holder_first_name"] == "After"
    assert data["holder_email"] == "after@test.gbb"

    await api_client.put(
        f"{API_PREFIX}/bookings/{supplier_id}", headers=auth_headers
    )


@pytest.mark.booking_flow
@pytest.mark.asyncio
async def test_alternative_prebooks(api_client, auth_headers, booking_flow_required):
    """Hard amendment search on a confirmed booking."""
    _, offer_id, _, _ = await _us_hotel_and_offer(api_client, auth_headers)
    check_in, check_out = future_stay(days_ahead=60, nights=3)

    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {"offer_id": offer_id, "use_payment_sdk": False, "commission": 0},
            headers=auth_headers,
        )
    ).json()

    confirm = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/confirm",
            {
                "booking_id": prebook["booking_id"],
                "holder": {
                    "first_name": "Alt",
                    "last_name": "Prebook",
                    "email": "alt@test.gbb",
                },
                "guests": [
                    {
                        "first_name": "Alt",
                        "last_name": "Prebook",
                        "email": "alt@test.gbb",
                    }
                ],
                "payment_method": "ACC_CREDIT_CARD",
            },
            headers=auth_headers,
        )
    ).json()

    supplier_id = confirm["supplier_booking_id"]

    alt = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/{supplier_id}/alternative-prebooks",
        {
            "occupancies": [{"adults": 2, "children": []}],
            "check_in": check_in,
            "check_out": check_out,
            "commission": 0,
        },
        headers=auth_headers,
    )
    assert_ok(alt, 200)
    data = alt.json()
    assert data["supplier_booking_id"] == supplier_id
    assert data["total"] >= 0

    await api_client.put(
        f"{API_PREFIX}/bookings/{supplier_id}", headers=auth_headers
    )
