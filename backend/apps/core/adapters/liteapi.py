import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from apps.core.exceptions import SupplierAPIError


def _path_segment(value: str) -> str:
    
    return urllib.parse.quote(value, safe="")



def calculate_agent_price(supplier_price, commission_percent):

    class Pricing:
        def __init__(self, sp, cp):
            self.supplier_price = sp
            self.commission_percent = cp
            self.commission_amount = sp * cp / 100
            self.agent_price = sp + self.commission_amount
    return Pricing(supplier_price, commission_percent)


def _raise_http_error(exc: urllib.error.HTTPError) -> None:
    raw = exc.read().decode(errors="replace") if exc.fp else ""
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {}
    if isinstance(body.get("error"), dict):
        message = body["error"].get("message") or body.get("message")
    else:
        message = body.get("message") or (
            body.get("error") if isinstance(body.get("error"), str) else None
        )
    if not message:
        message = raw[:500] if raw else exc.reason
    raise SupplierAPIError(exc.code, str(message), body if isinstance(body, dict) else {}) from exc


class BaseAdapter:
    def __init__(self, credentials, commission_percent):
        self.credentials = credentials
        self.commission_percent = commission_percent

class LiteAPIAdapter(BaseAdapter):
    
    
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
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            _raise_http_error(exc)

    def _request(self, endpoint, data):
        url = self.base_url + endpoint
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=self._headers())
        req.method = "POST"
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            _raise_http_error(exc)

    def _book_request(self, endpoint, data):
        url = self.book_base_url + endpoint
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=self._headers())
        req.method = "POST"
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            _raise_http_error(exc)

    def _book_get(self, endpoint, params=None):
        url = self.book_base_url + endpoint
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            _raise_http_error(exc)

    def _book_put(self, endpoint, params=None, data=None):
        url = self.book_base_url + endpoint
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        req.method = "PUT"
        if data:
            req.data = json.dumps(data).encode()
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
                if not content:
                    return {}
                return json.loads(content.decode())
        except urllib.error.HTTPError as exc:
            _raise_http_error(exc)

    def get_countries(self):
        
        response = self._get("/data/countries")
        return [
            {"code": item["code"], "name": item["name"]}
            for item in response.get("data", [])
        ]

    def get_currencies(self):
        """GET /data/currencies — reference list for wholesaler pricing / payment currency (UI)."""
        response = self._get("/data/currencies")
        return [
            {
                "code": item.get("code", ""),
                "name": item.get("currency", ""),
                "countries": list(item.get("countries") or []),
            }
            for item in response.get("data", [])
            if item.get("code")
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

    @staticmethod
    def _price_from_rate(rate):
        
        retail = rate.get("retailRate") or {}
        for key in ("total", "suggestedSellingPrice", "initialPrice"):
            entries = retail.get(key) or []
            if isinstance(entries, dict):
                entries = [entries]
            if entries:
                amount = entries[0].get("amount", 0)
                if isinstance(amount, dict):
                    amount = amount.get("amount", 0)
                price = float(amount or 0)
                if price > 0:
                    currency = entries[0].get("currency", "USD")
                    return price, currency
        return 0.0, "USD"

    def search_hotel_rates(self, hotel_id, check_in, check_out, guests, currency="USD", guest_nationality="US"):
        
        request_data = {
            "hotelIds": [hotel_id],
            "checkin": check_in.isoformat(),
            "checkout": check_out.isoformat(),
            "currency": currency,
            "guestNationality": guest_nationality.upper(),
            "occupancies": [{"rooms": 1, "adults": guests}],
            "includeHotelData": True,
            "timeout": 12,
        }
        response = self._request("/hotels/rates", request_data)

        if not response.get("data"):
            
            pass

        return self._process_response(response, check_in, check_out, guests)

    def get_min_rates(self, hotel_ids, check_in, check_out, guests, currency="USD", guest_nationality="US"):
        
        if not hotel_ids:
            return []

        request_data = {
            "hotelIds": hotel_ids,
            "checkin": check_in.isoformat(),
            "checkout": check_out.isoformat(),
            "currency": currency,
            "guestNationality": guest_nationality.upper(),
            "occupancies": [{"rooms": 1, "adults": guests}],
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
        for item in data_list:
            embedded = item.get("hotel") or {}
            hid = item.get("hotelId") or embedded.get("id")
            if hid and hid not in hotels_meta and embedded:
                hotels_meta[hid] = embedded

        first_hotel_rates = data_list[0] if data_list else {}
        hotel_id = first_hotel_rates.get("hotelId", "")
        hotel_meta = hotels_meta.get(hotel_id, {})

        processed = {
            "hotel": {
                "hotel_id": hotel_id,
                "name": hotel_meta.get("name", ""),
                "address": hotel_meta.get("address", ""),
                "rating": float(
                    hotel_meta.get("rating")
                    or hotel_meta.get("stars")
                    or hotel_meta.get("starRating")
                    or 0
                ),
                "main_photo": hotel_meta.get("main_photo")
                or hotel_meta.get("thumbnail")
                or hotel_meta.get("mainPhoto")
                or "",
            },
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "rooms": [],
        }

        rooms_by_offer: dict[str, dict] = {}

        for hotel_data_item in data_list:
            for room_type in hotel_data_item.get("roomTypes", []):
                offer_id = room_type.get("offerId", "")
                room_key = offer_id or room_type.get("roomTypeId", "")
                if room_key not in rooms_by_offer:
                    rooms_by_offer[room_key] = {
                        "room_type_id": room_type.get("roomTypeId", ""),
                        "offer_id": offer_id,
                        "room_name": "",
                        "rates": [],
                    }

                for rate in room_type.get("rates", []):
                    supplier_price, rate_currency = self._price_from_rate(rate)
                    if supplier_price <= 0:
                        continue

                    pricing = calculate_agent_price(
                        supplier_price, self.commission_percent
                    )

                    cancel_policies = rate.get("cancellationPolicies", {})
                    cancel_infos = cancel_policies.get("cancelPolicyInfos", [])
                    cancellation_deadline = (
                        cancel_infos[0].get("cancelTime") if cancel_infos else None
                    )
                    refundable = cancel_policies.get("refundableTag") == "RFN"

                    rate_room_name = rate.get("name") or ""
                    if rate_room_name and not rooms_by_offer[room_key]["room_name"]:
                        rooms_by_offer[room_key]["room_name"] = rate_room_name

                    rooms_by_offer[room_key]["rates"].append(
                        {
                            "rate_id": rate.get("rateId", ""),
                            "room_name": rate_room_name,
                            "board_type": rate.get("boardType", ""),
                            "board_name": rate.get("boardName", ""),
                            "currency": rate_currency,
                            "cancellation_deadline": cancellation_deadline,
                            "refundable": refundable,
                            "_supplier_price": pricing.supplier_price,
                            "_commission_percent": pricing.commission_percent,
                            "_commission_amount": pricing.commission_amount,
                            "_middleware_price": pricing.agent_price,
                            "_agent_commission": 0.0,
                            "_agent_price": pricing.agent_price,
                        }
                    )

        processed["rooms"] = [
            room for room in rooms_by_offer.values() if room["rates"]
        ]
        return processed
    
    
    def get_hotel_rates(self, hotel_id, check_in, check_out, guests, currency="USD", guest_nationality="US"):
        """BaseAdapter interface method"""
        result = self.search_hotel_rates(
            hotel_id, check_in, check_out, guests, currency, guest_nationality
        )
        return [result]
    
    def get_minimum_rate(self, hotel_id, check_in, check_out, guests):
        
        result = self.search_hotel_rates(hotel_id, check_in, check_out, guests)
        
        
        all_rates = []
        for room in result.get("rooms", []):
            for rate in room.get("rates", []):
                all_rates.append(rate)
        
        if not all_rates:
            return None
        
        cheapest = min(all_rates, key=lambda x: x["_agent_price"])
        return cheapest

    def create_prebook(self, offer_id, use_payment_sdk=False):
        
        offer_id = (offer_id or "").strip()
        if not offer_id:
            raise ValueError("offer_id is required")

        payload = {
            "offerId": offer_id,
            "usePaymentSdk": bool(use_payment_sdk),
        }

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
        
        params = {}
        if include_credit_balance:
            params["includeCreditBalance"] = True

        response = self._book_get(
            f"/prebooks/{_path_segment(prebook_id)}",
            params=params or None,
        )
        return response.get("data", {})

    def get_booking(self, booking_id):
        
        response = self._book_get(f"/bookings/{_path_segment(booking_id)}")
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

        
        response = self._book_get("/bookings/", params=params or None)
        data = response.get("data", [])
        return response.get("count", len(data)), data

    def cancel_booking(self, booking_id, timeout=None):
        
        params = {}
        if timeout is not None:
            params["timeout"] = timeout

        response = self._book_put(
            f"/bookings/{_path_segment(booking_id)}",
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
            f"/bookings/{_path_segment(booking_id)}/alternative-prebooks",
            payload,
        )
        return response.get("data", [])

    def amend_guest_name(self, booking_id, holder, remarks=None):
    
        payload = {"holder": holder}
        if remarks:
            payload["remarks"] = remarks

        response = self._book_put(
            f"/bookings/{_path_segment(booking_id)}/amend",
            data=payload,
        )
        if response.get("bookingId"):
            return response
        return response.get("data", response)

    def amend_dates(self, booking_id, check_in, check_out, guests):
        
        return {"booking_id": booking_id, "dates_updated": True}