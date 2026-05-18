from ninja.errors import HttpError
from apps.core.repositories.booking import BookingRepository
from apps.core.wiring import build_booking_service
import logging


logger = logging.getLogger(__name__)

booking_service = build_booking_service()
booking_repo = BookingRepository()


def resolve_supplier_booking_id(agent_id: str, reference: str):
    
    local = booking_repo.find_by_reference_for_agent(agent_id, reference)
    if local and local.supplier_booking_id:
        return local.supplier_booking_id, local
    if local:
        raise HttpError(404, "Booking is not yet confirmed with the supplier")
    return reference, None
