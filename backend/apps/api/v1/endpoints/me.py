from ninja import Router
from apps.api.auth import api_key_auth

router = Router(tags=["auth"])


@router.get("/me", auth=api_key_auth)
async def me(request):
    agent, api_key = request.auth
    return {
        "agent_id": str(agent.id),
        "company_name": agent.company_name,
        "api_key_name": api_key.name,
        "rate_limit": api_key.rate_limit,
    }
