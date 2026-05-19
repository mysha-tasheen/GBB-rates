import logging

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from ninja import Query, Router
from ninja.errors import HttpError
from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import (
    booking_service,
    logger,
    resolve_supplier_booking_id,
)
from apps.api.v1.schemas.booking_schemas import CancelBookingResponse

router = Router(tags=["bookings"])


@router.put(
    "/bookings/{reference}/cancel",
    response=CancelBookingResponse,
    auth=api_key_auth,
)
async def cancel_booking(
    request,
    reference: str,
    timeout: float = Query(4, ge=1, le=30),
):

    agent, _ = request.auth
    agent_id = str(agent.id)

    try:
        supplier_booking_id, local = await resolve_supplier_booking_id(
            agent_id, reference
        )
    except HttpError:
        raise

    if local and local.is_cancelled:
        raise HttpError(400, "Booking is already cancelled")

    try:
        result = await booking_service.cancel(
            supplier_booking_id=supplier_booking_id,
            local=local,
            timeout=timeout,
        )
        if local:
            await sync_to_async(booking_service.mark_cancelled, thread_sensitive=True)(
                local.id
            )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HttpError(404, "Booking not found") from exc
        logger.exception("Cancel booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to cancel booking"
        raise HttpError(502, detail) from exc
    except Exception as exc:
        logger.exception("Cancel booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to cancel booking"
        raise HttpError(502, detail) from exc

    return CancelBookingResponse(**result)
