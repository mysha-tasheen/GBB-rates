from datetime import date
from typing import Any, Protocol


class SearchSupplierPort(Protocol):
    

    async def get_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> list[dict[str, Any]]: ...

    async def get_min_rates(
        self,
        hotel_ids: list[str],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> list[dict[str, Any]]: ...
