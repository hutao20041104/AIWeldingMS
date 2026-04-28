import logging
from typing import Optional

from ninja import Router, Schema

from apps.devices.models import Device
from core.auth import JWTAuth

router = Router(tags=["devices"])
logger = logging.getLogger(__name__)


class DeviceOut(Schema):
    id: int
    device_code: str
    status: str
    status_label: str
    classroom: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@router.get("", auth=JWTAuth(), response={200: list[DeviceOut], 403: dict})
def list_devices(
    request,
    device_code: Optional[str] = None,
    status: Optional[str] = None,
    classroom: Optional[str] = None,
):
    if request.auth.role != "teacher":
        logger.warning("List devices forbidden user_id=%s role=%s", getattr(request.auth, "id", None), request.auth.role)
        return 403, {"message": "仅教师可查看设备信息"}

    logger.info(
        "List devices requested user_id=%s filters(device_code=%s, status=%s, classroom=%s)",
        getattr(request.auth, "id", None),
        device_code,
        status,
        classroom,
    )
    queryset = Device.objects.all()
    if device_code:
        queryset = queryset.filter(device_code__icontains=device_code.strip())
    if status:
        queryset = queryset.filter(status=status.strip())
    if classroom:
        queryset = queryset.filter(classroom__icontains=classroom.strip())

    return [
        {
            "id": item.id,
            "device_code": item.device_code,
            "status": item.status,
            "status_label": item.get_status_display(),
            "classroom": item.classroom,
            "start_time": item.start_time.isoformat() if item.start_time else None,
            "end_time": item.end_time.isoformat() if item.end_time else None,
        }
        for item in queryset
    ]
