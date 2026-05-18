import logging

import httpx
from django.conf import settings
from ninja import Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import (
    booking_service,
    logger,
    resolve_supplier_booking_id,
)
from apps.api.v1.schemas.booking_schemas import AmendGuestRequest, AmendGuestResponse

router = Router(tags=["bookings"])


@router.put("/bookings/{reference}/amend", response=AmendGuestResponse, auth=api_key_auth)
async def amend_guest_name(request, reference: str, payload: AmendGuestRequest):
    """Amend the booking holder's first name, last name, and email."""
    agent, _ = request.auth
    agent_id = str(agent.id)

    try:
        supplier_booking_id, local = resolve_supplier_booking_id(agent_id, reference)
    except HttpError:
        raise

    try:
        result = await booking_service.amend_holder(
            supplier_booking_id=supplier_booking_id,
            holder=payload.holder.model_dump(),
            remarks=payload.remarks,
            local=local,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HttpError(404, "Booking not found") from exc
        logger.exception("Amend guest failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to amend booking with supplier"
        raise HttpError(502, detail) from exc
    except Exception as exc:
        logger.exception("Amend guest failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to amend booking with supplier"
        raise HttpError(502, detail) from exc

    return AmendGuestResponse(**result)
