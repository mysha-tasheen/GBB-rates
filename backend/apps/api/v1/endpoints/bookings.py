from ninja import Router
from apps.api.v1.endpoints.alternative_prebooks import router as alternative_prebooks_router
from apps.api.v1.endpoints.amend_guest import router as amend_guest_router
from apps.api.v1.endpoints.cancel_booking import router as cancel_booking_router
from apps.api.v1.endpoints.confirm_booking import router as confirm_booking_router
from apps.api.v1.endpoints.create_prebook import router as create_prebook_router
from apps.api.v1.endpoints.get_booking import router as get_booking_router
from apps.api.v1.endpoints.list_bookings import router as list_bookings_router

router = Router(tags=["bookings"])


router.add_router("", create_prebook_router)
router.add_router("", list_bookings_router)
router.add_router("", confirm_booking_router)
router.add_router("", alternative_prebooks_router)
router.add_router("", amend_guest_router)
router.add_router("", get_booking_router)
router.add_router("", cancel_booking_router)
