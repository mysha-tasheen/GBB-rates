from ninja import Router
from typing import List
from datetime import date
import logging

from apps.api.v1.schemas import HotelRatesRequest, SearchResponseEssential
from apps.core.services.search_service import SearchService

router = Router()
logger = logging.getLogger(__name__)

search_service = SearchService()

@router.post("/hotel-rates", response=SearchResponseEssential)
def search_hotel_rates(request, payload: HotelRatesRequest):
    """
    POST /api/v1/hotel-rates
    Search for hotel rates from LiteAPI and other suppliers.
    """
    
    # Get agent info from auth
    agent, api_key_obj = request.auth
    logger.info(f"Agent {agent.company_name} searching hotel {payload.hotel_id}")
    
    nights = (payload.check_out - payload.check_in).days
    
    # Search across all active suppliers
    results = search_service.search_all_suppliers(
        hotel_id=payload.hotel_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        currency=payload.currency
    )
    
    if not results:
        return SearchResponseEssential(
            hotel=HotelEssential(
                hotel_id=payload.hotel_id,
                name="",
                address="",
                rating=0.0,
                main_photo=""
            ),
            check_in=payload.check_in.isoformat(),
            check_out=payload.check_out.isoformat(),
            nights=nights,
            rooms=[],
            total_suppliers=0
        )
    
    # Take first result (for now, combine multiple suppliers later)
    first_result = results[0]
    
    return SearchResponseEssential(
        hotel=HotelEssential(
            hotel_id=first_result["hotel"]["hotel_id"],
            name=first_result["hotel"]["name"],
            address=first_result["hotel"]["address"],
            rating=first_result["hotel"]["rating"],
            main_photo=first_result["hotel"]["main_photo"]
        ),
        check_in=first_result["check_in"],
        check_out=first_result["check_out"],
        nights=first_result["nights"],
        rooms=first_result["rooms"],
        total_suppliers=len(results)
    )