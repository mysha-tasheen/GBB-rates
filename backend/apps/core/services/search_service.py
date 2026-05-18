import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import date
import logging

from apps.core.adapters.registry import registry
from apps.core.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.active_adapters: Dict[str, BaseAdapter] = {}
        self._load_active_suppliers()
    
    def _load_active_suppliers(self):
        """Load configuration and create adapters for active suppliers"""
        config_path = Path(__file__).parent.parent.parent.parent / "data" / "suppliers.json"
        
        if not config_path.exists():
            logger.warning(f"Supplier config not found at {config_path}")
            return
        
        with open(config_path) as f:
            config = json.load(f)
        
        for supplier_config in config.get("suppliers", []):
            if not supplier_config.get("is_active", True):
                continue
            
            supplier_name = supplier_config["name"]
            commission = supplier_config["commission_percent"]
            credentials = supplier_config["credentials"]
            
            try:
                adapter = registry.get_adapter(supplier_name, credentials, commission)
                self.active_adapters[supplier_name] = adapter
                logger.info(f"Loaded adapter for {supplier_name} with {commission}% commission")
            except Exception as e:
                logger.error(f"Failed to load {supplier_name}: {e}")
    
    async def search_all_suppliers(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """Search across all active suppliers"""
        
        all_results = []
        
        for supplier_name, adapter in self.active_adapters.items():
            try:
                results = await adapter.get_hotel_rates(
                    hotel_id=hotel_id,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency
                )
                all_results.extend(results)
                logger.info(f"Found {len(results)} results from {supplier_name}")
                
            except Exception as e:
                logger.error(f"Failed to search {supplier_name}: {str(e)}")
                # Continue with other suppliers
        
        return all_results