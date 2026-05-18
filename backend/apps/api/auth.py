from typing import Optional, Tuple

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from ninja.security import APIKeyHeader

from apps.agents.models import Agent, AgentApiKey


class AgentApiKeyAuth(APIKeyHeader):
    param_name = "Authorization"

    def authenticate(self, request, key: str) -> Optional[Tuple[Agent, AgentApiKey]]:
        if key.startswith("ApiKey "):
            key = key[7:]
        elif key.startswith("Bearer "):
            key = key[7:]

        try:
            api_key_obj = AgentApiKey.objects.select_related("agent").get(
                key=key,
                is_active=True,
                expires_at__gt=timezone.now(),
            )
        except AgentApiKey.DoesNotExist:
            return None

        if not api_key_obj.agent.is_active:
            return None

        api_key_obj.last_used_at = timezone.now()
        api_key_obj.save(update_fields=["last_used_at"])

        request.agent_rate_limit = api_key_obj.rate_limit
        request.agent_id = str(api_key_obj.agent.id)

        return api_key_obj.agent, api_key_obj


class AgentLoginAuth:
    @staticmethod
    def authenticate(email: str, password: str, request=None) -> Optional[dict]:
        user = authenticate(request, username=email, password=password)

        if not user:
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                return None

        if not user:
            return None

        try:
            agent = user.agent
        except Agent.DoesNotExist:
            return None

        if not agent.is_active:
            return None

        api_key_obj = AgentApiKey.objects.filter(
            agent=agent,
            is_active=True,
            expires_at__gt=timezone.now(),
        ).first()

        if not api_key_obj:
            api_key_obj = AgentApiKey.objects.create(
                agent=agent,
                name=f"Default Key - {timezone.now().date()}",
                rate_limit=100,
            )

        return {
            "agent_id": str(agent.id),
            "agent_name": agent.company_name,
            "email": user.email,
            "api_key": api_key_obj.key,
            "expires_at": api_key_obj.expires_at.isoformat(),
            "rate_limit": api_key_obj.rate_limit,
        }


api_key_auth = AgentApiKeyAuth()
