import logging
import random
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone
from ninja import Router, Schema

from apps.courses.models import Course, CourseGroupAssignment, CourseStudent
from apps.devices.models import Device
from apps.users.models import ClassCatalog, MajorCatalog, Student, Teacher
from core.auth import JWTAuth

router = Router(tags=["courses"])
logger = logging.getLogger(__name__)


class StudentLiteOut(Schema):
    id: str
    identity_code: str
    username: str
    major: str
    major_code: str
    class_code: str
    class_name: str


class DeviceLiteOut(Schema):
    id: int
    device_code: str
    status: str
    status_label: str


class ClassroomOut(Schema):
    classroom: str
    devices: list[DeviceLiteOut]


class CourseOut(Schema):
    id: int
    course_code: str
    classroom: str
    class_display: str
    status: str
    status_label: str
    start_time: str
    end_time: str
    created_at: str
    student_count: int
    assistant_student_id: Optional[str] = None
    assistant_student_name: Optional[str] = None


class CourseDetailOut(CourseOut):
    student_ids: list[str]


class CourseSaveIn(Schema):
    classroom: str
    start_time: str
    end_time: str
    student_ids: list[str]
    assistant_student_id: Optional[str] = None


class GroupAssignmentIn(Schema):
    student_id: str
    device_id: int


class GroupSaveIn(Schema):
    assignments: list[GroupAssignmentIn]


STATUS_LABELS = {
    "not_started": "未开始",
    "in_progress": "进行中",
    "ended": "结束",
}


def _teacher_profile_or_none(user) -> Optional[Teacher]:
    return Teacher.objects.filter(user=user).first()


def _parse_dt_or_raise(text: str) -> datetime:
    value = (text or "").strip()
    if not value:
        raise ValueError("授课时间不能为空")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("授课时间格式错误，请使用 ISO 格式") from exc
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _next_course_code() -> str:
    prefix = timezone.localdate().strftime("COURSE%Y%m%d")
    last_item = Course.objects.filter(course_code__startswith=prefix).order_by("-course_code").first()
    if not last_item:
        return f"{prefix}001"
    try:
        seq = int(last_item.course_code[-3:]) + 1
    except ValueError:
        seq = 1
    return f"{prefix}{seq:03d}"


def _status_of(course: Course) -> str:
    return course.status


def _class_display_of(course: Course) -> str:
    majors = list(
        course.students.exclude(major__exact="")
        .order_by("major")
        .values_list("major", flat=True)
        .distinct()
    )
    if majors:
        return "、".join(majors)
    class_names = list(
        course.students.exclude(class_name__exact="")
        .order_by("class_name")
        .values_list("class_name", flat=True)
        .distinct()
    )
    return "、".join(class_names) if class_names else "-"


def _serialize_course(course: Course) -> dict:
    status = _status_of(course)
    return {
        "id": course.id,
        "course_code": course.course_code,
        "classroom": course.classroom,
        "class_display": _class_display_of(course),
        "status": status,
        "status_label": STATUS_LABELS[status],
        "start_time": course.start_time.isoformat(),
        "end_time": course.end_time.isoformat(),
        "created_at": course.created_at.isoformat(),
        "student_count": course.students.count(),
        "assistant_student_id": str(course.assistant_student_id) if course.assistant_student_id else None,
        "assistant_student_name": course.assistant_student.user.username if course.assistant_student_id else None,
    }


def _can_manage_grouping(course: Course, user) -> bool:
    if user.role == "teacher" and course.teacher.user_id == user.id:
        return True
    if user.role == "student" and course.assistant_student and course.assistant_student.user_id == user.id:
        return True
    return False


def _validate_grouping_or_raise(course: Course, assignments: list[tuple[str, int]]) -> None:
    enrolled_student_ids = set(str(x) for x in course.students.values_list("id", flat=True))
    if not enrolled_student_ids:
        raise ValueError("课程没有学生，无法分组")

    classroom_devices = {
        d.id: d for d in Device.objects.filter(classroom=course.classroom).order_by("device_code")
    }
    if not classroom_devices:
        raise ValueError("该课程所在教室没有设备，无法分组")

    if len(classroom_devices) * 3 < len(enrolled_student_ids):
        raise ValueError("设备数量不足，无法完成本次分组")

    assignment_students = [sid for sid, _ in assignments]
    if len(set(assignment_students)) != len(assignment_students):
        raise ValueError("学生分配重复，请检查分组结果")
    if set(assignment_students) != enrolled_student_ids:
        raise ValueError("需要为所有学生完成设备分配")

    per_device: dict[int, int] = {}
    for sid, did in assignments:
        if sid not in enrolled_student_ids:
            raise ValueError("存在不属于该课程的学生")
        if did not in classroom_devices:
            raise ValueError("存在不属于该教室的设备")
        per_device[did] = per_device.get(did, 0) + 1
        if per_device[did] > 3:
            raise ValueError("单台设备最多分配 3 名学生")


