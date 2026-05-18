import logging
from datetime import date

from django.conf import settings
from ninja import Query, Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth
from apps.api.v1.endpoints.bookings_common import booking_repo, booking_service, logger
from apps.api.v1.schemas.booking_schemas import BookingListItem, BookingListResponse

router = Router(tags=["bookings"])


@router.get("/bookings", response=BookingListResponse, auth=api_key_auth)
async def list_bookings(
    request,
    guest_id: str | None = Query(None),
    client_reference: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    booking_start_date: date | None = Query(None),
    booking_end_date: date | None = Query(None),
    status: str | None = Query(None),
    payment_status: str | None = Query(None),
    timeout: float = Query(4, ge=1, le=30),
):
    """
    List bookings — search by `guest_id` / `client_reference`, or omit both for all bookings.
    """
    agent, _ = request.auth
    agent_id = str(agent.id)

    try:
        if guest_id or client_reference:
            raw_items = await booking_service.list_bookings(
                guest_id=guest_id,
                client_reference=client_reference,
                timeout=timeout,
            )
            count = len(raw_items)
            parse = booking_service.parse_list_item
        else:
            count, raw_items = await booking_service.list_all_bookings(
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
                booking_start_date=(
                    booking_start_date.isoformat() if booking_start_date else None
                ),
                booking_end_date=(
                    booking_end_date.isoformat() if booking_end_date else None
                ),
                status=status,
                payment_status=payment_status,
                timeout=timeout,
            )
            parse = booking_service.parse_inventory_item
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("List bookings failed for agent %s", agent.company_name)
        detail = str(exc) if settings.DEBUG else "Unable to list bookings from supplier"
        raise HttpError(502, detail) from exc

    items = []
    for raw in raw_items:
        local = booking_repo.find_for_supplier_item(agent_id, raw)
        items.append(BookingListItem(**parse(raw, local=local)))

    return BookingListResponse(bookings=items, total=count)
