from dataclasses import dataclass


@dataclass(frozen=True)
class SupplierConfig:
    

    name: str
    commission_percent: float
    api_key: str
    api_url: str
    book_api_url: str = ""
