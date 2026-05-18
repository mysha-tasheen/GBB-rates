import logging

from ninja import Query, Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth
from apps.api.v1.mappers import map_hotel_min_rates_for_agent, map_hotel_rates_for_agent
from apps.core.pricing import apply_agent_commission, apply_agent_commission_to_min_rates
from apps.api.v1.schemas.search_schemas import (
    CountriesResponse,
    Country,
    HotelEssential,
    HotelListResponse,
    HotelMinRatesRequest,
    HotelMinRatesResponse,
    HotelRatesRequest,
    HotelSummary,
    SearchResponseEssential,
)
from apps.core.wiring import build_catalog_service, build_search_service

router = Router(tags=["search"])
logger = logging.getLogger(__name__)

catalog_service = build_catalog_service()
search_service = build_search_service()


def _supplier_error(exc: Exception, message: str) -> None:
    if isinstance(exc, ValueError):
        raise HttpError(503, str(exc)) from exc
    logger.exception(message)
    raise HttpError(502, message) from exc


@router.get("/countries", response=CountriesResponse, auth=api_key_auth)
async def list_countries(request):
    """
    Step 1 — List countries (ISO-2 codes).

    Use `code` as `country_code` on GET /hotels and as `guest_nationality` on POST /hotel-rates.
    """
    try:
        countries = await catalog_service.list_countries()
    except Exception as exc:
        _supplier_error(exc, "Unable to load countries from supplier")

    items = [Country(code=c["code"], name=c["name"]) for c in countries]
    return CountriesResponse(countries=items, total=len(items))


@router.get("/hotels", response=HotelListResponse, auth=api_key_auth)
async def list_hotels(
    request,
    country_code: str = Query(..., min_length=2, max_length=2, description="ISO-2 from GET /countries"),
    city_name: str | None = Query(None, description="Optional city filter (recommended for large countries)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Step 2 — List hotels in a country.

    Pick `hotel_id` values, then call POST /hotel-min-rates or POST /hotel-rates.
    """
    country_code = country_code.upper()

    try:
        hotels = await catalog_service.list_hotels(
            country_code=country_code,
            city_name=city_name,
            offset=offset,
            limit=limit,
        )
    except Exception as exc:
        _supplier_error(exc, "Unable to load hotels from supplier")

    items = [
        HotelSummary(
            hotel_id=h["hotel_id"],
            name=h["name"],
            city=h["city"],
            country_code=h["country_code"],
            address=h["address"],
            rating=h["rating"],
            main_photo=h["main_photo"],
        )
        for h in hotels
    ]

    return HotelListResponse(
        country_code=country_code,
        city_name=city_name,
        hotels=items,
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post("/hotel-min-rates", response=HotelMinRatesResponse, auth=api_key_auth)
async def search_hotel_min_rates(request, payload: HotelMinRatesRequest):
    """
    Cheapest rate per hotel — for listing pages after GET /hotels.

    Returns `hotel_id`, `price`, and `offer_id` only. Use POST /hotel-rates for full room detail.
    """
    agent, _ = request.auth
    logger.info(
        f"Agent {agent.company_name} min-rates for {len(payload.hotel_ids)} hotels"
    )

    rates = await search_service.get_hotel_min_rates(
        hotel_ids=payload.hotel_ids,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        currency=payload.currency,
        guest_nationality=payload.guest_nationality.upper(),
    )

    rates = apply_agent_commission_to_min_rates(rates, payload.commission)

    return map_hotel_min_rates_for_agent(
        rates,
        check_in=payload.check_in.isoformat(),
        check_out=payload.check_out.isoformat(),
        currency=payload.currency,
    )


@router.post("/hotel-rates", response=SearchResponseEssential, auth=api_key_auth)
async def search_hotel_rates(request, payload: HotelRatesRequest):
    """
    Step 3 — Get bookable rates for a hotel.

    Use `hotel_id` from GET /hotels.
    """
    agent, api_key_obj = request.auth
    logger.info(f"Agent {agent.company_name} searching hotel {payload.hotel_id}")

    nights = (payload.check_out - payload.check_in).days
    guest_nationality = payload.guest_nationality.upper()

    results = await search_service.search_all_suppliers(
        hotel_id=payload.hotel_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        currency=payload.currency,
        guest_nationality=guest_nationality,
    )

    if not results:
        return SearchResponseEssential(
            hotel=HotelEssential(
                hotel_id=payload.hotel_id,
                name="",
                address="",
                rating=0.0,
                main_photo="",
            ),
            check_in=payload.check_in.isoformat(),
            check_out=payload.check_out.isoformat(),
            nights=nights,
            rooms=[],
            total_suppliers=0,
        )

    result = apply_agent_commission(results[0], payload.commission)
    return map_hotel_rates_for_agent(result, total_suppliers=len(results))
