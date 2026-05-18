from apps.core.domain.commission import AgentPriceBreakdown
from apps.core.pricing import (
    PricingBreakdown,
    apply_agent_commission,
    apply_agent_commission_to_min_rates,
    calculate_agent_price,
)
from apps.core.repositories.supplier import SupplierRepository


class CommissionService:


    def __init__(self, suppliers: SupplierRepository | None = None):
        self._suppliers = suppliers or SupplierRepository()

    def platform_percent(self, supplier_name: str = "liteapi") -> float:
        return self._suppliers.commission_percent(supplier_name)

    def middleware_price(
        self,
        supplier_price: float,
        supplier_name: str = "liteapi",
    ) -> PricingBreakdown:
        return calculate_agent_price(
            supplier_price,
            self.platform_percent(supplier_name),
        )

    def agent_price_breakdown(
        self,
        supplier_price: float,
        agent_flat_commission: float = 0,
        supplier_name: str = "liteapi",
    ) -> AgentPriceBreakdown:
        pricing = self.middleware_price(supplier_price, supplier_name)
        extra = round(agent_flat_commission or 0, 2)
        return AgentPriceBreakdown(
            supplier_price=pricing.supplier_price,
            commission_percent=pricing.commission_percent,
            commission_amount=pricing.commission_amount,
            middleware_price=pricing.agent_price,
            agent_commission=extra,
            agent_price=round(pricing.agent_price + extra, 2),
        )

    def apply_flat_to_min_rates(
        self, rates: list[dict], agent_flat_commission: float | None
    ) -> list[dict]:
        return apply_agent_commission_to_min_rates(rates, agent_flat_commission)

    def apply_flat_to_hotel_rates(
        self, internal: dict, agent_flat_commission: float | None
    ) -> dict:
        return apply_agent_commission(internal, agent_flat_commission)
