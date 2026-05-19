import logging
from typing import Optional, Tuple

from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from ninja.security import APIKeyHeader

from apps.agents.models import Agent, AgentApiKey

logger = logging.getLogger(__name__)


class AgentApiKeyAuth(APIKeyHeader):
    param_name = "Authorization"

    async def authenticate(
        self, request, key: str
    ) -> Optional[Tuple[Agent, AgentApiKey]]:
        return await sync_to_async(self._authenticate_sync, thread_sensitive=True)(
            request, key
        )

    def _authenticate_sync(
        self, request, key: str
    ) -> Optional[Tuple[Agent, AgentApiKey]]:
        if not key:
            return None
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
    def _resolve_user(email: str, password: str, request=None) -> Optional[User]:
        email = (email or "").strip()
        if not email or not password:
            return None

        candidates: list[User] = []
        try:
            candidates.append(User.objects.get(email__iexact=email))
        except User.DoesNotExist:
            pass

        if not candidates:
            try:
                candidates.append(User.objects.get(username=email))
            except User.DoesNotExist:
                return None

        for user_obj in candidates:
            user = authenticate(
                request, username=user_obj.username, password=password
            )
            if user:
                return user
            if user_obj.check_password(password) and user_obj.is_active:
                return user_obj

        return None

    @staticmethod
    def authenticate(email: str, password: str, request=None) -> Optional[dict]:
        user = AgentLoginAuth._resolve_user(email, password, request)
        if not user:
            logger.info("Login failed for email=%s", (email or "").strip())
            return None

        try:
            agent = user.agent
        except Agent.DoesNotExist:
            logger.warning("Login user has no agent profile: %s", user.email)
            return None

        if not agent.is_active:
            logger.warning("Login agent inactive: %s", user.email)
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
