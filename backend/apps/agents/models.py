import secrets
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Agent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agent")
    company_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agents"

    def __str__(self):
        return self.company_name


class AgentApiKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=100, unique=True, editable=False)
    name = models.CharField(max_length=100, default="Default Key")
    rate_limit = models.IntegerField(default=100)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_api_keys"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = f"b2b_live_{secrets.token_urlsafe(32)}"
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=90)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.agent.company_name}"
