from typing import Any, Protocol


class BookingSupplierPort(Protocol):
    

    async def create_prebook(
        self,
        offer_id: str,
        use_payment_sdk: bool = False,
    ) -> dict[str, Any]: ...

    async def get_prebook(
        self,
        prebook_id: str,
        include_credit_balance: bool = False,
    ) -> dict[str, Any]: ...

    async def confirm_booking(
        self,
        prebook_id: str,
        holder: dict[str, Any],
        guests: list[dict[str, Any]],
        payment_method: str = "ACC_CREDIT_CARD",
        transaction_id: str | None = None,
        client_reference: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_booking(self, booking_id: str) -> dict[str, Any]: ...

    async def list_bookings(
        self,
        guest_id: str | None = None,
        client_reference: str | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def list_all_bookings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        booking_start_date: str | None = None,
        booking_end_date: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        timeout: float | None = None,
    ) -> tuple[int, list[dict[str, Any]]]: ...

    async def cancel_booking(
        self,
        booking_id: str,
        timeout: float | None = None,
    ) -> dict[str, Any]: ...

    async def amend_guest_name(
        self,
        booking_id: str,
        holder: dict[str, Any],
        remarks: str | None = None,
    ) -> dict[str, Any]: ...

    async def create_alternative_prebooks(
        self,
        booking_id: str,
        occupancies: list[dict[str, Any]],
        checkin: str,
        checkout: str,
        refundable_rates_only: bool = False,
        board_type: str | None = None,
    ) -> list[dict[str, Any]]: ...
