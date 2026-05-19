from typing import Any
from apps.core.async_bridge import run_sync
from apps.core.ports.catalog import CatalogSupplierPort

class CatalogService:

    def __init__(self, supplier: CatalogSupplierPort):
        self._supplier = supplier

    async def list_countries(self) -> list[dict[str, str]]:
        return await run_sync(self._supplier.get_countries)

    async def list_currencies(self) -> list[dict[str, Any]]:
        return await run_sync(self._supplier.get_currencies)

    async def list_hotels(
        self,
        country_code: str,
        city_name: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return await run_sync(
            self._supplier.get_hotels,
            country_code=country_code,
            city_name=city_name,
            offset=offset,
            limit=limit,
        )
