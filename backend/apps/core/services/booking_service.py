from apps.core.pricing import calculate_agent_price
from apps.core.repositories.booking import BookingRecord


class BookingAdapter:
    async def create_prebook(self, offer_id, use_payment_sdk, voucher_code=None):
        raise NotImplementedError

    async def get_prebook(self, prebook_id, include_credit_balance=False):
        raise NotImplementedError

    async def list_bookings(self, guest_id=None, client_reference=None, timeout=None):
        raise NotImplementedError

    async def list_all_bookings(
        self,
        start_date=None,
        end_date=None,
        booking_start_date=None,
        booking_end_date=None,
        status=None,
        payment_status=None,
        timeout=None,
    ):
        raise NotImplementedError

    async def get_booking(self, booking_id):
        raise NotImplementedError

    async def cancel_booking(self, booking_id, timeout=None):
        raise NotImplementedError

    async def amend_guest_name(self, booking_id, holder, remarks=None):
        raise NotImplementedError

    async def create_alternative_prebooks(
        self, booking_id, occupancies, checkin, checkout, **kwargs
    ):
        raise NotImplementedError

    async def confirm_booking(
        self,
        prebook_id,
        holder,
        guests,
        payment_method,
        transaction_id=None,
        client_reference=None,
    ):
        raise NotImplementedError


