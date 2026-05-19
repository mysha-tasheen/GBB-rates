import logging
from ninja.errors import HttpError
from apps.api.lazy import LazyService
from apps.core.wiring import (
    build_catalog_service,
    build_commission_service,
    build_search_service,
)

logger = logging.getLogger(__name__)

catalog_service = LazyService(build_catalog_service)
search_service = LazyService(build_search_service)
commission_service = LazyService(build_commission_service)


def supplier_error(exc: Exception, message: str) -> None:
    if isinstance(exc, ValueError):
        raise HttpError(503, str(exc)) from exc
    logger.exception(message)
    raise HttpError(502, message) from exc
