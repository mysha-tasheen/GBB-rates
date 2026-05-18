from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.agents.models import Agent, AgentApiKey


class Command(BaseCommand):
    help = "Create a new agent user"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--company", required=True)
        parser.add_argument("--phone", required=True)

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        company = options["company"]
        phone = options["phone"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=company,
        )

        agent = Agent.objects.create(
            user=user,
            company_name=company,
            phone=phone,
            is_active=True,
        )

        api_key = AgentApiKey.objects.create(
            agent=agent,
            name="Production Key",
            rate_limit=100,
        )

        self.stdout.write(self.style.SUCCESS("Agent created successfully!"))
        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write(f"API Key: {api_key.key}")
