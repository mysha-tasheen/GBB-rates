from apps.api.v1.schemas.search_schemas import (
    HotelEssential,
    HotelMinRate,
    HotelMinRatesResponse,
    RateEssential,
    RoomTypeEssential,
    SearchResponseEssential,
)


def map_hotel_min_rates_for_agent(
    rates: list[dict],
    check_in: str,
    check_out: str,
    currency: str,
) -> HotelMinRatesResponse:
    items = [
        HotelMinRate(
            hotel_id=r["hotel_id"],
            price=r["_agent_price"],
            offer_id=r["offer_id"],
        )
        for r in rates
        if r.get("hotel_id")
    ]
    return HotelMinRatesResponse(
        check_in=check_in,
        check_out=check_out,
        currency=currency,
        rates=items,
        total=len(items),
    )


def map_hotel_rates_for_agent(internal: dict, total_offers: int) -> SearchResponseEssential:
    rooms = []
    for room in internal.get("rooms", []):
        rates = [
            RateEssential(
                rate_id=rate["rate_id"],
                room_name=rate["room_name"],
                board_type=rate["board_type"],
                board_name=rate["board_name"],
                price=rate["_agent_price"],
                currency=rate["currency"],
                cancellation_deadline=rate.get("cancellation_deadline"),
                refundable=rate.get("refundable", True),
                payment_types=rate.get("payment_types", []),
            )
            for rate in room.get("rates", [])
            if rate.get("_agent_price", 0) > 0
        ]
        if not rates:
            continue
        rooms.append(
            RoomTypeEssential(
                room_type_id=room["room_type_id"],
                offer_id=room["offer_id"],
                rates=rates,
            )
        )

    hotel = internal["hotel"]
    return SearchResponseEssential(
        hotel=HotelEssential(
            hotel_id=hotel["hotel_id"],
            name=hotel["name"],
            address=hotel["address"],
            rating=hotel["rating"],
            main_photo=hotel["main_photo"],
        ),
        check_in=internal["check_in"],
        check_out=internal["check_out"],
        nights=internal["nights"],
        rooms=rooms,
        total_offers=total_offers,
    )
