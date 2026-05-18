"""
Outbound ports (typing.Protocol) — pure Python contracts for suppliers.

Implemented by apps.core.adapters (e.g. LiteAPIAdapter).
"""

from apps.core.ports.booking import BookingSupplierPort
from apps.core.ports.catalog import CatalogSupplierPort
from apps.core.ports.search import SearchSupplierPort

__all__ = ["BookingSupplierPort", "CatalogSupplierPort", "SearchSupplierPort"]
