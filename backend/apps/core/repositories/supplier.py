import logging
from django.db.utils import OperationalError
from apps.core.config import get_nuitee_config
from apps.core.models import Supplier

logger = logging.getLogger(__name__)


class SupplierRepository:
    

    def commission_percent(self, supplier_name: str) -> float:
        fallback = get_nuitee_config().default_commission_percent
        try:
            supplier = Supplier.objects.get(name=supplier_name, is_active=True)
            return float(supplier.commission_percent)
        except OperationalError:
            return fallback
        except Supplier.DoesNotExist:
            logger.warning(
                "No Supplier record for %s, using NUITEE_COMMISSION_PERCENT",
                supplier_name,
            )
            return fallback
