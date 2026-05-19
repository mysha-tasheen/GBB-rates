import uuid
from decimal import Decimal

from apps.core.domain.booking import Booking
from apps.core.domain.prebook import AgentPrebook, PrebookInternal
from apps.core.exceptions import BookingNotFound
from apps.core.models import Booking as BookingModel


def _truncate(value: str, max_len: int) -> str:
    if not value:
        return ""
    return value[:max_len]


class BookingRepository:

    def create_prebook(
        self,
        agent_id: str,
        agent: AgentPrebook,
        internal: PrebookInternal,
    ) -> Booking:
        row = BookingModel.objects.create(
            agent_id=agent_id,
            supplier_name="liteapi",
            prebook_id=internal.prebook_id,
            transaction_id=internal.transaction_id,
            hotel_id=agent.hotel_id,
            rate_id=_truncate(internal.rate_id, 500),
            offer_id=_truncate(internal.offer_id, 500),
            supplier_price=Decimal(str(internal.supplier_price)),
            commission_percent=Decimal(str(internal.commission_percent)),
            commission_amount=Decimal(str(internal.commission_amount)),
            middleware_price=Decimal(str(internal.middleware_price)),
            agent_commission=Decimal(str(internal.agent_commission)),
            agent_price=Decimal(str(internal.agent_price)),
            currency=internal.currency,
            status=BookingModel.Status.PREBOOKED,
        )
        return self._to_domain(row)

    def get_for_agent(
        self,
        agent_id: str,
        booking_id: str | None = None,
        prebook_id: str | None = None,
    ) -> Booking:
        qs = BookingModel.objects.filter(agent_id=agent_id)
        try:
            if booking_id:
                row = qs.get(id=booking_id)
            else:
                row = qs.get(prebook_id=prebook_id)
        except BookingModel.DoesNotExist as exc:
            raise BookingNotFound from exc
        return self._to_domain(row)

    def find_by_prebook_for_agent(
        self, agent_id: str, prebook_id: str
    ) -> Booking | None:
        row = BookingModel.objects.filter(
            agent_id=agent_id, prebook_id=prebook_id
        ).first()
        return self._to_domain(row) if row else None

    def find_by_reference_for_agent(
        self, agent_id: str, reference: str
    ) -> Booking | None:
        try:
            uuid.UUID(reference)
        except ValueError:
            pass
        else:
            row = BookingModel.objects.filter(agent_id=agent_id, id=reference).first()
            if row:
                return self._to_domain(row)

        row = BookingModel.objects.filter(
            agent_id=agent_id, supplier_booking_id=reference
        ).first()
        return self._to_domain(row) if row else None

    def find_for_supplier_item(
        self, agent_id: str, item: dict
    ) -> Booking | None:
        client_ref = item.get("clientReference") or item.get("client_reference") or ""
        if client_ref:
            row = BookingModel.objects.filter(agent_id=agent_id, id=client_ref).first()
            if row:
                return self._to_domain(row)

        supplier_id = (
            item.get("bookingId")
            or item.get("booking_Id")
            or item.get("supplier_Booking_Id")
            or ""
        )
        if supplier_id:
            row = BookingModel.objects.filter(
                agent_id=agent_id, supplier_booking_id=supplier_id
            ).first()
            if row:
                return self._to_domain(row)

        prebook_id = item.get("prebookId") or item.get("prebook_Id") or ""
        if prebook_id:
            return self.find_by_prebook_for_agent(agent_id, prebook_id)

        return None

    def mark_failed(self, booking_id: str) -> None:
        BookingModel.objects.filter(id=booking_id).update(
            status=BookingModel.Status.FAILED,
        )

    def mark_confirmed(self, booking_id: str, supplier_booking_id: str) -> None:
        BookingModel.objects.filter(id=booking_id).update(
            supplier_booking_id=supplier_booking_id,
            status=BookingModel.Status.CONFIRMED,
        )

    def mark_cancelled(self, booking_id: str) -> None:
        BookingModel.objects.filter(id=booking_id).update(
            status=BookingModel.Status.CANCELLED,
        )

    @staticmethod
    def _to_domain(row: BookingModel) -> Booking:
        return Booking(
            id=str(row.id),
            prebook_id=row.prebook_id,
            transaction_id=row.transaction_id or "",
            supplier_booking_id=row.supplier_booking_id or "",
            hotel_id=row.hotel_id,
            agent_price=float(row.agent_price),
            agent_commission=float(row.agent_commission),
            currency=row.currency,
            status=row.status,
        )
