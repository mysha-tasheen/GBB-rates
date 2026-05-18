from django.contrib import admin

from apps.core.models import Booking, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("display_name", "name", "commission_percent", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "display_name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "agent",
        "prebook_id",
        "hotel_id",
        "agent_price",
        "agent_commission",
        "commission_amount",
        "supplier_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "supplier_name")
    search_fields = ("hotel_id", "supplier_booking_id", "agent__company_name")
    readonly_fields = ("created_at", "updated_at")
