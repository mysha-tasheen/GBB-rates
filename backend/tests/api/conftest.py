import pytest
from tests.support import API_PREFIX, api_get, api_post_json, future_stay


@pytest.fixture
async def us_hotel_offer(api_client, auth_headers, nuitee_required):
    
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
    return {
        "hotel_id": rate["hotel_id"],
        "offer_id": rate["offer_id"],
        "check_in": check_in,
        "check_out": check_out,
    }
