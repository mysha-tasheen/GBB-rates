from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional


class BaseAdapter(ABC):
    def __init__(self, credentials: Dict[str, Any], commission_percent: float):
        self.credentials = credentials
        self.commission_percent = commission_percent

    @abstractmethod
    async def get_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]:
        pass

    async def get_minimum_rate(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> Optional[Dict[str, Any]]:
        return None
