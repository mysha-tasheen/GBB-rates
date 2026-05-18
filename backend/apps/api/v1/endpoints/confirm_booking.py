import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from ninja import Router
from ninja.errors import HttpError
from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import booking_service, logger
from apps.api.v1.schemas.booking_schemas import ConfirmBookingRequest, ConfirmBookingResponse
from apps.core.exceptions import BookingNotFound

router = Router(tags=["bookings"])


@router.post("/bookings/confirm", response=ConfirmBookingResponse, auth=api_key_auth)
async def confirm_booking(request, payload: ConfirmBookingRequest):
    
    agent, _ = request.auth

    holder = payload.holder.model_dump()
    guests = [g.model_dump() for g in payload.guests]

    try:
        record = await sync_to_async(
            booking_service.get_local_for_agent, thread_sensitive=True
        )(
            agent_id=str(agent.id),
            booking_id=payload.booking_id,
            prebook_id=payload.prebook_id,
        )
    except BookingNotFound:
        raise HttpError(404, "Booking not found") from None

    try:
        result = await booking_service.confirm(
            booking=record,
            holder=holder,
            guests=guests,
            payment_method=payload.payment_method,
            client_reference=payload.client_reference,
        )
        await sync_to_async(booking_service.mark_confirmed, thread_sensitive=True)(
            record.id, result["supplier_booking_id"]
        )
    except ValueError as exc:
        if "Supplier did not confirm" in str(exc):
            await sync_to_async(booking_service.mark_failed, thread_sensitive=True)(
                record.id
            )
        raise HttpError(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("Confirm booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to confirm booking with supplier"
        raise HttpError(502, detail) from exc

    return ConfirmBookingResponse(**result)
