import json
import uuid
import datetime
from django.utils import timezone
from langchain_core.tools import tool
from apps.courses.models import Course, CourseStudent
from apps.users.models import Student, Teacher
from apps.devices.models import Device
from conf_agent.settings import logger

@tool
def manage_course_tool(action: str, start_time: str = "", end_time: str = "", classroom: str = "", target_class_or_major: str = "", course_code: str = "") -> str:
    """
    排课（创建课程）或删课（删除课程）的工具。
    action: "create" (排课/创建课程) 或 "delete" (删课/取消课程)
    start_time: 课程开始时间，ISO格式 (如 "2026-05-01T10:00:00+08:00")，创建时必填。
    end_time: 课程结束时间，ISO格式，创建时必填。
    classroom: 教室地点 (如 "实训室301")，创建时必填。
    target_class_or_major: 上课的班级或专业名 (如 "机电1班")，创建时必填。
    course_code: 课程编号，删除时必填。
    """
    logger.info(f"Using manage_course_tool: action={action}")
    
    if action == "delete":
        if not course_code:
            return "删除课程失败：必须提供 course_code。"
        try:
            course = Course.objects.get(course_code=course_code)
            course.delete()
            return f"成功删除了课程: {course_code}"
        except Course.DoesNotExist:
            return f"找不到课程编号为 {course_code} 的课程，删除失败。"

    elif action == "create":
        if not start_time or not end_time or not classroom or not target_class_or_major:
            return "创建课程失败：必须提供 start_time, end_time, classroom 和 target_class_or_major。"

        # 找一个老师 (默认找第一个)
        teacher = Teacher.objects.first()
        if not teacher:
            return "系统内没有教师信息，无法创建课程。"

        # 解析时间
        try:
            st = datetime.datetime.fromisoformat(start_time)
            et = datetime.datetime.fromisoformat(end_time)
        except ValueError:
            return "时间格式不正确，需要是标准的 ISO 8601 格式。"
            
        # 校验地点是否存在
        existing_classrooms = set(Device.objects.values_list('classroom', flat=True).distinct())
        if classroom not in existing_classrooms:
            valid_list = ', '.join(filter(bool, existing_classrooms))
            return f"创建课程中止：系统中不存在地点 '{classroom}'。当前系统允许的地点有: {valid_list}。"

        # 校验是否有时间重叠的课程
        from django.db.models import Q
        overlapping_courses = Course.objects.filter(
            classroom=classroom,
            start_time__lt=et,
            end_time__gt=st
        )
        if overlapping_courses.exists():
            conflict = overlapping_courses.first()
            return f"创建课程中止：在所选时间段内，地点 '{classroom}' 已被课程 '{conflict.course_code}' 占用（{conflict.start_time.strftime('%Y-%m-%d %H:%M')} 至 {conflict.end_time.strftime('%Y-%m-%d %H:%M')}）。请选择其他时间或地点。"

        # 生成自动编号
        new_course_code = f"C{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # 查找目标班级学生
        students = Student.objects.filter(class_name__icontains=target_class_or_major)
        if not students.exists():
            students = Student.objects.filter(major__icontains=target_class_or_major)

        if not students.exists():
            return f"创建课程中止：未找到班级或专业名为 '{target_class_or_major}' 的学生。"

        # 创建课程
        course = Course.objects.create(
            course_code=new_course_code,
            teacher=teacher,
            classroom=classroom,
            start_time=st,
            end_time=et
        )

        # 批量绑定学生
        course_students = [
            CourseStudent(course=course, student=student)
            for student in students
        ]
        CourseStudent.objects.bulk_create(course_students)

        return f"课程创建成功！\n课程编号: {new_course_code}\n地点: {classroom}\n上课人数: {len(course_students)}\n请将这些信息以人类友好的方式告知用户。"
    else:
        return f"未知的 action: {action}"

@tool
def query_course_tool(start_time_gte: str = "", start_time_lte: str = "", course_code: str = "") -> str:
    """
    查询课程表的工具。可以根据时间范围或课程编号来查询安排的课程。
    start_time_gte: 查询在该时间之后开始的课程 (ISO格式，如 "2026-05-01T00:00:00+08:00")
    start_time_lte: 查询在该时间之前开始的课程 (ISO格式，如 "2026-05-07T23:59:59+08:00")
    course_code: 若提供，则进行精确编号查询。
    注意：在回答用户“我下周有课吗”、“我今天的课表”时，务必根据当前系统时间计算出准确的 start_time_gte 和 start_time_lte 传入！
    """
    logger.info(f"Using query_course_tool: gte={start_time_gte}, lte={start_time_lte}, code={course_code}")
    
    queryset = Course.objects.all().select_related("teacher__user").prefetch_related("students")
    
    if course_code:
        queryset = queryset.filter(course_code=course_code)
    else:
        if start_time_gte:
            try:
                st = datetime.datetime.fromisoformat(start_time_gte)
                queryset = queryset.filter(start_time__gte=st)
            except ValueError:
                pass
        if start_time_lte:
            try:
                et = datetime.datetime.fromisoformat(start_time_lte)
                queryset = queryset.filter(start_time__lte=et)
            except ValueError:
                pass

    records = list(queryset)
    if not records:
        return "在此查询条件下未找到任何课程安排。"
        
    data_list = []
    for r in records:
        data_list.append({
            "course_code": r.course_code,
            "teacher_name": r.teacher.user.username if hasattr(r.teacher, 'user') else str(r.teacher.id),
            "classroom": r.classroom,
            "start_time": r.start_time.isoformat(),
            "end_time": r.end_time.isoformat(),
            "student_count": r.students.count(),
            "status": r.status
        })
        
    return "查询到以下课程数据，请根据这些数据为您的人类用户做出专业清晰的解答：\n" + json.dumps(data_list, ensure_ascii=False, indent=2)
