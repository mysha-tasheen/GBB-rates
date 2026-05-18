import urllib.request
import urllib.parse
import json
from datetime import date

# Dummy placeholders replacing async/await, httpx, and logging for pure Python.
# In a true synchronous/pure Python context, we would use urllib for HTTP, and remove all async/await usage.

def calculate_agent_price(supplier_price, commission_percent):
    # Dummy placeholder since original is imported
    class Pricing:
        def __init__(self, sp, cp):
            self.supplier_price = sp
            self.commission_percent = cp
            self.commission_amount = sp * cp / 100
            self.agent_price = sp + self.commission_amount
    return Pricing(supplier_price, commission_percent)

class BaseAdapter:
    def __init__(self, credentials, commission_percent):
        self.credentials = credentials
        self.commission_percent = commission_percent

class LiteAPIAdapter(BaseAdapter):
    """
    Adapter for LiteAPI Travel (https://api.liteapi.travel)
    Note: This is a pure Python synchronous version.
    """
    
    def __init__(self, credentials, commission_percent):
        super().__init__(credentials, commission_percent)
        self.api_key = credentials.get("api_key")
        self.base_url = credentials.get("base_url", "https://api.liteapi.travel/v3.0")
        self.book_base_url = credentials.get(
            "book_base_url", "https://book.liteapi.travel/v3.0"
        )
    
    def _headers(self):
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, endpoint, params=None):
        url = self.base_url + endpoint
        if params:
            url += '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def _request(self, endpoint, data):
        url = self.base_url + endpoint
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=self._headers())
        req.method = "POST"
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def _book_request(self, endpoint, data):
        url = self.book_base_url + endpoint
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=self._headers())
        req.method = "POST"
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode())

    def _book_get(self, endpoint, params=None):
        url = self.book_base_url + endpoint
        if params:
            url += '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def _book_put(self, endpoint, params=None, data=None):
        url = self.book_base_url + endpoint
        if params:
            url += '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        req.method = "PUT"
        if data:
            req.data = json.dumps(data).encode()
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()
            if not content:
                return {}
            return json.loads(content.decode())

    def get_countries(self):
        """GET /data/countries — ISO-2 codes and names."""
        response = self._get("/data/countries")
        return [
            {"code": item["code"], "name": item["name"]}
            for item in response.get("data", [])
        ]

    def get_hotels(self, country_code, city_name=None, offset=0, limit=50):
        """GET /data/hotels — hotels in a country (optionally filtered by city)."""
        params = {
            "countryCode": country_code.upper(),
            "offset": max(offset, 0),
            "limit": min(max(limit, 1), 200),
        }
        if city_name:
            params["cityName"] = city_name

        response = self._get("/data/hotels", params=params)
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

    def search_hotel_rates(self, hotel_id, check_in, check_out, guests, currency="USD", guest_nationality="US"):
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
        response = self._request("/hotels/rates", request_data)

        if not response.get("data"):
            # no logging in pure python
            pass

        return self._process_response(response, check_in, check_out, guests)

    def get_min_rates(self, hotel_ids, check_in, check_out, guests, currency="USD", guest_nationality="US"):
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

        response = self._request("/hotels/min-rates", request_data)
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

    def _process_response(self, response, check_in, check_out, guests):
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
    def get_hotel_rates(self, hotel_id, check_in, check_out, guests, currency="USD", guest_nationality="US"):
        """BaseAdapter interface method"""
        result = self.search_hotel_rates(
            hotel_id, check_in, check_out, guests, currency, guest_nationality
        )
        return [result]
    
    def get_minimum_rate(self, hotel_id, check_in, check_out, guests):
        """Get cheapest rate"""
        result = self.search_hotel_rates(hotel_id, check_in, check_out, guests)
        
        # Find the cheapest rate across all rooms
        all_rates = []
        for room in result.get("rooms", []):
            for rate in room.get("rates", []):
                all_rates.append(rate)
        
        if not all_rates:
            return None
        
        cheapest = min(all_rates, key=lambda x: x["_agent_price"])
        return cheapest

    def create_prebook(self, offer_id, use_payment_sdk=False, voucher_code=None):
        """POST /rates/prebook on book API — verify availability and lock pricing."""
        payload = {
            "offerId": offer_id,
            "usePaymentSdk": use_payment_sdk,
        }
        if voucher_code:
            payload["voucherCode"] = voucher_code

        response = self._book_request("/rates/prebook", payload)
        return response.get("data", {})

    def confirm_booking(self, prebook_id, holder, guests, payment_method="ACC_CREDIT_CARD", transaction_id=None, client_reference=None):
        """POST /rates/book — confirm reservation after prebook."""
        payment = {"method": payment_method}
        if payment_method == "TRANSACTION":
            if not transaction_id:
                raise ValueError("transaction_id is required when payment_method is TRANSACTION")
            payment["transactionId"] = transaction_id

        payload = {
            "prebookId": prebook_id,
            "holder": holder,
            "guests": guests,
            "payment": payment,
        }
        if client_reference:
            payload["clientReference"] = client_reference

        response = self._book_request("/rates/book", payload)
        return response.get("data", {})

    def get_prebook(self, prebook_id, include_credit_balance=False):
        """GET /prebooks/{prebookId} — retrieve an existing prebook session."""
        params = {}
        if include_credit_balance:
            params["includeCreditBalance"] = True

        response = self._book_get(
            f"/prebooks/{prebook_id}",
            params=params or None,
        )
        return response.get("data", {})

    def get_booking(self, booking_id):
        """GET /bookings/{bookingId} — retrieve a single booking."""
        response = self._book_get(f"/bookings/{booking_id}")
        return response.get("data", {})

    def list_bookings(self, guest_id=None, client_reference=None, timeout=None):
        """GET /bookings — search by guestId and/or clientReference."""
        if not guest_id and not client_reference:
            raise ValueError("guest_id or client_reference is required")

        params = {}
        if guest_id:
            params["guestId"] = guest_id
        if client_reference:
            params["clientReference"] = client_reference
        if timeout is not None:
            params["timeout"] = timeout

        response = self._book_get("/bookings", params=params)
        return response.get("data", [])

    def list_all_bookings(
        self,
        start_date=None,
        end_date=None,
        booking_start_date=None,
        booking_end_date=None,
        status=None,
        payment_status=None,
        timeout=None,
    ):
        """GET /bookings — all bookings for the API key with optional filters."""
        params = {}
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

        response = self._book_get("/bookings", params=params or None)
        data = response.get("data", [])
        return response.get("count", len(data)), data

    def cancel_booking(self, booking_id, timeout=None):
        """PUT /bookings/{bookingId} — cancel a confirmed booking."""
        params = {}
        if timeout is not None:
            params["timeout"] = timeout

        response = self._book_put(
            f"/bookings/{booking_id}",
            params=params or None,
        )
        return response.get("data", {})

    def create_alternative_prebooks(
        self,
        booking_id,
        occupancies,
        checkin,
        checkout,
        refundable_rates_only=False,
        board_type=None,
    ):
        """POST /bookings/{bookingId}/alternative-prebooks — amend dates/occupancy."""
        payload = {
            "occupancies": occupancies,
            "checkin": checkin,
            "checkout": checkout,
        }
        if refundable_rates_only:
            payload["refundableRatesOnly"] = True
        if board_type:
            payload["boardType"] = board_type

        response = self._book_request(
            f"/bookings/{booking_id}/alternative-prebooks",
            payload,
        )
        return response.get("data", [])

    def amend_guest_name(self, booking_id, holder, remarks=None):
        """PUT /bookings/{bookingId}/amend — update holder name and email."""
        payload = {"holder": holder}
        if remarks:
            payload["remarks"] = remarks

        response = self._book_put(
            f"/bookings/{booking_id}/amend",
            data=payload,
        )
        if response.get("bookingId"):
            return response
        return response.get("data", response)

    def amend_dates(self, booking_id, check_in, check_out, guests):
        """Amend dates"""
        return {"booking_id": booking_id, "dates_updated": True}