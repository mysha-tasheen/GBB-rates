"""
Django ORM persistence (database layer).

Imports apps.core.models and maps to domain types. Services must not import Django.
"""

from apps.core.repositories.booking import BookingRepository
from apps.core.repositories.supplier import SupplierRepository

__all__ = ["BookingRepository", "SupplierRepository"]
