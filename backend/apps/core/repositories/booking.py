from dataclasses import dataclass
from decimal import Decimal

from apps.core.models import Booking


@dataclass(frozen=True)
class BookingRecord:
    id: str
    prebook_id: str
    transaction_id: str
    supplier_booking_id: str
    hotel_id: str
    agent_price: float
    agent_commission: float
    currency: str
    status: str


class BookingRepository:
    """Django ORM access for booking persistence."""

    def create_prebook(
        self,
        agent_id: str,
        agent_view: dict,
        internal: dict,
    ) -> BookingRecord:
        booking = Booking.objects.create(
            agent_id=agent_id,
            supplier_name="liteapi",
            prebook_id=internal["prebook_id"],
            transaction_id=internal["transaction_id"],
            hotel_id=agent_view["hotel_id"],
            rate_id=internal["rate_id"],
            offer_id=internal["offer_id"],
            supplier_price=Decimal(str(internal["supplier_price"])),
            commission_percent=Decimal(str(internal["commission_percent"])),
            commission_amount=Decimal(str(internal["commission_amount"])),
            middleware_price=Decimal(str(internal["middleware_price"])),
            agent_commission=Decimal(str(internal["agent_commission"])),
            agent_price=Decimal(str(internal["agent_price"])),
            currency=internal["currency"],
            status=Booking.Status.PREBOOKED,
        )
        return self._to_record(booking)

    def get_for_agent(
        self,
        agent_id: str,
        booking_id: str | None = None,
        prebook_id: str | None = None,
    ) -> BookingRecord:
        qs = Booking.objects.filter(agent_id=agent_id)
        if booking_id:
            booking = qs.get(id=booking_id)
        else:
            booking = qs.get(prebook_id=prebook_id)
        return self._to_record(booking)

    def find_by_prebook_for_agent(
        self, agent_id: str, prebook_id: str
    ) -> BookingRecord | None:
        booking = Booking.objects.filter(
            agent_id=agent_id, prebook_id=prebook_id
        ).first()
        if not booking:
            return None
        return self._to_record(booking)

    def find_by_reference_for_agent(
        self, agent_id: str, reference: str
    ) -> BookingRecord | None:
        """Look up by GBB booking UUID or supplier booking ID."""
        booking = Booking.objects.filter(agent_id=agent_id, id=reference).first()
        if booking:
            return self._to_record(booking)

        booking = Booking.objects.filter(
            agent_id=agent_id, supplier_booking_id=reference
        ).first()
        if booking:
            return self._to_record(booking)

        return None

    def find_for_supplier_item(
        self, agent_id: str, item: dict
    ) -> BookingRecord | None:
        """Match a LiteAPI booking list item to a local GBB booking."""
        client_ref = item.get("clientReference") or item.get("client_reference") or ""
        if client_ref:
            booking = Booking.objects.filter(agent_id=agent_id, id=client_ref).first()
            if booking:
                return self._to_record(booking)

        supplier_id = (
            item.get("bookingId")
            or item.get("booking_Id")
            or item.get("supplier_Booking_Id")
            or ""
        )
        if supplier_id:
            booking = Booking.objects.filter(
                agent_id=agent_id, supplier_booking_id=supplier_id
            ).first()
            if booking:
                return self._to_record(booking)

        prebook_id = item.get("prebookId") or item.get("prebook_Id") or ""
        if prebook_id:
            return self.find_by_prebook_for_agent(agent_id, prebook_id)

        return None

    def mark_failed(self, booking_id: str) -> None:
        Booking.objects.filter(id=booking_id).update(
            status=Booking.Status.FAILED,
        )

    def mark_confirmed(self, booking_id: str, supplier_booking_id: str) -> None:
        Booking.objects.filter(id=booking_id).update(
            supplier_booking_id=supplier_booking_id,
            status=Booking.Status.CONFIRMED,
        )

    def mark_cancelled(self, booking_id: str) -> None:
        Booking.objects.filter(id=booking_id).update(
            status=Booking.Status.CANCELLED,
        )

    @staticmethod
    def _to_record(booking: Booking) -> BookingRecord:
        return BookingRecord(
            id=str(booking.id),
            prebook_id=booking.prebook_id,
            transaction_id=booking.transaction_id or "",
            supplier_booking_id=booking.supplier_booking_id or "",
            hotel_id=booking.hotel_id,
            agent_price=float(booking.agent_price),
            agent_commission=float(booking.agent_commission),
            currency=booking.currency,
            status=booking.status,
        )
