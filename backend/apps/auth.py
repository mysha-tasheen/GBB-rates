from ninja.security import HttpApiKey, HttpBearer
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Optional, Tuple
from apps.agents.models import AgentApiKey, Agent

class AgentApiKeyAuth(HttpApiKey):
    
    
    param_name = "Authorization"
    openapi_scheme = "ApiKey"
    
    def authenticate(self, request, key: str) -> Optional[Tuple[Agent, AgentApiKey]]:
        
        # Remove 'ApiKey ' prefix if present
        if key.startswith('ApiKey '):
            key = key[7:]
        elif key.startswith('Bearer '):
            key = key[7:]
        
        try:
            # Find the API key
            api_key_obj = AgentApiKey.objects.select_related('agent').get(
                key=key,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            
            # Check if agent is active
            if not api_key_obj.agent.is_active:
                return None
            
            # Update last used time
            api_key_obj.last_used_at = timezone.now()
            api_key_obj.save(update_fields=['last_used_at'])
            
            # Store rate limit in request for middleware
            request.agent_rate_limit = api_key_obj.rate_limit
            request.agent_id = str(api_key_obj.agent.id)
            
            # Return agent and api_key object
            return (api_key_obj.agent, api_key_obj)
            
        except AgentApiKey.DoesNotExist:
            return None


class AgentLoginAuth:
    
    
    @staticmethod
    def authenticate(email: str, password: str, request=None) -> Optional[dict]:
        from django.contrib.auth import authenticate
        
        # Try to authenticate
        user = authenticate(request, username=email, password=password)
        
        if not user:
            # Try with email as username
            try:
                from django.contrib.auth.models import User
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                return None
        
        if not user:
            return None
        
        # Check if user has an agent profile
        try:
            agent = user.agent
        except:
            return None
        
        if not agent.is_active:
            return None
        
        # Get or create API key
        api_key_obj = AgentApiKey.objects.filter(
            agent=agent,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if not api_key_obj:
            api_key_obj = AgentApiKey.objects.create(
                agent=agent,
                name=f"Default Key - {timezone.now().date()}",
                rate_limit=100
            )
        
        return {
            'agent_id': str(agent.id),
            'agent_name': agent.company_name,
            'email': user.email,
            'api_key': api_key_obj.key,
            'expires_at': api_key_obj.expires_at.isoformat(),
            'rate_limit': api_key_obj.rate_limit
        }