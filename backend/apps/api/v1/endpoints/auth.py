from ninja import Router
from pydantic import BaseModel

from apps.api.auth import AgentLoginAuth

router = Router(tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    agent_id: str
    agent_name: str
    email: str
    api_key: str
    expires_at: str
    rate_limit: int


@router.post("/auth/login", auth=None, response={200: LoginResponse, 401: dict})
def login(request, payload: LoginRequest):
    result = AgentLoginAuth.authenticate(
        payload.email.strip(),
        payload.password,
        request,
    )
    if not result:
        return 401, {"detail": "Invalid credentials"}
    return result
