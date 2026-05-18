from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class PrebookRoom:
    rate_id: str
    room_name: str
    board_name: str
    refundable: bool
    cancellation_deadline: Optional[str]
    price: float
    currency: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rate_id": self.rate_id,
            "room_name": self.room_name,
            "board_name": self.board_name,
            "refundable": self.refundable,
            "cancellation_deadline": self.cancellation_deadline,
            "price": self.price,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class AgentPrebook:
    

    prebook_id: str
    hotel_id: str
    check_in: str
    check_out: str
    currency: str
    price: float
    terms_and_conditions: str
    room: PrebookRoom
    transaction_id: Optional[str] = None
    secret_key: Optional[str] = None
    credit_line: Optional[dict[str, Any]] = None

    def to_agent_dict(self) -> dict[str, Any]:
        data = {
            "prebook_id": self.prebook_id,
            "hotel_id": self.hotel_id,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "currency": self.currency,
            "price": self.price,
            "terms_and_conditions": self.terms_and_conditions,
            "room": self.room.to_dict(),
            "transaction_id": self.transaction_id,
            "secret_key": self.secret_key,
        }
        if self.credit_line:
            data["credit_line"] = self.credit_line
        return data


@dataclass(frozen=True)
class PrebookInternal:
    

    offer_id: str
    rate_id: str
    supplier_price: float
    commission_percent: float
    commission_amount: float
    middleware_price: float
    agent_commission: float
    agent_price: float
    currency: str
    prebook_id: str
    transaction_id: str
