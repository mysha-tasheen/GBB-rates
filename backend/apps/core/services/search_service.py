import logging
from datetime import date
from typing import Any, Dict, List

from apps.core.async_bridge import run_sync
from apps.core.ports.search import SearchSupplierPort

logger = logging.getLogger(__name__)


class SearchService:
    

    def __init__(self, suppliers: Dict[str, SearchSupplierPort]):
        self._suppliers = suppliers

    async def search_all_suppliers(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]:
        if not self._suppliers:
            logger.error("No active suppliers — cannot fetch hotel rates")
            return []

        all_results: List[Dict[str, Any]] = []

        for supplier_name, supplier in self._suppliers.items():
            try:
                results = await run_sync(
                    supplier.get_hotel_rates,
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
        if not self._suppliers:
            logger.error("No active suppliers — cannot fetch min rates")
            return []

        all_rates: List[Dict[str, Any]] = []

        for supplier_name, supplier in self._suppliers.items():
            get_min_rates = getattr(supplier, "get_min_rates", None)
            if not get_min_rates:
                continue
            try:
                rates = await run_sync(
                    get_min_rates,
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
