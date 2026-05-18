"""Supplier and platform config from environment (no Django)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NuiteeConfig:
    api_key: str
    api_url: str
    book_api_url: str
    default_commission_percent: float


def get_nuitee_config() -> NuiteeConfig:
    return NuiteeConfig(
        api_key=os.environ.get("NUITEE_API_KEY", ""),
        api_url=os.environ.get("NUITEE_API_URL", "https://api.liteapi.travel/v3.0"),
        book_api_url=os.environ.get(
            "NUITEE_BOOK_API_URL", "https://book.liteapi.travel/v3.0"
        ),
        default_commission_percent=float(
            os.environ.get("NUITEE_COMMISSION_PERCENT", "10")
        ),
    )