def _save_grouping(course: Course, assignments: list[tuple[str, int]]) -> None:
    _validate_grouping_or_raise(course, assignments)
    student_map = {str(s.id): s for s in Student.objects.filter(id__in=[sid for sid, _ in assignments])}
    device_map = {d.id: d for d in Device.objects.filter(id__in=[did for _, did in assignments])}
    with transaction.atomic():
        CourseGroupAssignment.objects.filter(course=course).delete()
        CourseGroupAssignment.objects.bulk_create(
            [
                CourseGroupAssignment(
                    course=course,
                    student=student_map[sid],
                    device=device_map[did],
                )
                for sid, did in assignments
            ]
        )


@router.get("/students/", auth=JWTAuth(), response={200: list[StudentLiteOut], 403: dict})
def list_course_students(
    request,
    class_code: Optional[str] = None,
    major_code: Optional[str] = None,
    name: Optional[str] = None,
):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查询学生"}

    qs = Student.objects.select_related("user").filter(user__role="student")
    if class_code:
        qs = qs.filter(class_code__icontains=class_code.strip())
    if major_code:
        qs = qs.filter(major_code__icontains=major_code.strip())
    if name:
        qs = qs.filter(user__username__icontains=name.strip())

    return [
        {
            "id": str(item.id),
            "identity_code": item.user.identity_code,
            "username": item.user.username,
            "major": item.major,
            "major_code": item.major_code,
            "class_code": item.class_code,
            "class_name": item.class_name,
        }
        for item in qs.order_by("major_code", "class_code", "user__username")
    ]


@router.get("/options/", auth=JWTAuth(), response={200: dict, 403: dict})
def course_options(request):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查看课程配置"}

    majors = [{"name": item.name, "code": item.code} for item in MajorCatalog.objects.order_by("code")]
    classes = [
        {"name": item.name, "code": item.code, "major_code": item.major.code if item.major else ""}
        for item in ClassCatalog.objects.select_related("major").order_by("code")
    ]
    classrooms = []
    for room in Device.objects.exclude(classroom__exact="").values_list("classroom", flat=True).distinct().order_by("classroom"):
        devices = Device.objects.filter(classroom=room).order_by("device_code")
        classrooms.append(
            {
                "classroom": room,
                "devices": [
                    {
                        "id": d.id,
                        "device_code": d.device_code,
                        "status": d.status,
                        "status_label": d.get_status_display(),
                    }
                    for d in devices
                ],
            }
        )
    return {"majors": majors, "classes": classes, "classrooms": classrooms}


@router.get("/next-code/", auth=JWTAuth(), response={200: dict, 403: dict})
def next_course_code(request):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查看课程编号"}
    return {"course_code": _next_course_code()}


@router.get("", auth=JWTAuth(), response={200: list[CourseOut], 403: dict})
def list_courses(request):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查看课程"}
    teacher = _teacher_profile_or_none(request.auth)
    if not teacher:
        return []
    qs = Course.objects.filter(teacher=teacher).prefetch_related("students").order_by("-created_at")
    return [_serialize_course(item) for item in qs]


@router.get("/{course_id}/", auth=JWTAuth(), response={200: CourseDetailOut, 403: dict, 404: dict})
def get_course(request, course_id: int):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查看课程"}
    teacher = _teacher_profile_or_none(request.auth)
    course = Course.objects.filter(id=course_id, teacher=teacher).prefetch_related("students").first()
    if not course:
        return 404, {"message": "课程不存在"}
    payload = _serialize_course(course)
    payload["student_ids"] = [str(sid) for sid in course.students.values_list("id", flat=True)]
    return payload