class BookingService:
    def __init__(self, adapter, commission_percent):
        self._adapter = adapter
        self._commission_percent = commission_percent

    def parse_prebook(self, data, agent_commission):
        supplier_price = float(data.get("price") or 0)
        pricing = calculate_agent_price(supplier_price, self._commission_percent)
        extra = round(agent_commission, 2)
        agent_price = round(pricing.agent_price + extra, 2)

        room_types = data.get("roomTypes") or []
        rates = room_types[0].get("rates", []) if room_types else []
        rate = rates[0] if rates else {}

        cancel_policies = rate.get("cancellationPolicies") or {}
        cancel_infos = cancel_policies.get("cancelPolicyInfos") or []
        cancellation_deadline = (
            cancel_infos[0].get("cancelTime") if cancel_infos else None
        )
        refundable = cancel_policies.get("refundableTag") == "RFN"

        retail = rate.get("retailRate", {}).get("total", [{}])
        currency = (
            retail[0].get("currency", data.get("currency", "USD"))
            if retail
            else data.get("currency", "USD")
        )

        agent_view = {
            "prebook_id": data.get("prebookId", ""),
            "hotel_id": data.get("hotelId", ""),
            "check_in": data.get("checkin", ""),
            "check_out": data.get("checkout", ""),
            "currency": data.get("currency", currency),
            "price": agent_price,
            "terms_and_conditions": data.get("termsAndConditions") or "",
            "room": {
                "rate_id": rate.get("rateId", ""),
                "room_name": rate.get("name", ""),
                "board_name": rate.get("boardName", ""),
                "refundable": refundable,
                "cancellation_deadline": cancellation_deadline,
                "price": agent_price,
                "currency": data.get("currency", currency),
            },
            "transaction_id": data.get("transactionId") or None,
            "secret_key": data.get("secretKey") or None,
        }

        internal = {
            "offer_id": data.get("offerId", ""),
            "rate_id": rate.get("rateId", ""),
            "supplier_price": pricing.supplier_price,
            "commission_percent": pricing.commission_percent,
            "commission_amount": pricing.commission_amount,
            "middleware_price": pricing.agent_price,
            "agent_commission": extra,
            "agent_price": agent_price,
            "currency": data.get("currency", currency),
            "prebook_id": data.get("prebookId", ""),
            "transaction_id": data.get("transactionId", ""),
        }

        return agent_view, internal

    async def prebook(
        self,
        offer_id,
        use_payment_sdk,
        agent_commission,
        voucher_code=None,
    ):
        raw = await self._adapter.create_prebook(
            offer_id=offer_id,
            use_payment_sdk=use_payment_sdk,
            voucher_code=voucher_code,
        )

        if not raw.get("prebookId"):
            raise ValueError("Supplier did not return a prebook session")

        return self.parse_prebook(raw, agent_commission)

    def parse_alternative_option(self, data: dict, agent_commission: float) -> dict:
        view, _ = self.parse_prebook(data, agent_commission)
        room = view["room"]
        return {
            "prebook_id": view["prebook_id"],
            "offer_id": data.get("offerId", ""),
            "hotel_id": view["hotel_id"],
            "check_in": view["check_in"],
            "check_out": view["check_out"],
            "currency": view["currency"],
            "price": view["price"],
            "price_difference_percent": float(data.get("priceDifferencePercent") or 0),
            "cancellation_changed": bool(data.get("cancellationChanged")),
            "board_changed": bool(data.get("boardChanged")),
            "room_name": room["room_name"],
            "board_name": room["board_name"],
            "refundable": room["refundable"],
            "cancellation_deadline": room.get("cancellation_deadline"),
        }

    async def alternative_prebooks(
        self,
        supplier_booking_id: str,
        occupancies: list[dict],
        check_in: str,
        check_out: str,
        agent_commission: float,
        refundable_rates_only: bool = False,
        board_type: str | None = None,
    ) -> list[dict]:
        liteapi_occupancies = [
            {
                "adults": occ["adults"],
                "children": occ.get("children") or [],
            }
            for occ in occupancies
        ]

        raw_list = await self._adapter.create_alternative_prebooks(
            supplier_booking_id,
            occupancies=liteapi_occupancies,
            checkin=check_in,
            checkout=check_out,
            refundable_rates_only=refundable_rates_only,
            board_type=board_type,
        )

        return [
            self.parse_alternative_option(item, agent_commission)
            for item in raw_list
            if item.get("prebookId")
        ]

    async def get_prebook(
        self,
        prebook_id: str,
        agent_commission: float,
        include_credit_balance: bool = False,
    ) -> dict:
        raw = await self._adapter.get_prebook(
            prebook_id,
            include_credit_balance=include_credit_balance,
        )

        if not raw.get("prebookId"):
            raise ValueError("Prebook session not found")

        agent_view, _ = self.parse_prebook(raw, agent_commission)

        if include_credit_balance:
            credit = raw.get("creditLine") or {}
            if credit:
                agent_view["credit_line"] = {
                    "remaining_credit": float(credit.get("remainingCredit") or 0),
                    "currency": credit.get("currency", agent_view["currency"]),
                }

        return agent_view

    def parse_list_item(self, item: dict, local=None) -> dict:
        hotel = item.get("hotel") or {}
        holder = item.get("holder") or {}
        rooms = item.get("rooms") or []
        room = rooms[0] if rooms else {}

        guest_name = ""
        if room:
            guest_name = "%s %s" % (
                room.get("firstName", ""),
                room.get("lastName", ""),
            )
            guest_name = guest_name.strip()

        holder_name = "%s %s" % (
            holder.get("firstName", ""),
            holder.get("lastName", ""),
        )
        holder_name = holder_name.strip()

        if local:
            price = local.agent_price
            booking_id = local.id
        else:
            supplier_price = float(item.get("price") or 0)
            pricing = calculate_agent_price(supplier_price, self._commission_percent)
            price = pricing.agent_price
            booking_id = None

        return {
            "booking_id": booking_id,
            "supplier_booking_id": item.get("bookingId", ""),
            "client_reference": item.get("clientReference") or "",
            "prebook_id": item.get("prebookId") or "",
            "status": item.get("status", ""),
            "payment_status": item.get("paymentStatus") or "",
            "hotel_id": hotel.get("hotelId", ""),
            "hotel_name": hotel.get("name", ""),
            "check_in": item.get("checkin", ""),
            "check_out": item.get("checkout", ""),
            "currency": item.get("currency", "USD"),
            "price": price,
            "hotel_confirmation_code": item.get("hotelConfirmationCode") or "",
            "holder_name": holder_name,
            "holder_email": holder.get("email") or item.get("email") or "",
            "guest_name": guest_name,
            "created_at": item.get("createdAt") or None,
        }

    def parse_inventory_item(self, item: dict, local=None) -> dict:
        """Map LiteAPI inventory list shape (GET /bookings, no guest filter)."""
        supplier_booking_id = (
            item.get("bookingId")
            or item.get("booking_Id")
            or item.get("supplier_Booking_Id")
            or ""
        )
        prebook_id = item.get("prebookId") or item.get("prebook_Id") or ""
        client_reference = item.get("clientReference") or item.get("client_reference") or ""
        guest_name = "%s %s" % (item.get("firstName", ""), item.get("lastName", ""))
        guest_name = guest_name.strip()

        if local:
            price = local.agent_price
            booking_id = local.id
        else:
            supplier_price = float(item.get("retail_rate") or item.get("price") or 0)
            pricing = calculate_agent_price(supplier_price, self._commission_percent)
            price = pricing.agent_price
            booking_id = None

        hotel_confirmation = (
            item.get("hotelConfirmationCode")
            or item.get("hotel_confirmation_code")
            or ""
        )

        return {
            "booking_id": booking_id,
            "supplier_booking_id": supplier_booking_id,
            "client_reference": client_reference,
            "prebook_id": prebook_id,
            "status": item.get("status", ""),
            "payment_status": item.get("paymentStatus") or item.get("payment_status") or "",
            "hotel_id": item.get("hotelId") or "",
            "hotel_name": item.get("Hotel_name") or item.get("hotelName") or "",
            "check_in": item.get("checkin", ""),
            "check_out": item.get("checkout", ""),
            "currency": item.get("currency", "USD"),
            "price": price,
            "hotel_confirmation_code": hotel_confirmation,
            "holder_name": guest_name,
            "holder_email": item.get("email") or "",
            "guest_name": guest_name,
            "created_at": item.get("createdAt") or item.get("created_at"),
        }

    def parse_booking_detail(self, item: dict, local=None) -> dict:
        normalized = dict(item)
        if not normalized.get("rooms") and normalized.get("bookedRooms"):
            normalized["rooms"] = [
                {
                    "firstName": br.get("firstName", ""),
                    "lastName": br.get("lastName", ""),
                }
                for br in normalized["bookedRooms"]
            ]

        detail = self.parse_list_item(normalized, local=local)

        booked_rooms = item.get("bookedRooms") or []
        room = booked_rooms[0] if booked_rooms else {}
        room_type = room.get("roomType") or {}
        rate = room.get("rate") or {}

        cancel = rate.get("cancellationPolicies") or item.get("cancellationPolicies") or {}
        cancel_infos = cancel.get("cancelPolicyInfos") or []
        cancellation_deadline = (
            cancel_infos[0].get("cancelTime") if cancel_infos else None
        )
        refundable = cancel.get("refundableTag") == "RFN"

        holder = item.get("holder") or {}

        detail.update(
            {
                "holder_phone": holder.get("phone") or "",
                "room_name": room_type.get("name", ""),
                "board_name": room.get("boardName") or rate.get("boardName", ""),
                "refundable": refundable,
                "cancellation_deadline": cancellation_deadline,
                "updated_at": item.get("updatedAt") or None,
            }
        )
        return detail

    async def get_booking(self, supplier_booking_id: str) -> dict:
        raw = await self._adapter.get_booking(supplier_booking_id)

        if not raw.get("bookingId"):
            raise ValueError("Booking not found")

        return raw

    @staticmethod
    def parse_cancel(data: dict, local=None) -> dict:
        return {
            "booking_id": local.id if local else None,
            "supplier_booking_id": data.get("bookingId", ""),
            "status": data.get("status", ""),
            "cancellation_fee": float(data.get("cancellation_fee") or 0),
            "refund_amount": float(data.get("refund_amount") or 0),
            "currency": data.get("currency", "USD"),
        }

    async def cancel(
        self,
        supplier_booking_id: str,
        local=None,
        timeout: float | None = None,
    ) -> dict:
        raw = await self._adapter.cancel_booking(
            supplier_booking_id,
            timeout=timeout,
        )

        if not raw.get("bookingId"):
            raise ValueError("Supplier did not cancel the booking")

        return self.parse_cancel(raw, local=local)

    @staticmethod
    def _liteapi_amend_holder(holder: dict) -> dict:
        payload = {
            "firstName": holder["first_name"],
            "lastName": holder["last_name"],
            "email": holder["email"],
        }
        if holder.get("phone"):
            payload["phone"] = holder["phone"]
        return payload

    @staticmethod
    def parse_amend(data: dict, local=None) -> dict:
        return {
            "booking_id": local.id if local else None,
            "supplier_booking_id": data.get("bookingId", ""),
            "amendment_id": data.get("id"),
            "status": data.get("status", ""),
            "holder_first_name": data.get("holderFirstName", ""),
            "holder_last_name": data.get("holderLastName", ""),
            "holder_email": data.get("holderEmail", ""),
            "remarks": data.get("remarks") or "",
        }

    async def amend_holder(
        self,
        supplier_booking_id: str,
        holder: dict,
        remarks: str | None = None,
        local=None,
    ) -> dict:
        raw = await self._adapter.amend_guest_name(
            supplier_booking_id,
            holder=self._liteapi_amend_holder(holder),
            remarks=remarks,
        )

        if not raw.get("bookingId"):
            raise ValueError("Supplier did not accept the amendment")

        return self.parse_amend(raw, local=local)

    async def list_bookings(
        self,
        guest_id: str | None = None,
        client_reference: str | None = None,
        timeout: float | None = None,
    ) -> list[dict]:
        if not guest_id and not client_reference:
            raise ValueError("guest_id or client_reference is required")

        return await self._adapter.list_bookings(
            guest_id=guest_id,
            client_reference=client_reference,
            timeout=timeout,
        )

    async def list_all_bookings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        booking_start_date: str | None = None,
        booking_end_date: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        timeout: float | None = None,
    ) -> tuple[int, list[dict]]:
        return await self._adapter.list_all_bookings(
            start_date=start_date,
            end_date=end_date,
            booking_start_date=booking_start_date,
            booking_end_date=booking_end_date,
            status=status,
            payment_status=payment_status,
            timeout=timeout,
        )

    @staticmethod
    def _liteapi_holder(holder):
        return {
            "firstName": holder["first_name"],
            "lastName": holder["last_name"],
            "email": holder["email"],
            "phone": holder.get("phone") or "0000000000",
        }

    @staticmethod
    def _liteapi_guests(guests):
        return [
            {
                "occupancyNumber": g.get("occupancy_number", 1),
                "firstName": g["first_name"],
                "lastName": g["last_name"],
                "email": g["email"],
                "phone": g.get("phone") or "0000000000",
            }
            for g in guests
        ]

    @staticmethod
    def parse_confirm(data, booking, holder):
        hotel = data.get("hotel") or {}
        booked_rooms = data.get("bookedRooms") or []
        room = booked_rooms[0] if booked_rooms else {}

        guest_name = "%s %s" % (holder["first_name"], holder["last_name"])

        return {
            "booking_id": booking.id,
            "supplier_booking_id": data.get("bookingId", ""),
            "status": data.get("status", "CONFIRMED"),
            "hotel_id": hotel.get("hotelId", getattr(booking, "hotel_id", "")),
            "hotel_name": hotel.get("name", ""),
            "check_in": data.get("checkin", ""),
            "check_out": data.get("checkout", ""),
            "currency": data.get("currency", getattr(booking, "currency", "")),
            "price": getattr(booking, "agent_price", 0),
            "hotel_confirmation_code": data.get("hotelConfirmationCode") or "",
            "room_name": room.get("roomType", {}).get("name", ""),
            "board_name": room.get("boardName", ""),
            "guest_name": guest_name.strip(),
        }

    async def confirm(
        self,
        booking,
        holder,
        guests,
        payment_method,
        client_reference=None,
    ):
        if getattr(booking, "status", None) != "prebooked":
            raise ValueError("Booking is already %s" % getattr(booking, "status", ""))

        if not getattr(booking, "prebook_id", None):
            raise ValueError("Booking has no prebook session")

        tx_id = getattr(booking, "transaction_id", None) if payment_method == "TRANSACTION" else None
        ref = client_reference or getattr(booking, "id", "")

        raw = await self._adapter.confirm_booking(
            prebook_id=getattr(booking, "prebook_id", None),
            holder=self._liteapi_holder(holder),
            guests=self._liteapi_guests(guests),
            payment_method=payment_method,
            transaction_id=tx_id or None,
            client_reference=ref,
        )

        if not raw.get("bookingId"):
            raise ValueError("Supplier did not confirm the booking")

        return self.parse_confirm(raw, booking, holder)
