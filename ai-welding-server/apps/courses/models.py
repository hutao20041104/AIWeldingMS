from django.db import models
from django.utils import timezone

from apps.users.models import Student, Teacher


class Course(models.Model):
    course_code = models.CharField(max_length=32, unique=True, verbose_name="课程编号")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="courses", verbose_name="授课教师")
    assistant_student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_courses",
        verbose_name="课程助教",
    )
    classroom = models.CharField(max_length=64, verbose_name="授课地点")
    start_time = models.DateTimeField(verbose_name="授课开始时间")
    end_time = models.DateTimeField(verbose_name="授课结束时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    students = models.ManyToManyField(Student, through="CourseStudent", related_name="courses", verbose_name="上课学生")

    class Meta:
        db_table = "courses"
        verbose_name = "课程"
        verbose_name_plural = "课程"
        ordering = ["-created_at"]

    def __str__(self):
        return self.course_code

    @property
    def status(self) -> str:
        now = timezone.now()
        if now < self.start_time:
            return "not_started"
        if now > self.end_time:
            return "ended"
        return "in_progress"


class CourseStudent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_students")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="student_courses")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "course_students"
        verbose_name = "课程学生关联"
        verbose_name_plural = "课程学生关联"
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="uniq_course_student"),
        ]


class CourseGroupAssignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="group_assignments")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="group_assignments")
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE, related_name="group_assignments")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "course_group_assignments"
        verbose_name = "课程分组"
        verbose_name_plural = "课程分组"
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="uniq_course_group_student"),
        ]


class DeviceTelemetry(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="telemetry_records", verbose_name="课程")
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE, related_name="telemetry_records", verbose_name="设备")
    current = models.FloatField(verbose_name="电流(A)")
    voltage = models.FloatField(verbose_name="电压(V)")
    wire_feed_speed = models.FloatField(verbose_name="送丝速度")
    recorded_at = models.DateTimeField(db_index=True, verbose_name="记录时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "device_telemetry_records"
        verbose_name = "设备遥测记录"
        verbose_name_plural = "设备遥测记录"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["course", "device", "-recorded_at"], name="idx_telemetry_course_dev_time"),
            models.Index(fields=["course", "-recorded_at"], name="idx_telemetry_course_time"),
        ]
