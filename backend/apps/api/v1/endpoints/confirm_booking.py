import logging

from django.conf import settings
from ninja import Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import booking_repo, booking_service, logger
from apps.api.v1.schemas.booking_schemas import ConfirmBookingRequest, ConfirmBookingResponse
from apps.core.models import Booking

router = Router(tags=["bookings"])


@router.post("/bookings/confirm", response=ConfirmBookingResponse, auth=api_key_auth)
async def confirm_booking(request, payload: ConfirmBookingRequest):
    """Step 2 — Confirm booking after prebook."""
    agent, _ = request.auth

    holder = payload.holder.model_dump()
    guests = [g.model_dump() for g in payload.guests]

    try:
        record = booking_repo.get_for_agent(
            agent_id=str(agent.id),
            booking_id=payload.booking_id,
            prebook_id=payload.prebook_id,
        )
    except Booking.DoesNotExist:
        raise HttpError(404, "Booking not found") from None

    try:
        result = await booking_service.confirm(
            booking=record,
            holder=holder,
            guests=guests,
            payment_method=payload.payment_method,
            client_reference=payload.client_reference,
        )
        booking_repo.mark_confirmed(record.id, result["supplier_booking_id"])
    except ValueError as exc:
        if "Supplier did not confirm" in str(exc):
            booking_repo.mark_failed(record.id)
        raise HttpError(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("Confirm booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to confirm booking with supplier"
        raise HttpError(502, detail) from exc

    return ConfirmBookingResponse(**result)
