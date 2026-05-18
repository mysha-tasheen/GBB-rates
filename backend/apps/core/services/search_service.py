import logging
from datetime import date
from typing import Any, Dict, List, Protocol

logger = logging.getLogger(__name__)


class SearchAdapter(Protocol):
    async def get_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]: ...

    async def get_min_rates(
        self,
        hotel_ids: List[str],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]: ...


class SearchService:
    """Pure Python multi-supplier search orchestration."""

    def __init__(self, adapters: Dict[str, SearchAdapter]):
        self._adapters = adapters

    async def search_all_suppliers(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]:
        if not self._adapters:
            logger.error("No active suppliers — cannot fetch hotel rates")
            return []

        all_results: List[Dict[str, Any]] = []

        for supplier_name, adapter in self._adapters.items():
            try:
                results = await adapter.get_hotel_rates(
                    hotel_id=hotel_id,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                    guest_nationality=guest_nationality,
                )
                all_results.extend(results)
                logger.info("Found %s results from %s", len(results), supplier_name)
            except Exception as e:
                logger.error("Failed to search %s: %s", supplier_name, e)

        return all_results

    async def get_hotel_min_rates(
        self,
        hotel_ids: List[str],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]:
        if not self._adapters:
            logger.error("No active suppliers — cannot fetch min rates")
            return []

        all_rates: List[Dict[str, Any]] = []

        for supplier_name, adapter in self._adapters.items():
            get_min_rates = getattr(adapter, "get_min_rates", None)
            if not get_min_rates:
                continue
            try:
                rates = await get_min_rates(
                    hotel_ids=hotel_ids,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                    guest_nationality=guest_nationality,
                )
                all_rates.extend(rates)
                logger.info("Found %s min rates from %s", len(rates), supplier_name)
            except Exception as e:
                logger.error("Failed min rates from %s: %s", supplier_name, e)

        return all_rates
