from dataclasses import dataclass
from enum import Enum


class BookingStatus(str, Enum):
    PREBOOKED = "prebooked"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class Booking:
    """Local GBB booking record (pure Python — no Django)."""

    id: str
    prebook_id: str
    transaction_id: str
    supplier_booking_id: str
    hotel_id: str
    agent_price: float
    agent_commission: float
    currency: str
    status: str

    @property
    def is_prebooked(self) -> bool:
        return self.status == BookingStatus.PREBOOKED.value

    @property
    def is_cancelled(self) -> bool:
        return self.status == BookingStatus.CANCELLED.value
