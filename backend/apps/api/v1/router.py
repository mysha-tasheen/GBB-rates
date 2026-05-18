from ninja import Router

from apps.api.v1.endpoints.auth import router as auth_router
from apps.api.v1.endpoints.me import router as me_router

v1_router = Router()
v1_router.add_router("", auth_router)
v1_router.add_router("", me_router)
