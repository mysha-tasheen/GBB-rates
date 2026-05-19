import pytest
from tests.support import (
    API_PREFIX,
    api_get,
    api_post_json,
    api_put_json,
    assert_ok,
    future_stay,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.booking_flow,
    pytest.mark.django_db(transaction=True),
]


def _holder(email: str = "integration@test.gbb"):
    return {
        "first_name": "Test",
        "last_name": "Agent",
        "email": email,
        "phone": "+10000000000",
    }


def _guest(email: str = "integration@test.gbb"):
    return {
        "occupancy_number": 1,
        "first_name": "Test",
        "last_name": "Guest",
        "email": email,
    }


async def _confirm_booking(api_client, auth_headers, booking_id: str, email: str):
    return await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/confirm",
        {
            "booking_id": booking_id,
            "holder": _holder(email),
            "guests": [_guest(email)],
            "payment_method": "ACC_CREDIT_CARD",
        },
        headers=auth_headers,
    )


async def _cancel_booking(api_client, reference: str, auth_headers: dict):
    return await api_client.put(
        f"{API_PREFIX}/bookings/{reference}/cancel",
        headers=auth_headers,
    )


@pytest.mark.asyncio
async def test_confirm_get_cancel_booking(
    api_client, auth_headers, booking_flow_required, us_hotel_offer
):
    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {
                "offer_id": us_hotel_offer["offer_id"],
                "use_payment_sdk": False,
                "commission": 0,
            },
            headers=auth_headers,
        )
    ).json()

    confirm = await _confirm_booking(
        api_client, auth_headers, prebook["booking_id"], "integration@test.gbb"
    )
    assert_ok(confirm, 200)
    confirmed = confirm.json()
    reference = confirmed["booking_reference"]
    assert reference
    assert confirmed["status"]

    detail = await api_get(
        api_client,
        f"{API_PREFIX}/bookings/{reference}",
        headers=auth_headers,
    )
    assert_ok(detail, 200)
    assert detail.json()["booking_reference"] == reference

    cancel = await _cancel_booking(api_client, reference, auth_headers)
    assert_ok(cancel, 200)
    assert cancel.json()["status"] in ("CANCELLED", "CANCELLED_WITH_CHARGES")


@pytest.mark.asyncio
async def test_amend_guest_name(
    api_client, auth_headers, booking_flow_required, us_hotel_offer
):
    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {
                "offer_id": us_hotel_offer["offer_id"],
                "use_payment_sdk": False,
                "commission": 0,
            },
            headers=auth_headers,
        )
    ).json()

    confirm = await _confirm_booking(
        api_client, auth_headers, prebook["booking_id"], "before@test.gbb"
    )
    assert_ok(confirm, 200)
    reference = confirm.json()["booking_reference"]

    amend = await api_put_json(
        api_client,
        f"{API_PREFIX}/bookings/{reference}/amend",
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

    await _cancel_booking(api_client, reference, auth_headers)


@pytest.mark.asyncio
async def test_alternative_prebooks(
    api_client, auth_headers, booking_flow_required, us_hotel_offer
):
    check_in, check_out = future_stay(days_ahead=60, nights=3)

    prebook = (
        await api_post_json(
            api_client,
            f"{API_PREFIX}/bookings/prebook",
            {
                "offer_id": us_hotel_offer["offer_id"],
                "use_payment_sdk": False,
                "commission": 0,
            },
            headers=auth_headers,
        )
    ).json()

    confirm = await _confirm_booking(
        api_client, auth_headers, prebook["booking_id"], "alt@test.gbb"
    )
    assert_ok(confirm, 200)
    reference = confirm.json()["booking_reference"]

    alt = await api_post_json(
        api_client,
        f"{API_PREFIX}/bookings/{reference}/alternative-prebooks",
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
    assert data["booking_reference"] == reference
    assert data["total"] >= 0

    await _cancel_booking(api_client, reference, auth_headers)
