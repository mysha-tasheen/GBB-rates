import httpx
from datetime import date
from typing import List, Dict, Any, Optional
import logging

from .base import BaseAdapter
from config.settings import settings

logger = logging.getLogger(__name__)

class LiteAPIAdapter(BaseAdapter):
    """
    Adapter for LiteAPI Travel (https://api.liteapi.travel)
    """
    
    def __init__(self, credentials: Dict[str, Any], commission_percent: float):
        super().__init__(credentials, commission_percent)
        self.api_key = credentials.get("api_key")
        self.base_url = credentials.get("base_url", "https://api.liteapi.travel/v3.0")
    
    async def _request(self, endpoint: str, data: Dict) -> Dict:
        """Make authenticated request to LiteAPI"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    def _calculate_commission(self, price: float) -> Dict:
        """Calculate commission and final price"""
        commission_amount = price * (self.commission_percent / 100)
        return {
            "supplier_price": price,
            "commission_percent": self.commission_percent,
            "commission_amount": round(commission_amount, 2),
            "final_price": round(price + commission_amount, 2)
        }
    
    async def search_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Search hotel rates from LiteAPI
        POST /v3.0/hotels/rates
        """
        
        # Prepare request for LiteAPI
        request_data = {
            "hotel_ids": [hotel_id],
            "checkin": check_in.isoformat(),
            "checkout": check_out.isoformat(),
            "adults": guests,
            "currency": currency
        }
        
        # Call LiteAPI
        response = await self._request("/hotels/rates", request_data)
        
        # Process response - extract essential fields
        processed_response = self._process_response(response, check_in, check_out, guests)
        
        return processed_response
    
    def _process_response(self, response: Dict, check_in: date, check_out: date, guests: int) -> Dict:
        """Extract only essential fields from LiteAPI response"""
        
        nights = (check_out - check_in).days
        
        # Get hotel info
        hotel_data = response.get("hotels", [{}])[0] if response.get("hotels") else {}
        
        processed = {
            "supplier_name": "liteapi",
            "hotel": {
                "hotel_id": hotel_data.get("id", ""),
                "name": hotel_data.get("name", ""),
                "address": hotel_data.get("address", ""),
                "rating": hotel_data.get("rating", 0.0),
                "main_photo": hotel_data.get("main_photo", "")
            },
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "rooms": []
        }
        
        # Process room types and rates
        data_list = response.get("data", [])
        for hotel_data_item in data_list:
            for room_type in hotel_data_item.get("roomTypes", []):
                for rate in room_type.get("rates", []):
                    # Get supplier price (from retailRate.total)
                    retail_total = rate.get("retailRate", {}).get("total", [{}])[0]
                    supplier_price = float(retail_total.get("amount", 0))
                    
                    # Calculate commission
                    commission_info = self._calculate_commission(supplier_price)
                    
                    # Get cancellation policy
                    cancel_policies = rate.get("cancellationPolicies", {})
                    cancel_infos = cancel_policies.get("cancelPolicyInfos", [])
                    cancellation_deadline = cancel_infos[0].get("cancelTime") if cancel_infos else None
                    refundable = cancel_policies.get("refundableTag") == "RFN"
                    
                    # Build essential rate
                    essential_rate = {
                        "rate_id": rate.get("rateId", ""),
                        "room_name": rate.get("name", ""),
                        "board_type": rate.get("boardType", ""),
                        "board_name": rate.get("boardName", ""),
                        "supplier_price": commission_info["supplier_price"],
                        "commission_percent": commission_info["commission_percent"],
                        "commission_amount": commission_info["commission_amount"],
                        "final_price": commission_info["final_price"],
                        "currency": retail_total.get("currency", "USD"),
                        "cancellation_deadline": cancellation_deadline,
                        "refundable": refundable,
                        "payment_types": rate.get("paymentTypes", [])
                    }
                    
                    # Build room type
                    essential_room = {
                        "room_type_id": room_type.get("roomTypeId", ""),
                        "offer_id": room_type.get("offerId", ""),
                        "supplier": room_type.get("supplier", "liteapi"),
                        "rates": [essential_rate]
                    }
                    
                    processed["rooms"].append(essential_room)
        
        return processed
    
    # Required BaseAdapter methods
    async def get_hotel_rates(self, hotel_id: str, check_in: date, check_out: date, guests: int, currency: str = "USD") -> List[Dict]:
        """BaseAdapter interface method"""
        result = await self.search_hotel_rates(hotel_id, check_in, check_out, guests, currency)
        return [result]
    
    async def get_minimum_rate(self, hotel_id: str, check_in: date, check_out: date, guests: int) -> Optional[Dict]:
        """Get cheapest rate"""
        result = await self.search_hotel_rates(hotel_id, check_in, check_out, guests)
        
        # Find the cheapest rate across all rooms
        all_rates = []
        for room in result.get("rooms", []):
            for rate in room.get("rates", []):
                all_rates.append(rate)
        
        if not all_rates:
            return None
        
        cheapest = min(all_rates, key=lambda x: x["final_price"])
        return cheapest
    
    async def create_checkout_session(self, rate_id: str, guest_details: Dict, final_price: float) -> Dict:
        """Create prebook - implement based on LiteAPI prebook endpoint"""
        # TODO: Implement LiteAPI prebook endpoint
        return {"session_id": f"prebook_{rate_id}", "expires_at": "2026-06-01T23:59:59Z"}
    
    async def complete_booking(self, session_id: str, payment_details: Dict) -> Dict:
        """Confirm booking - implement based on LiteAPI confirm endpoint"""
        # TODO: Implement LiteAPI confirm endpoint
        return {"booking_reference": f"booking_{session_id}", "status": "confirmed"}
    
    async def get_prebook(self, prebook_id: str) -> Dict:
        """Get prebook status"""
        return {"status": "active", "expires_at": "2026-06-01T23:59:59Z"}
    
    async def get_booking(self, booking_id: str) -> Dict:
        """Get booking details"""
        return {"booking_id": booking_id, "status": "confirmed"}
    
    async def list_bookings(self, agent_id: str) -> List[Dict]:
        """List agent bookings"""
        return []
    
    async def cancel_booking(self, booking_id: str) -> Dict:
        """Cancel booking"""
        return {"booking_id": booking_id, "status": "cancelled"}
    
    async def amend_guest_name(self, booking_id: str, guest_details: Dict) -> Dict:
        """Amend guest name"""
        return {"booking_id": booking_id, "guest_updated": True}
    
    async def amend_dates(self, booking_id: str, check_in: date, check_out: date, guests: int) -> Dict:
        """Amend dates"""
        return {"booking_id": booking_id, "dates_updated": True}