@router.post("", auth=JWTAuth(), response={201: CourseDetailOut, 400: dict, 403: dict})
def create_course(request, payload: CourseSaveIn):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可创建课程"}
    teacher = _teacher_profile_or_none(request.auth)
    if not teacher:
        return 403, {"message": "教师信息不存在"}
    if not payload.student_ids:
        return 400, {"message": "请至少选择一名学生"}

    try:
        start_time = _parse_dt_or_raise(payload.start_time)
        end_time = _parse_dt_or_raise(payload.end_time)
    except ValueError as exc:
        return 400, {"message": str(exc)}
    if start_time >= end_time:
        return 400, {"message": "授课开始时间必须早于结束时间"}

    students = list(Student.objects.filter(id__in=payload.student_ids))
    if len(students) != len(set(payload.student_ids)):
        return 400, {"message": "存在无效学生，请重新选择"}
    assistant_student = None
    if payload.assistant_student_id:
        assistant_student = next((s for s in students if str(s.id) == payload.assistant_student_id), None)
        if assistant_student is None:
            return 400, {"message": "助教必须是该课程已选学生"}

    with transaction.atomic():
        course = Course.objects.create(
            course_code=_next_course_code(),
            teacher=teacher,
            classroom=payload.classroom.strip(),
            start_time=start_time,
            end_time=end_time,
            assistant_student=assistant_student,
        )
        CourseStudent.objects.bulk_create([CourseStudent(course=course, student=s) for s in students])

    course = Course.objects.prefetch_related("students").get(id=course.id)
    data = _serialize_course(course)
    data["student_ids"] = [str(sid) for sid in course.students.values_list("id", flat=True)]
    return 201, data


@router.put("/{course_id}/", auth=JWTAuth(), response={200: CourseDetailOut, 400: dict, 403: dict, 404: dict})
def update_course(request, course_id: int, payload: CourseSaveIn):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可编辑课程"}
    teacher = _teacher_profile_or_none(request.auth)
    course = Course.objects.filter(id=course_id, teacher=teacher).prefetch_related("students").first()
    if not course:
        return 404, {"message": "课程不存在"}
    if _status_of(course) != "not_started":
        return 400, {"message": "仅未开始课程可编辑"}
    if not payload.student_ids:
        return 400, {"message": "请至少选择一名学生"}

    try:
        start_time = _parse_dt_or_raise(payload.start_time)
        end_time = _parse_dt_or_raise(payload.end_time)
    except ValueError as exc:
        return 400, {"message": str(exc)}
    if start_time >= end_time:
        return 400, {"message": "授课开始时间必须早于结束时间"}

    students = list(Student.objects.filter(id__in=payload.student_ids))
    if len(students) != len(set(payload.student_ids)):
        return 400, {"message": "存在无效学生，请重新选择"}
    assistant_student = None
    if payload.assistant_student_id:
        assistant_student = next((s for s in students if str(s.id) == payload.assistant_student_id), None)
        if assistant_student is None:
            return 400, {"message": "助教必须是该课程已选学生"}

    with transaction.atomic():
        course.classroom = payload.classroom.strip()
        course.start_time = start_time
        course.end_time = end_time
        course.assistant_student = assistant_student
        course.save(update_fields=["classroom", "start_time", "end_time", "assistant_student", "updated_at"])
        CourseStudent.objects.filter(course=course).delete()
        CourseStudent.objects.bulk_create([CourseStudent(course=course, student=s) for s in students])
        CourseGroupAssignment.objects.filter(course=course).delete()

    course.refresh_from_db()
    course = Course.objects.prefetch_related("students").get(id=course.id)
    data = _serialize_course(course)
    data["student_ids"] = [str(sid) for sid in course.students.values_list("id", flat=True)]
    return data


@router.delete("/{course_id}/", auth=JWTAuth(), response={200: dict, 400: dict, 403: dict, 404: dict})
def delete_course(request, course_id: int):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可删除课程"}
    teacher = _teacher_profile_or_none(request.auth)
    course = Course.objects.filter(id=course_id, teacher=teacher).first()
    if not course:
        return 404, {"message": "课程不存在"}
    if _status_of(course) == "ended":
        return 400, {"message": "已结束课程不可删除"}
    course.delete()
    return {"message": "删除成功"}


@router.get("/{course_id}/grouping/", auth=JWTAuth(), response={200: dict, 403: dict, 404: dict})
def get_grouping(request, course_id: int):
    teacher = _teacher_profile_or_none(request.auth) if request.auth.role == "teacher" else None
    if request.auth.role == "teacher":
        course = Course.objects.filter(id=course_id, teacher=teacher).first()
    else:
        course = Course.objects.filter(id=course_id).first()
    if not course:
        return 404, {"message": "课程不存在"}
    if not _can_manage_grouping(course, request.auth):
        return 403, {"message": "无分组管理权限"}

    students = list(course.students.select_related("user").order_by("major", "class_name", "user__username"))
    devices = list(Device.objects.filter(classroom=course.classroom).order_by("device_code"))
    existing = {
        str(item.student_id): item.device_id
        for item in CourseGroupAssignment.objects.filter(course=course)
    }
    return {
        "course_id": course.id,
        "course_code": course.course_code,
        "classroom": course.classroom,
        "assistant_student_id": str(course.assistant_student_id) if course.assistant_student_id else None,
        "assistant_student_name": course.assistant_student.user.username if course.assistant_student_id else None,
        "can_manage": True,
        "students": [
            {
                "id": str(s.id),
                "identity_code": s.user.identity_code,
                "username": s.user.username,
                "major": s.major,
                "class_name": s.class_name,
                "device_id": existing.get(str(s.id)),
            }
            for s in students
        ],
        "devices": [
            {
                "id": d.id,
                "device_code": d.device_code,
                "status": d.status,
                "status_label": d.get_status_display(),
            }
            for d in devices
        ],
    }


