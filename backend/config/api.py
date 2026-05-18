from ninja import NinjaAPI

from apps.api.auth import api_key_auth
from apps.api.v1.router import v1_router

api = NinjaAPI(
    title="GBB Rates API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    auth=api_key_auth,
)

api.add_router("/v1", v1_router)
