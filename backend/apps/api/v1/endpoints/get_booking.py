import logging

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from ninja import Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import (
    booking_service,
    logger,
    resolve_supplier_booking_id,
)
from apps.api.v1.schemas.booking_schemas import BookingDetailResponse

router = Router(tags=["bookings"])


@router.get("/bookings/{reference}", response=BookingDetailResponse, auth=api_key_auth)
async def get_booking(request, reference: str):

    agent, _ = request.auth
    agent_id = str(agent.id)

    try:
        supplier_booking_id, local = await resolve_supplier_booking_id(
            agent_id, reference
        )
    except HttpError:
        raise

    try:
        raw = await booking_service.get_booking(supplier_booking_id)
    except ValueError as exc:
        raise HttpError(404, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HttpError(404, "Booking not found") from exc
        logger.exception("Get booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to retrieve booking from supplier"
        raise HttpError(502, detail) from exc
    except Exception as exc:
        logger.exception("Get booking failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to retrieve booking from supplier"
        raise HttpError(502, detail) from exc

    if not local:
        local = await sync_to_async(
            booking_service.find_local_for_supplier_item, thread_sensitive=True
        )(agent_id, raw)

    return BookingDetailResponse(**booking_service.parse_booking_detail(raw, local=local))
