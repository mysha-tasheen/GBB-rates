from ninja import Query, Router

from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.search_common import (
    catalog_service,
    commission_service,
    logger,
    search_service,
    supplier_error,
)
from apps.api.v1.endpoints.search_minimum import router as search_minimum_router
from apps.api.v1.mappers import map_hotel_rates_for_agent
from apps.api.v1.schemas.search_schemas import (
    CountriesResponse,
    Country,
    CurrenciesResponse,
    Currency,
    HotelEssential,
    HotelListResponse,
    HotelRatesRequest,
    HotelSummary,
    SearchResponseEssential,
)

router = Router(tags=["search"])
router.add_router("", search_minimum_router)


@router.get("/countries", response=CountriesResponse, auth=api_key_auth)
async def list_countries(request):
    
    try:
        countries = await catalog_service.list_countries()
    except Exception as exc:
        supplier_error(exc, "Unable to load countries")

    items = [Country(code=c["code"], name=c["name"]) for c in countries]
    return CountriesResponse(countries=items, total=len(items))


@router.get("/currencies", response=CurrenciesResponse, auth=api_key_auth)
async def list_currencies(request):
    """Wholesaler reference: ISO codes and names for currency selection (e.g. FJD for Fiji)."""
    try:
        currencies = await catalog_service.list_currencies()
    except Exception as exc:
        supplier_error(exc, "Unable to load currencies")

    items = [
        Currency(code=c["code"], name=c["name"], countries=c.get("countries", []))
        for c in currencies
    ]
    return CurrenciesResponse(currencies=items, total=len(items))


@router.get("/hotels", response=HotelListResponse, auth=api_key_auth)
async def list_hotels(
    request,
    country_code: str = Query(..., min_length=2, max_length=2, description="ISO-2 from GET /countries"),
    city_name: str | None = Query(None, description="Optional city filter (recommended for large countries)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    
    country_code = country_code.upper()

    try:
        hotels = await catalog_service.list_hotels(
            country_code=country_code,
            city_name=city_name,
            offset=offset,
            limit=limit,
        )
    except Exception as exc:
        supplier_error(exc, "Unable to load hotels")

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


@router.post("/hotel-rates", response=SearchResponseEssential, auth=api_key_auth)
async def search_hotel_rates(request, payload: HotelRatesRequest):
    
    agent, _ = request.auth
    logger.info("Agent %s searching hotel %s", agent.company_name, payload.hotel_id)

    nights = (payload.check_out - payload.check_in).days
    guest_nationality = payload.guest_nationality.upper()

    try:
        suppliers = search_service._get()._suppliers
    except Exception as exc:
        supplier_error(exc, "Search is not configured")

    if not suppliers:
        supplier_error(
            ValueError("Rates provider not configured"),
            "Search is not configured — check NUITEE_API_KEY",
        )

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
            total_offers=0,
        )

    result = commission_service.apply_flat_to_hotel_rates(results[0], payload.commission)
    return map_hotel_rates_for_agent(result, total_offers=len(results))
