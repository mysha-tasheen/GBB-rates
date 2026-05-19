import json
import logging
from pathlib import Path
from typing import Dict
from apps.core.adapters import registry
from apps.core.adapters.base import BaseAdapter
from apps.core.adapters.liteapi import LiteAPIAdapter
from apps.core.config import get_nuitee_config
from apps.core.repositories.booking import BookingRepository
from apps.core.repositories.supplier import SupplierRepository
from apps.core.services.booking_service import BookingService
from apps.core.services.catalog_service import CatalogService
from apps.core.services.commission_service import CommissionService
from apps.core.services.search_service import SearchService

logger = logging.getLogger(__name__)

_supplier_repo = SupplierRepository()
_commission_service = CommissionService(_supplier_repo)

def build_commission_service() -> CommissionService:
    return _commission_service

def _config_path() -> Path:
    
    return Path(__file__).resolve().parent.parent.parent / "data" / "suppliers.json"

def _load_adapters_from_json() -> Dict[str, BaseAdapter]:
    
    path = _config_path()
    if not path.exists():
        return {}

    adapters: Dict[str, BaseAdapter] = {}
    with open(path) as f:
        config = json.load(f)

    for supplier_config in config.get("suppliers", []):
        if not supplier_config.get("is_active", True):
            continue

        name = supplier_config["name"]
        commission = _commission_service.platform_percent(name)
        credentials = supplier_config["credentials"]

        try:
            adapters[name] = registry.get_adapter(name, credentials, commission)
            logger.info("Loaded adapter for %s with %s%% commission", name, commission)
        except Exception as e:
            logger.error("Failed to load %s: %s", name, e)

    return adapters

def _load_adapters_from_env() -> Dict[str, BaseAdapter]:
    
    cfg = get_nuitee_config()
    if not cfg.api_key:
        logger.error(
            "No suppliers loaded: set NUITEE_API_KEY or add data/suppliers.json"
        )
        return {}

    try:
        commission = _commission_service.platform_percent("liteapi")
        adapter = registry.get_adapter(
            "liteapi",
            {"api_key": cfg.api_key, "base_url": cfg.api_url},
            commission,
        )
        logger.info("Loaded liteapi from env with %s%% commission", commission)
        return {"liteapi": adapter}
    except Exception as e:
        logger.error("Failed to load liteapi from env: %s", e)
        return {}

def build_search_service() -> SearchService:
    
    adapters = _load_adapters_from_json()
    if not adapters:
        logger.warning("Supplier config missing or empty, using env defaults")
        adapters = _load_adapters_from_env()
    return SearchService(adapters)

def build_catalog_service() -> CatalogService:
    
    cfg = get_nuitee_config()
    if not cfg.api_key:
        raise ValueError("NUITEE_API_KEY is not configured")

    adapter = LiteAPIAdapter(
        credentials={"api_key": cfg.api_key, "base_url": cfg.api_url},
        commission_percent=0,
    )
    return CatalogService(adapter)

def warm_services() -> None:
    
    from apps.api.v1.endpoints.bookings_common import booking_service
    from apps.api.v1.endpoints.search_common import search_service

    try:
        search_service._get()
    except Exception as exc:
        logger.warning("Search service not warmed: %s", exc)
    try:
        booking_service._get()
    except Exception as exc:
        logger.warning("Booking service not warmed: %s", exc)

def build_booking_service() -> BookingService:

    cfg = get_nuitee_config()
    if not cfg.api_key:
        raise ValueError("NUITEE_API_KEY is not configured")

    commission = _commission_service.platform_percent("liteapi")
    adapter = LiteAPIAdapter(
        credentials={
            "api_key": cfg.api_key,
            "base_url": cfg.api_url,
            "book_base_url": cfg.book_api_url,
        },
        commission_percent=commission,
    )
    return BookingService(adapter, _commission_service, BookingRepository())
