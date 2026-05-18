from dataclasses import dataclass


@dataclass(frozen=True)
class PricingBreakdown:
    """Internal pricing — never expose commission fields to agents."""

    supplier_price: float
    commission_percent: float
    commission_amount: float
    agent_price: float

    @property
    def currency_note(self) -> str:
        return (
            f"supplier={self.supplier_price}, commission={self.commission_amount} "
            f"({self.commission_percent}%), agent={self.agent_price}"
        )


def apply_agent_commission_to_min_rates(
    rates: list[dict], commission: float | None
) -> list[dict]:
    """Add optional agent commission to each hotel min-rate."""
    extra = round(commission or 0, 2)
    for rate in rates:
        middleware_price = rate.get("_agent_price", 0)
        rate["_middleware_price"] = middleware_price
        rate["_agent_commission"] = extra
        rate["_agent_price"] = round(middleware_price + extra, 2)
    return rates


def apply_agent_commission(internal: dict, commission: float | None) -> dict:
    """
    Add optional agent commission on top of middleware price (per rate).

    Example: middleware $1030 + agent commission $50 → agent sees $1080.
    """
    extra = round(commission or 0, 2)

    for room in internal.get("rooms", []):
        for rate in room.get("rates", []):
            middleware_price = rate.get("_agent_price", 0)
            rate["_middleware_price"] = middleware_price
            rate["_agent_commission"] = extra
            rate["_agent_price"] = round(middleware_price + extra, 2)

    return internal


def calculate_agent_price(supplier_price: float, commission_percent: float) -> PricingBreakdown:
    """
    Apply B2B markup: agent_price = supplier_price + (supplier_price × commission%).

    Example: $1000 supplier @ 3% → $30 commission → $1030 agent price.
    """
    commission_amount = round(supplier_price * (commission_percent / 100), 2)
    agent_price = round(supplier_price + commission_amount, 2)
    return PricingBreakdown(
        supplier_price=round(supplier_price, 2),
        commission_percent=commission_percent,
        commission_amount=commission_amount,
        agent_price=agent_price,
    )
