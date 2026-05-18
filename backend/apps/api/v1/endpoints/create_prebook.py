import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from ninja import Query, Router
from ninja.errors import HttpError
from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import booking_service, logger
from apps.api.v1.schemas.booking_schemas import (
    CreditLineInfo,
    PrebookRequest,
    PrebookResponse,
    PrebookRoomRate,
)

router = Router(tags=["bookings"])


def _to_prebook_response(agent_view: dict, booking_id: str | None = None) -> PrebookResponse:
    credit = agent_view.get("credit_line")
    return PrebookResponse(
        booking_id=booking_id,
        prebook_id=agent_view["prebook_id"],
        hotel_id=agent_view["hotel_id"],
        check_in=agent_view["check_in"],
        check_out=agent_view["check_out"],
        currency=agent_view["currency"],
        price=agent_view["price"],
        terms_and_conditions=agent_view["terms_and_conditions"],
        room=PrebookRoomRate(**agent_view["room"]),
        transaction_id=agent_view.get("transaction_id"),
        secret_key=agent_view.get("secret_key"),
        credit_line=CreditLineInfo(**credit) if credit else None,
    )


@router.post("/bookings/prebook", response=PrebookResponse, auth=api_key_auth)
async def create_prebook(request, payload: PrebookRequest):
    
    agent, _ = request.auth

    try:
        agent_prebook, internal = await booking_service.prebook(
            offer_id=payload.offer_id,
            use_payment_sdk=payload.use_payment_sdk,
            agent_commission=payload.commission,
            voucher_code=payload.voucher_code,
        )
        record = await sync_to_async(booking_service.save_prebook, thread_sensitive=True)(
            agent_id=str(agent.id),
            agent=agent_prebook,
            internal=internal,
        )
        agent_view = agent_prebook.to_agent_dict()
    except ValueError as exc:
        raise HttpError(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("Prebook failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to create prebook with supplier"
        raise HttpError(502, detail) from exc

    return _to_prebook_response(agent_view, booking_id=record.id)


@router.get("/bookings/prebook/{prebook_id}", response=PrebookResponse, auth=api_key_auth)
async def get_prebook(
    request,
    prebook_id: str,
    commission: float = Query(0, ge=0),
    include_credit_balance: bool = Query(False),
):
    
    agent, _ = request.auth

    local = await sync_to_async(
        booking_service.find_local_by_prebook, thread_sensitive=True
    )(str(agent.id), prebook_id)
    agent_commission = local.agent_commission if local else commission

    try:
        agent_prebook = await booking_service.get_prebook(
            prebook_id=prebook_id,
            agent_commission=agent_commission,
            include_credit_balance=include_credit_balance,
        )
        agent_view = agent_prebook.to_agent_dict()
    except ValueError as exc:
        raise HttpError(404, str(exc)) from exc
    except Exception as exc:
        logger.exception("Get prebook failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to retrieve prebook from supplier"
        raise HttpError(502, detail) from exc

    return _to_prebook_response(agent_view, booking_id=local.id if local else None)
