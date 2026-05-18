import logging
from ninja import Router
from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.search_common import commission_service, logger, search_service
from apps.api.v1.mappers import map_hotel_min_rates_for_agent
from apps.api.v1.schemas.search_schemas import HotelMinRatesRequest, HotelMinRatesResponse

router = Router(tags=["search"])


@router.post("/hotel-min-rates", response=HotelMinRatesResponse, auth=api_key_auth)
async def search_hotel_min_rates(request, payload: HotelMinRatesRequest):
    
    agent, _ = request.auth
    logger.info(
        "Agent %s min-rates for %s hotels",
        agent.company_name,
        len(payload.hotel_ids),
    )

    rates = await search_service.get_hotel_min_rates(
        hotel_ids=payload.hotel_ids,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        currency=payload.currency,
        guest_nationality=payload.guest_nationality.upper(),
    )

    rates = commission_service.apply_flat_to_min_rates(rates, payload.commission)

    return map_hotel_min_rates_for_agent(
        rates,
        check_in=payload.check_in.isoformat(),
        check_out=payload.check_out.isoformat(),
        currency=payload.currency,
    )
