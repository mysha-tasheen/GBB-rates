# Pure Python Rewrite (no type hints, pure value types, no typing module)
from apps.core.domain.booking import Booking
from apps.core.domain.prebook import AgentPrebook, PrebookInternal, PrebookRoom
from apps.core.ports.booking import BookingSupplierPort
from apps.core.repositories.booking import BookingRepository
from apps.core.services.commission_service import CommissionService

class BookingService:

    def __init__(self, supplier, commissions, bookings):
        self._supplier = supplier
        self._commissions = commissions
        self._bookings = bookings

    def save_prebook(self, agent_id, agent, internal):
        return self._bookings.create_prebook(agent_id, agent, internal)

    def get_local_for_agent(self, agent_id, booking_id=None, prebook_id=None):
        return self._bookings.get_for_agent(agent_id, booking_id, prebook_id)

    def find_local_by_prebook(self, agent_id, prebook_id):
        return self._bookings.find_by_prebook_for_agent(agent_id, prebook_id)

    def find_local_by_reference(self, agent_id, reference):
        return self._bookings.find_by_reference_for_agent(agent_id, reference)

    def find_local_for_supplier_item(self, agent_id, item):
        return self._bookings.find_for_supplier_item(agent_id, item)

    def mark_confirmed(self, booking_id, supplier_booking_id):
        self._bookings.mark_confirmed(booking_id, supplier_booking_id)

    def mark_failed(self, booking_id):
        self._bookings.mark_failed(booking_id)

    def mark_cancelled(self, booking_id):
        self._bookings.mark_cancelled(booking_id)

    def resolve_supplier_reference(self, agent_id, reference):
        local = self.find_local_by_reference(agent_id, reference)
        if local and local.supplier_booking_id:
            return (local.supplier_booking_id, local)
        if local:
            raise ValueError("Booking is not yet confirmed with the supplier")
        return (reference, None)

    def parse_prebook(self, data, agent_commission):
        supplier_price = float(data.get("price") or 0)
        pricing = self._commissions.agent_price_breakdown(
            supplier_price, agent_flat_commission=agent_commission
        )
        agent_price = pricing.agent_price

        room_types = data.get("roomTypes") or []
        rates = room_types[0].get("rates", []) if room_types else []
        rate = rates[0] if rates else {}

        cancel_policies = rate.get("cancellationPolicies") or {}
        cancel_infos = cancel_policies.get("cancelPolicyInfos") or []
        if cancel_infos:
            cancellation_deadline = cancel_infos[0].get("cancelTime")
        else:
            cancellation_deadline = None
        refundable = (cancel_policies.get("refundableTag") == "RFN")

        retail = rate.get("retailRate", {}).get("total", [{}])
        if retail:
            currency = retail[0].get("currency", data.get("currency", "USD"))
        else:
            currency = data.get("currency", "USD")

        room = PrebookRoom(
            rate_id=rate.get("rateId", ""),
            room_name=rate.get("name", ""),
            board_name=rate.get("boardName", ""),
            refundable=refundable,
            cancellation_deadline=cancellation_deadline,
            price=agent_price,
            currency=data.get("currency", currency),
        )

        agent = AgentPrebook(
            prebook_id=data.get("prebookId", ""),
            hotel_id=data.get("hotelId", ""),
            check_in=data.get("checkin", ""),
            check_out=data.get("checkout", ""),
            currency=data.get("currency", currency),
            price=agent_price,
            terms_and_conditions=data.get("termsAndConditions") or "",
            room=room,
            transaction_id=data.get("transactionId") or None,
            secret_key=data.get("secretKey") or None,
        )

        internal = PrebookInternal(
            offer_id=data.get("offerId", ""),
            rate_id=rate.get("rateId", ""),
            supplier_price=pricing.supplier_price,
            commission_percent=pricing.commission_percent,
            commission_amount=pricing.commission_amount,
            middleware_price=pricing.middleware_price,
            agent_commission=pricing.agent_commission,
            agent_price=agent_price,
            currency=data.get("currency", currency),
            prebook_id=data.get("prebookId", ""),
            transaction_id=data.get("transactionId", "") or "",
        )

        return agent, internal

    def _agent_price(self, supplier_price, local=None):
        if local:
            return (local.agent_price, local.id)
        return (self._commissions.middleware_price(supplier_price).agent_price, None)

    async def prebook(self, offer_id, use_payment_sdk, agent_commission, voucher_code=None):
        raw = await self._supplier.create_prebook(
            offer_id=offer_id,
            use_payment_sdk=use_payment_sdk,
            voucher_code=voucher_code,
        )
        if not raw.get("prebookId"):
            raise ValueError("Supplier did not return a prebook session")
        return self.parse_prebook(raw, agent_commission)

    async def get_prebook(self, prebook_id, agent_commission, include_credit_balance=False):
        raw = await self._supplier.get_prebook(
            prebook_id,
            include_credit_balance=include_credit_balance,
        )
        if not raw.get("prebookId"):
            raise ValueError("Prebook session not found")
        agent, _ = self.parse_prebook(raw, agent_commission)
        if include_credit_balance:
            credit = raw.get("creditLine") or {}
            if credit:
                return AgentPrebook(
                    prebook_id=agent.prebook_id,
                    hotel_id=agent.hotel_id,
                    check_in=agent.check_in,
                    check_out=agent.check_out,
                    currency=agent.currency,
                    price=agent.price,
                    terms_and_conditions=agent.terms_and_conditions,
                    room=agent.room,
                    transaction_id=agent.transaction_id,
                    secret_key=agent.secret_key,
                    credit_line={
                        "remaining_credit": float(credit.get("remainingCredit") or 0),
                        "currency": credit.get("currency", agent.currency),
                    },
                )
        return agent

    async def get_booking(self, supplier_booking_id):
        raw = await self._supplier.get_booking(supplier_booking_id)
        if not raw.get("bookingId"):
            raise ValueError("Booking not found")
        return raw

    async def confirm(self, booking, holder, guests, payment_method, client_reference=None):
        if not booking.is_prebooked:
            raise ValueError("Booking is already %s" % booking.status)
        if not booking.prebook_id:
            raise ValueError("Booking has no prebook session")

        if payment_method == "TRANSACTION":
            tx_id = booking.transaction_id
        else:
            tx_id = None
        ref = client_reference or booking.id

        raw = await self._supplier.confirm_booking(
            prebook_id=booking.prebook_id,
            holder=self._liteapi_holder(holder),
            guests=self._liteapi_guests(guests),
            payment_method=payment_method,
            transaction_id=tx_id or None,
            client_reference=ref,
        )
        if not raw.get("bookingId"):
            raise ValueError("Supplier did not confirm the booking")
        return self.parse_confirm(raw, booking, holder)

    async def cancel(self, supplier_booking_id, local=None, timeout=None):
        raw = await self._supplier.cancel_booking(supplier_booking_id, timeout=timeout)
        if not raw.get("bookingId"):
            raise ValueError("Supplier did not cancel the booking")
        return self.parse_cancel(raw, local)

    async def amend_holder(self, supplier_booking_id, holder, remarks=None, local=None):
        raw = await self._supplier.amend_guest_name(
            supplier_booking_id,
            holder=self._liteapi_amend_holder(holder),
            remarks=remarks,
        )
        if not raw.get("bookingId"):
            raise ValueError("Supplier did not accept the amendment")
        return self.parse_amend(raw, local)

    async def alternative_prebooks(
        self,
        supplier_booking_id,
        occupancies,
        check_in,
        check_out,
        agent_commission,
        refundable_rates_only=False,
        board_type=None,
    ):
        liteapi_occupancies = []
        for occ in occupancies:
            liteapi_occupancies.append({
                "adults": occ["adults"],
                "children": occ.get("children") or []
            })
        raw_list = await self._supplier.create_alternative_prebooks(
            supplier_booking_id,
            occupancies=liteapi_occupancies,
            checkin=check_in,
            checkout=check_out,
            refundable_rates_only=refundable_rates_only,
            board_type=board_type,
        )
        result = []
        for item in raw_list:
            if item.get("prebookId"):
                result.append(self.parse_alternative_option(item, agent_commission))
        return result

    async def list_bookings(self, guest_id=None, client_reference=None, timeout=None):
        if not guest_id and not client_reference:
            raise ValueError("guest_id or client_reference is required")
        return await self._supplier.list_bookings(
            guest_id=guest_id,
            client_reference=client_reference,
            timeout=timeout,
        )

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
        return await self._supplier.list_all_bookings(
            start_date=start_date,
            end_date=end_date,
            booking_start_date=booking_start_date,
            booking_end_date=booking_end_date,
            status=status,
            payment_status=payment_status,
            timeout=timeout,
        )

    def parse_list_item(self, item, local=None):
        hotel = item.get("hotel") or {}
        holder = item.get("holder") or {}
        rooms = item.get("rooms") or []
        if rooms:
            room = rooms[0]
        else:
            room = {}

        guest_name = ("%s %s" % (room.get('firstName', ''), room.get('lastName', ''))).strip()
        holder_name = ("%s %s" % (holder.get('firstName', ''), holder.get('lastName', ''))).strip()

        supplier_price = float(item.get("price") or 0)
        price, booking_id = self._agent_price(supplier_price, local)

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

    def parse_inventory_item(self, item, local=None):
        supplier_booking_id = (
            item.get("bookingId")
            or item.get("booking_Id")
            or item.get("supplier_Booking_Id")
            or ""
        )
        guest_name = ("%s %s" % (item.get('firstName', ''), item.get('lastName', ''))).strip()
        supplier_price = float(item.get("retail_rate") or item.get("price") or 0)
        price, booking_id = self._agent_price(supplier_price, local)

        return {
            "booking_id": booking_id,
            "supplier_booking_id": supplier_booking_id,
            "client_reference": item.get("clientReference") or item.get("client_reference") or "",
            "prebook_id": item.get("prebookId") or item.get("prebook_Id") or "",
            "status": item.get("status", ""),
            "payment_status": item.get("paymentStatus") or item.get("payment_status") or "",
            "hotel_id": item.get("hotelId") or "",
            "hotel_name": item.get("Hotel_name") or item.get("hotelName") or "",
            "check_in": item.get("checkin", ""),
            "check_out": item.get("checkout", ""),
            "currency": item.get("currency", "USD"),
            "price": price,
            "hotel_confirmation_code": (
                item.get("hotelConfirmationCode") or item.get("hotel_confirmation_code") or ""
            ),
            "holder_name": guest_name,
            "holder_email": item.get("email") or "",
            "guest_name": guest_name,
            "created_at": item.get("createdAt") or item.get("created_at"),
        }

    def parse_booking_detail(self, item, local=None):
        normalized = dict(item)
        if not normalized.get("rooms") and normalized.get("bookedRooms"):
            normalized["rooms"] = []
            for br in normalized["bookedRooms"]:
                normalized["rooms"].append(
                    {
                        "firstName": br.get("firstName", ""),
                        "lastName": br.get("lastName", ""),
                    }
                )

        detail = self.parse_list_item(normalized, local=local)
        booked_rooms = item.get("bookedRooms") or []
        if booked_rooms:
            room = booked_rooms[0]
        else:
            room = {}
        room_type = room.get("roomType") or {}
        rate = room.get("rate") or {}

        cancel = rate.get("cancellationPolicies") or item.get("cancellationPolicies") or {}
        cancel_infos = cancel.get("cancelPolicyInfos") or []
        if cancel_infos:
            cancellation_deadline = cancel_infos[0].get("cancelTime")
        else:
            cancellation_deadline = None
        holder = item.get("holder") or {}

        detail.update(
            {
                "holder_phone": holder.get("phone") or "",
                "room_name": room_type.get("name", ""),
                "board_name": room.get("boardName") or rate.get("boardName", ""),
                "refundable": (cancel.get("refundableTag") == "RFN"),
                "cancellation_deadline": cancellation_deadline,
                "updated_at": item.get("updatedAt") or None,
            }
        )
        return detail

    def parse_alternative_option(self, data, agent_commission):
        agent, _ = self.parse_prebook(data, agent_commission)
        view = agent.to_agent_dict()
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

    @staticmethod
    def parse_cancel(data, local=None):
        return {
            "booking_id": local.id if local else None,
            "supplier_booking_id": data.get("bookingId", ""),
            "status": data.get("status", ""),
            "cancellation_fee": float(data.get("cancellation_fee") or 0),
            "refund_amount": float(data.get("refund_amount") or 0),
            "currency": data.get("currency", "USD"),
        }

    @staticmethod
    def parse_amend(data, local=None):
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

    @staticmethod
    def parse_confirm(data, booking, holder):
        hotel = data.get("hotel") or {}
        booked_rooms = data.get("bookedRooms") or []
        if booked_rooms:
            room = booked_rooms[0]
        else:
            room = {}
        guest_name = ("%s %s" % (holder['first_name'], holder['last_name'])).strip()

        return {
            "booking_id": booking.id,
            "supplier_booking_id": data.get("bookingId", ""),
            "status": data.get("status", "CONFIRMED"),
            "hotel_id": hotel.get("hotelId", booking.hotel_id),
            "hotel_name": hotel.get("name", ""),
            "check_in": data.get("checkin", ""),
            "check_out": data.get("checkout", ""),
            "currency": data.get("currency", booking.currency),
            "price": booking.agent_price,
            "hotel_confirmation_code": data.get("hotelConfirmationCode") or "",
            "room_name": room.get("roomType", {}).get("name", ""),
            "board_name": room.get("boardName", ""),
            "guest_name": guest_name,
        }

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
        result = []
        for g in guests:
            result.append({
                "occupancyNumber": g.get("occupancy_number", 1),
                "firstName": g["first_name"],
                "lastName": g["last_name"],
                "email": g["email"],
                "phone": g.get("phone") or "0000000000",
            })
        return result

    @staticmethod
    def _liteapi_amend_holder(holder):
        payload = {
            "firstName": holder["first_name"],
            "lastName": holder["last_name"],
            "email": holder["email"],
        }
        if holder.get("phone"):
            payload["phone"] = holder["phone"]
        return payload
