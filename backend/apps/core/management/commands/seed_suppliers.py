from django.core.management.base import BaseCommand

from apps.core.models import Supplier


class Command(BaseCommand):
    help = "Seed default supplier commission rates (run after migrate)"

    def handle(self, *args, **options):
        supplier, created = Supplier.objects.update_or_create(
            name="liteapi",
            defaults={
                "display_name": "Nuitee / LiteAPI",
                "commission_percent": "3.00",
                "is_active": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {supplier.display_name} — {supplier.commission_percent}% commission"
            )
        )
