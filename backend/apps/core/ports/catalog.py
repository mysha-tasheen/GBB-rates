from datetime import date
from typing import Any, Protocol


class CatalogSupplierPort(Protocol):
    
    async def get_countries(self) -> list[dict[str, str]]: ...

    async def get_currencies(self) -> list[dict[str, Any]]: ...

    async def get_hotels(
        self,
        country_code: str,
        city_name: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...
