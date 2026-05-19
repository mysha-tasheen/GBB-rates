import logging
from asgiref.sync import sync_to_async
from ninja.errors import HttpError
from apps.api.lazy import LazyService
from apps.core.wiring import build_booking_service

logger = logging.getLogger(__name__)

booking_service = LazyService(build_booking_service)


async def resolve_supplier_booking_id(agent_id: str, reference: str):
    
    try:
        return await sync_to_async(
            booking_service.resolve_supplier_reference,
            thread_sensitive=True,
        )(agent_id, reference)
    except ValueError as exc:
        raise HttpError(404, str(exc)) from exc
