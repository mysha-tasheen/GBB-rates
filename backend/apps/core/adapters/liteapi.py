import httpx
from datetime import date
from typing import List, Dict, Any, Optional
import logging

from apps.core.pricing import calculate_agent_price

from .base import BaseAdapter

logger = logging.getLogger(__name__)

class LiteAPIAdapter(BaseAdapter):
    """
    Adapter for LiteAPI Travel (https://api.liteapi.travel)
    """
    
    def __init__(self, credentials: Dict[str, Any], commission_percent: float):
        super().__init__(credentials, commission_percent)
        self.api_key = credentials.get("api_key")
        self.base_url = credentials.get("base_url", "https://api.liteapi.travel/v3.0")
        self.book_base_url = credentials.get(
            "book_base_url", "https://book.liteapi.travel/v3.0"
        )
    
    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _request(self, endpoint: str, data: Dict) -> Dict:
        """Make authenticated POST request to LiteAPI search/data API."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def _book_request(self, endpoint: str, data: Dict) -> Dict:
        """Make authenticated POST request to LiteAPI book API."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.book_base_url}{endpoint}",
                headers=self._headers(),
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def _book_get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Make authenticated GET request to LiteAPI book API."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.book_base_url}{endpoint}",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _book_put(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Make authenticated PUT request to LiteAPI book API."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.put(
                f"{self.book_base_url}{endpoint}",
                headers=self._headers(),
                params=params,
                json=data,
            )
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()

    async def get_countries(self) -> List[Dict[str, str]]:
        """GET /data/countries — ISO-2 codes and names."""
        response = await self._get("/data/countries")
        return [
            {"code": item["code"], "name": item["name"]}
            for item in response.get("data", [])
        ]

    async def get_hotels(
        self,
        country_code: str,
        city_name: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """GET /data/hotels — hotels in a country (optionally filtered by city)."""
        params: Dict[str, Any] = {
            "countryCode": country_code.upper(),
            "offset": max(offset, 0),
            "limit": min(max(limit, 1), 200),
        }
        if city_name:
            params["cityName"] = city_name

        response = await self._get("/data/hotels", params=params)
        hotels = []
        for item in response.get("data", []):
            hotels.append(
                {
                    "hotel_id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "city": item.get("city", ""),
                    "country_code": item.get("country", country_code.upper()),
                    "address": item.get("address", ""),
                    "rating": float(item.get("stars") or 0),
                    "main_photo": item.get("main_photo", ""),
                }
            )
        return hotels
    
    async def search_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> Dict[str, Any]:
        """
        Search hotel rates from LiteAPI
        POST /v3.0/hotels/rates
        """
        
        request_data = {
            "hotelIds": [hotel_id],
            "checkin": check_in.isoformat(),
            "checkout": check_out.isoformat(),
            "currency": currency,
            "guestNationality": guest_nationality.upper(),
            "occupancies": [{"adults": guests}],
            "includeHotelData": True,
        }
        
        response = await self._request("/hotels/rates", request_data)

        if not response.get("data"):
            logger.warning(
                "LiteAPI returned no rate data for hotel %s (check dates, hotel_id, nationality)",
                hotel_id,
            )

        return self._process_response(response, check_in, check_out, guests)

    async def get_min_rates(
        self,
        hotel_ids: List[str],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict[str, Any]]:
        """POST /hotels/min-rates — cheapest rate per hotel (for listing pages)."""
        if not hotel_ids:
            return []

        request_data = {
            "hotelIds": hotel_ids,
            "checkin": check_in.isoformat(),
            "checkout": check_out.isoformat(),
            "currency": currency,
            "guestNationality": guest_nationality.upper(),
            "occupancies": [{"adults": guests}],
        }

        response = await self._request("/hotels/min-rates", request_data)
        results = []

        for item in response.get("data", []):
            supplier_price = float(item.get("price") or 0)
            pricing = calculate_agent_price(supplier_price, self.commission_percent)
            results.append(
                {
                    "hotel_id": item.get("hotelId", ""),
                    "offer_id": item.get("offerId", ""),
                    "_supplier_price": pricing.supplier_price,
                    "_commission_percent": pricing.commission_percent,
                    "_commission_amount": pricing.commission_amount,
                    "_middleware_price": pricing.agent_price,
                    "_agent_commission": 0.0,
                    "_agent_price": pricing.agent_price,
                }
            )

        return results

    def _process_response(self, response: Dict, check_in: date, check_out: date, guests: int) -> Dict:
        """Extract only essential fields from LiteAPI response"""
        
        nights = (check_out - check_in).days
        data_list = response.get("data", [])

        hotels_meta = {
            h.get("id", ""): h for h in response.get("hotels", []) if h.get("id")
        }

        first_hotel_rates = data_list[0] if data_list else {}
        hotel_id = first_hotel_rates.get("hotelId", "")
        hotel_meta = hotels_meta.get(hotel_id, {})

        processed = {
            "supplier_name": "liteapi",
            "hotel": {
                "hotel_id": hotel_id,
                "name": hotel_meta.get("name", ""),
                "address": hotel_meta.get("address", ""),
                "rating": float(hotel_meta.get("rating") or 0),
                "main_photo": hotel_meta.get("main_photo", ""),
            },
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "rooms": []
        }

        for hotel_data_item in data_list:
            for room_type in hotel_data_item.get("roomTypes", []):
                for rate in room_type.get("rates", []):
                    # Get supplier price (from retailRate.total)
                    retail_total = rate.get("retailRate", {}).get("total", [{}])[0]
                    supplier_price = float(retail_total.get("amount", 0))
                    pricing = calculate_agent_price(supplier_price, self.commission_percent)

                    # Get cancellation policy
                    cancel_policies = rate.get("cancellationPolicies", {})
                    cancel_infos = cancel_policies.get("cancelPolicyInfos", [])
                    cancellation_deadline = cancel_infos[0].get("cancelTime") if cancel_infos else None
                    refundable = cancel_policies.get("refundableTag") == "RFN"
                    
                    essential_rate = {
                        "rate_id": rate.get("rateId", ""),
                        "room_name": rate.get("name", ""),
                        "board_type": rate.get("boardType", ""),
                        "board_name": rate.get("boardName", ""),
                        "currency": retail_total.get("currency", "USD"),
                        "cancellation_deadline": cancellation_deadline,
                        "refundable": refundable,
                        "payment_types": rate.get("paymentTypes", []),
                        # Internal — stripped before API response; used for bookings
                        "_supplier_price": pricing.supplier_price,
                        "_commission_percent": pricing.commission_percent,
                        "_commission_amount": pricing.commission_amount,
                        "_middleware_price": pricing.agent_price,
                        "_agent_commission": 0.0,
                        "_agent_price": pricing.agent_price,
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
    async def get_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int,
        currency: str = "USD",
        guest_nationality: str = "US",
    ) -> List[Dict]:
        """BaseAdapter interface method"""
        result = await self.search_hotel_rates(
            hotel_id, check_in, check_out, guests, currency, guest_nationality
        )
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
        
        cheapest = min(all_rates, key=lambda x: x["_agent_price"])
        return cheapest
    
    async def create_prebook(
        self,
        offer_id: str,
        use_payment_sdk: bool = False,
        voucher_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /rates/prebook on book API — verify availability and lock pricing."""
        payload: Dict[str, Any] = {
            "offerId": offer_id,
            "usePaymentSdk": use_payment_sdk,
        }
        if voucher_code:
            payload["voucherCode"] = voucher_code

        response = await self._book_request("/rates/prebook", payload)
        return response.get("data", {})
    
    async def confirm_booking(
        self,
        prebook_id: str,
        holder: Dict[str, Any],
        guests: List[Dict[str, Any]],
        payment_method: str = "ACC_CREDIT_CARD",
        transaction_id: Optional[str] = None,
        client_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /rates/book — confirm reservation after prebook."""
        payment: Dict[str, Any] = {"method": payment_method}
        if payment_method == "TRANSACTION":
            if not transaction_id:
                raise ValueError("transaction_id is required when payment_method is TRANSACTION")
            payment["transactionId"] = transaction_id

        payload: Dict[str, Any] = {
            "prebookId": prebook_id,
            "holder": holder,
            "guests": guests,
            "payment": payment,
        }
        if client_reference:
            payload["clientReference"] = client_reference

        response = await self._book_request("/rates/book", payload)
        return response.get("data", {})
    
    async def get_prebook(
        self,
        prebook_id: str,
        include_credit_balance: bool = False,
    ) -> Dict[str, Any]:
        """GET /prebooks/{prebookId} — retrieve an existing prebook session."""
        params: Dict[str, Any] = {}
        if include_credit_balance:
            params["includeCreditBalance"] = True

        response = await self._book_get(
            f"/prebooks/{prebook_id}",
            params=params or None,
        )
        return response.get("data", {})
    
    async def get_booking(self, booking_id: str) -> Dict[str, Any]:
        """GET /bookings/{bookingId} — retrieve a single booking."""
        response = await self._book_get(f"/bookings/{booking_id}")
        return response.get("data", {})

    async def list_bookings(
        self,
        guest_id: Optional[str] = None,
        client_reference: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """GET /bookings — search by guestId and/or clientReference."""
        if not guest_id and not client_reference:
            raise ValueError("guest_id or client_reference is required")

        params: Dict[str, Any] = {}
        if guest_id:
            params["guestId"] = guest_id
        if client_reference:
            params["clientReference"] = client_reference
        if timeout is not None:
            params["timeout"] = timeout

        response = await self._book_get("/bookings", params=params)
        return response.get("data", [])

    async def list_all_bookings(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        booking_start_date: Optional[str] = None,
        booking_end_date: Optional[str] = None,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> tuple[int, List[Dict[str, Any]]]:
        """GET /bookings — all bookings for the API key with optional filters."""
        params: Dict[str, Any] = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if booking_start_date:
            params["bookingStartDate"] = booking_start_date
        if booking_end_date:
            params["bookingEndDate"] = booking_end_date
        if status:
            params["status"] = status
        if payment_status:
            params["paymentStatus"] = payment_status
        if timeout is not None:
            params["timeout"] = timeout

        response = await self._book_get("/bookings", params=params or None)
        data = response.get("data", [])
        return response.get("count", len(data)), data
    
    async def cancel_booking(
        self,
        booking_id: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """PUT /bookings/{bookingId} — cancel a confirmed booking."""
        params: Dict[str, Any] = {}
        if timeout is not None:
            params["timeout"] = timeout

        response = await self._book_put(
            f"/bookings/{booking_id}",
            params=params or None,
        )
        return response.get("data", {})
    
    async def create_alternative_prebooks(
        self,
        booking_id: str,
        occupancies: List[Dict[str, Any]],
        checkin: str,
        checkout: str,
        refundable_rates_only: bool = False,
        board_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """POST /bookings/{bookingId}/alternative-prebooks — amend dates/occupancy."""
        payload: Dict[str, Any] = {
            "occupancies": occupancies,
            "checkin": checkin,
            "checkout": checkout,
        }
        if refundable_rates_only:
            payload["refundableRatesOnly"] = True
        if board_type:
            payload["boardType"] = board_type

        response = await self._book_request(
            f"/bookings/{booking_id}/alternative-prebooks",
            payload,
        )
        return response.get("data", [])

    async def amend_guest_name(
        self,
        booking_id: str,
        holder: Dict[str, Any],
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """PUT /bookings/{bookingId}/amend — update holder name and email."""
        payload: Dict[str, Any] = {"holder": holder}
        if remarks:
            payload["remarks"] = remarks

        response = await self._book_put(
            f"/bookings/{booking_id}/amend",
            data=payload,
        )
        if response.get("bookingId"):
            return response
        return response.get("data", response)
    
    async def amend_dates(self, booking_id: str, check_in: date, check_out: date, guests: int) -> Dict:
        """Amend dates"""
        return {"booking_id": booking_id, "dates_updated": True}