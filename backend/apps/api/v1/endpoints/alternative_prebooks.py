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
from apps.api.v1.schemas.booking_schemas import (
    AlternativePrebookOption,
    AlternativePrebooksRequest,
    AlternativePrebooksResponse,
)

router = Router(tags=["bookings"])


@router.post(
    "/bookings/{reference}/alternative-prebooks",
    response=AlternativePrebooksResponse,
    auth=api_key_auth,
)
async def create_alternative_prebooks(
    request, reference: str, payload: AlternativePrebooksRequest
):
    """Search alternative rates for amending check-in, check-out, or occupancy."""
    agent, _ = request.auth
    agent_id = str(agent.id)

    try:
        supplier_booking_id, local = resolve_supplier_booking_id(agent_id, reference)
    except HttpError:
        raise

    try:
        options = await booking_service.alternative_prebooks(
            supplier_booking_id=supplier_booking_id,
            occupancies=[o.model_dump() for o in payload.occupancies],
            check_in=payload.check_in.isoformat(),
            check_out=payload.check_out.isoformat(),
            agent_commission=payload.commission,
            refundable_rates_only=payload.refundable_rates_only,
            board_type=payload.board_type,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HttpError(404, "Booking not found") from exc
        logger.exception(
            "Alternative prebooks failed for agent %s", agent.company_name
        )
        detail = (
            str(exc) if settings.DEBUG else "Unable to fetch alternatives from supplier"
        )
        raise HttpError(502, detail) from exc
    except Exception as exc:
        logger.exception(
            "Alternative prebooks failed for agent %s", agent.company_name
        )
        detail = (
            str(exc) if settings.DEBUG else "Unable to fetch alternatives from supplier"
        )
        raise HttpError(502, detail) from exc

    return AlternativePrebooksResponse(
        booking_id=local.id if local else None,
        supplier_booking_id=supplier_booking_id,
        alternatives=[AlternativePrebookOption(**opt) for opt in options],
        total=len(options),
    )