@router.post("/{course_id}/grouping/random/", auth=JWTAuth(), response={200: dict, 400: dict, 403: dict, 404: dict})
def random_grouping(request, course_id: int):
    teacher = _teacher_profile_or_none(request.auth) if request.auth.role == "teacher" else None
    if request.auth.role == "teacher":
        course = Course.objects.filter(id=course_id, teacher=teacher).first()
    else:
        course = Course.objects.filter(id=course_id).first()
    if not course:
        return 404, {"message": "课程不存在"}
    if not _can_manage_grouping(course, request.auth):
        return 403, {"message": "无分组管理权限"}

    students = list(course.students.values_list("id", flat=True))
    devices = list(Device.objects.filter(classroom=course.classroom).order_by("device_code").values_list("id", flat=True))
    if len(devices) * 3 < len(students):
        return 400, {"message": "设备数量不足，无法完成本次分组"}
    random.shuffle(students)
    assignments: list[tuple[str, int]] = []
    for idx, sid in enumerate(students):
        device_id = devices[idx // 3]
        assignments.append((str(sid), int(device_id)))
    try:
        _save_grouping(course, assignments)
    except ValueError as exc:
        return 400, {"message": str(exc)}
    return {"message": "随机分组成功"}


@router.put("/{course_id}/grouping/", auth=JWTAuth(), response={200: dict, 400: dict, 403: dict, 404: dict})
def save_grouping(request, course_id: int, payload: GroupSaveIn):
    teacher = _teacher_profile_or_none(request.auth) if request.auth.role == "teacher" else None
    if request.auth.role == "teacher":
        course = Course.objects.filter(id=course_id, teacher=teacher).first()
    else:
        course = Course.objects.filter(id=course_id).first()
    if not course:
        return 404, {"message": "课程不存在"}
    if not _can_manage_grouping(course, request.auth):
        return 403, {"message": "无分组管理权限"}
    assignments = [(item.student_id, item.device_id) for item in payload.assignments]
    try:
        _save_grouping(course, assignments)
    except ValueError as exc:
        return 400, {"message": str(exc)}
    return {"message": "分组保存成功"}


@router.get("/monitor/current/", auth=JWTAuth(), response={200: dict, 403: dict})
def current_monitor(request):
    if request.auth.role != "teacher":
        return 403, {"message": "仅教师可查看实验监控"}
    teacher = _teacher_profile_or_none(request.auth)
    if not teacher:
        return {"has_active_course": False}

    now = timezone.now()
    course = (
        Course.objects.filter(teacher=teacher, start_time__lte=now, end_time__gte=now)
        .select_related("assistant_student__user")
        .order_by("-start_time")
        .first()
    )
    if not course:
        return {"has_active_course": False}

    devices = list(Device.objects.filter(classroom=course.classroom).order_by("device_code"))
    assignments = list(
        CourseGroupAssignment.objects.filter(course=course)
        .select_related("student__user", "device")
        .order_by("device__device_code", "student__user__username")
    )
    grouped: dict[int, list[dict]] = {}
    for item in assignments:
        grouped.setdefault(item.device_id, []).append(
            {
                "student_id": str(item.student_id),
                "identity_code": item.student.user.identity_code,
                "username": item.student.user.username,
                "major": item.student.major,
                "class_name": item.student.class_name,
            }
        )

    return {
        "has_active_course": True,
        "course": {
            "id": course.id,
            "course_code": course.course_code,
            "classroom": course.classroom,
            "start_time": course.start_time.isoformat(),
            "end_time": course.end_time.isoformat(),
            "assistant_student_name": course.assistant_student.user.username if course.assistant_student_id else None,
            "student_count": course.students.count(),
        },
        "devices": [
            {
                "id": d.id,
                "device_code": d.device_code,
                "status": d.status,
                "status_label": d.get_status_display(),
                "students": grouped.get(d.id, []),
                "seat_usage": f"{len(grouped.get(d.id, []))}/3",
            }
            for d in devices
        ],
    }
