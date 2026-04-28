from ninja import NinjaAPI

from apps.users.api import router as auth_router

api = NinjaAPI(
    title="AI Welding Server API", 
    version="1.0.0",
)
api.add_router("/auth/", auth_router)
