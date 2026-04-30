from ninja import NinjaAPI

from apps.users.api import router as auth_router
from apps.students.api import router as students_router
from apps.devices.api import router as devices_router
from apps.courses.api import router as courses_router
from apps.users.assistant_api import assistant_router

api = NinjaAPI(
    title="AI Welding Server API", 
    version="1.0.0",
)
api.add_router("/auth/", auth_router)
api.add_router("/students/", students_router)
api.add_router("/devices/", devices_router)
api.add_router("/courses/", courses_router)
api.add_router("/assistant/", assistant_router)
