from uuid import uuid4

from django.db import models

from apps.agents.models import Agent


class Supplier(models.Model):
    """Supplier config — commission % is applied in middleware, not shown to agents."""

    name = models.CharField(max_length=50, unique=True, help_text="e.g. liteapi")
    display_name = models.CharField(max_length=100)
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Markup % added to supplier price (e.g. 3.00 = 3%)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers"

    def __str__(self):
        return f"{self.display_name} ({self.commission_percent}%)"


class Booking(models.Model):
    """Internal booking record with full price breakdown (not shown to agents)."""

    class Status(models.TextChoices):
        PREBOOKED = "prebooked", "Prebooked"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name="bookings")
    supplier_name = models.CharField(max_length=50)
    supplier_booking_id = models.CharField(max_length=200, blank=True)
    prebook_id = models.CharField(max_length=100, blank=True, db_index=True)
    transaction_id = models.CharField(max_length=200, blank=True)

    hotel_id = models.CharField(max_length=50)
    rate_id = models.CharField(max_length=500)
    offer_id = models.CharField(max_length=500)

    supplier_price = models.DecimalField(max_digits=12, decimal_places=2)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    middleware_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Supplier price + platform commission (before agent markup)",
    )
    agent_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Extra commission the agent added",
    )
    agent_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final price charged to the agent (middleware + agent commission)",
    )
    currency = models.CharField(max_length=3, default="USD")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREBOOKED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agent.company_name} — {self.hotel_id} ({self.status})"
