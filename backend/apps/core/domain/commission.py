from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPriceBreakdown:
    

    supplier_price: float
    commission_percent: float
    commission_amount: float
    middleware_price: float
    agent_commission: float
    agent_price: float
