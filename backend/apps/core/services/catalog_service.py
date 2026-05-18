import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class CatalogAdapter(Protocol):
    async def get_countries(self) -> list[dict[str, str]]: ...

    async def get_hotels(
        self,
        country_code: str,
        city_name: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...


class CatalogService:
    """Pure Python catalog operations (countries, hotels)."""

    def __init__(self, adapter: CatalogAdapter):
        self._adapter = adapter

    async def list_countries(self) -> list[dict[str, str]]:
        return await self._adapter.get_countries()

    async def list_hotels(
        self,
        country_code: str,
        city_name: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return await self._adapter.get_hotels(
            country_code=country_code,
            city_name=city_name,
            offset=offset,
            limit=limit,
        )
