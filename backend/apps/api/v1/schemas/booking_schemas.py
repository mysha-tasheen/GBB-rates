from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class PrebookRequest(BaseModel):
    offer_id: str = Field(..., description="From hotel-rates or hotel-min-rates response")
    use_payment_sdk: bool = Field(
        False,
        description="Set true only if using LiteAPI payment SDK on the client",
    )
    commission: float = Field(
        0,
        ge=0,
        description="Agent commission flat amount (same as used in rates search)",
    )
    voucher_code: Optional[str] = Field(None, description="Optional supplier voucher code")


class PrebookRoomRate(BaseModel):
    rate_id: str
    room_name: str
    board_name: str
    refundable: bool
    cancellation_deadline: Optional[str] = None
    price: float = Field(..., description="Room total (markup included)")
    currency: str


class CreditLineInfo(BaseModel):
    remaining_credit: float
    currency: str


class PrebookResponse(BaseModel):
    booking_id: Optional[str] = Field(
        None,
        description="GBB booking UUID when this prebook was created via POST /bookings/prebook",
    )
    prebook_id: str = Field(..., description="Supplier prebook ID — required for confirm step")
    hotel_id: str
    check_in: str
    check_out: str
    currency: str
    price: float = Field(..., description="Total price for the agent (markup included)")
    terms_and_conditions: str = ""
    room: PrebookRoomRate
    transaction_id: Optional[str] = Field(
        None,
        description="Only when use_payment_sdk=true",
    )
    secret_key: Optional[str] = Field(
        None,
        description="Only when use_payment_sdk=true (payment SDK)",
    )
    credit_line: Optional[CreditLineInfo] = Field(
        None,
        description="Present on GET when include_credit_balance=true",
    )


class HolderInput(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str = Field("", description="Payer phone (required by supplier if empty use placeholder)")


class GuestInput(BaseModel):
    occupancy_number: int = Field(1, ge=1, description="Room number (1 per room)")
    first_name: str
    last_name: str
    email: str
    phone: str = ""


PaymentMethod = Literal["ACC_CREDIT_CARD", "TRANSACTION", "WALLET", "CREDIT"]


class ConfirmBookingRequest(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID from POST /bookings/prebook"
    )
    prebook_id: Optional[str] = Field(None, description="Supplier prebook ID (alternative to booking_id)")
    holder: HolderInput
    guests: List[GuestInput] = Field(..., min_length=1)
    payment_method: PaymentMethod = Field(
        "ACC_CREDIT_CARD",
        description="ACC_CREDIT_CARD for sandbox; TRANSACTION if using payment SDK",
    )
    client_reference: Optional[str] = Field(
        None, description="Optional idempotency key (defaults to booking_id)",
    )

    @model_validator(mode="after")
    def require_booking_reference(self):
        if not self.booking_id and not self.prebook_id:
            raise ValueError("Either booking_id or prebook_id is required")
        return self


class ConfirmBookingResponse(BaseModel):
    booking_id: str = Field(..., description="GBB booking reference (UUID)")
    supplier_booking_id: str
    status: str
    hotel_id: str
    hotel_name: str = ""
    check_in: str
    check_out: str
    currency: str
    price: float = Field(..., description="Total charged to agent")
    hotel_confirmation_code: str = ""
    room_name: str = ""
    board_name: str = ""
    guest_name: str = ""


class BookingListItem(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID when matched to a local record"
    )
    supplier_booking_id: str
    client_reference: str = ""
    prebook_id: str = ""
    status: str
    payment_status: str = ""
    hotel_id: str
    hotel_name: str = ""
    check_in: str
    check_out: str
    currency: str
    price: float = Field(..., description="Total price for the agent (markup included)")
    hotel_confirmation_code: str = ""
    holder_name: str = ""
    holder_email: str = ""
    guest_name: str = ""
    created_at: Optional[str] = None


class BookingListResponse(BaseModel):
    bookings: List[BookingListItem]
    total: int


class OccupancyInput(BaseModel):
    adults: int = Field(..., ge=1, description="Adults in this room")
    children: List[int] = Field(
        default_factory=list,
        description="Ages of children (empty if none)",
    )


class AlternativePrebooksRequest(BaseModel):
    occupancies: List[OccupancyInput] = Field(
        ..., min_length=1, description="One entry per room"
    )
    check_in: date = Field(..., description="New check-in date")
    check_out: date = Field(..., description="New check-out date")
    commission: float = Field(
        0,
        ge=0,
        description="Agent commission flat amount applied to each alternative price",
    )
    refundable_rates_only: bool = Field(
        False,
        description="When true, only fully refundable alternatives are returned",
    )
    board_type: Optional[str] = Field(
        None,
        description="Filter by board type (e.g. RO, BB); omit for all",
    )

    @model_validator(mode="after")
    def check_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class AlternativePrebookOption(BaseModel):
    prebook_id: str = Field(..., description="Use with POST /bookings/rebook")
    offer_id: str
    hotel_id: str
    check_in: str
    check_out: str
    currency: str
    price: float = Field(..., description="Total price for the agent (markup included)")
    price_difference_percent: float = Field(
        0, description="Percent difference vs original booking price"
    )
    cancellation_changed: bool = False
    board_changed: bool = False
    room_name: str = ""
    board_name: str = ""
    refundable: bool = False
    cancellation_deadline: Optional[str] = None


class AlternativePrebooksResponse(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID of the original booking"
    )
    supplier_booking_id: str = Field(
        ..., description="Original supplier booking ID (existingBookingId for rebook)"
    )
    alternatives: List[AlternativePrebookOption]
    total: int


class AmendGuestRequest(BaseModel):
    holder: HolderInput
    remarks: Optional[str] = Field(None, description="Optional notes for the amendment")


class AmendGuestResponse(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID when matched to a local record"
    )
    supplier_booking_id: str
    amendment_id: Optional[int] = Field(None, description="Supplier amendment request ID")
    status: str = Field(..., description="Amendment status (e.g. PENDING)")
    holder_first_name: str
    holder_last_name: str
    holder_email: str
    remarks: str = ""


class CancelBookingResponse(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID when matched to a local record"
    )
    supplier_booking_id: str
    status: str = Field(
        ...,
        description="CANCELLED (refunded) or CANCELLED_WITH_CHARGES",
    )
    cancellation_fee: float = Field(0, description="Fee charged on cancellation")
    refund_amount: float = Field(0, description="Amount refunded to the agent")
    currency: str


class BookingDetailResponse(BaseModel):
    booking_id: Optional[str] = Field(
        None, description="GBB booking UUID when matched to a local record"
    )
    supplier_booking_id: str
    client_reference: str = ""
    prebook_id: str = ""
    status: str
    payment_status: str = ""
    hotel_id: str
    hotel_name: str = ""
    check_in: str
    check_out: str
    currency: str
    price: float = Field(..., description="Total price for the agent (markup included)")
    hotel_confirmation_code: str = ""
    holder_name: str = ""
    holder_email: str = ""
    holder_phone: str = ""
    guest_name: str = ""
    room_name: str = ""
    board_name: str = ""
    refundable: bool = False
    cancellation_deadline: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
