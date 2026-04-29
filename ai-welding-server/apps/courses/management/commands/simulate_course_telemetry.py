import random
import time
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.courses.models import Course, DeviceTelemetry
from apps.devices.models import Device


class Command(BaseCommand):
    help = "模拟一节课内多台设备并发写入电流/电压/送丝速度遥测数据。"
    DURATION_MIN = 45
    INTERVAL_SEC = 1
    RNG_SEED = 2026

    def _resolve_course(self) -> Course:
        now = timezone.now()
        active_course = Course.objects.filter(start_time__lte=now, end_time__gte=now).order_by("-start_time").first()
        if active_course:
            return active_course
        latest_course = Course.objects.order_by("-created_at").first()
        if latest_course:
            return latest_course
        raise CommandError("没有可用课程，请先创建课程")

    def handle(self, *args, **options):
        random.seed(self.RNG_SEED)

        course = self._resolve_course()
        devices_qs = Device.objects.filter(classroom=course.classroom).order_by("device_code")
        devices = list(devices_qs)
        if not devices:
            raise CommandError(f"课程教室 {course.classroom} 无设备，无法模拟")

        duration_min = self.DURATION_MIN
        interval_sec = self.INTERVAL_SEC
        end_at = timezone.now() + timedelta(minutes=duration_min)

        self.stdout.write(
            self.style.SUCCESS(
                f"开始模拟 telemetry: course={course.course_code}, classroom={course.classroom}, "
                f"devices={len(devices)}, duration={duration_min}min, interval={interval_sec}s"
            )
        )

        base_current = {d.id: random.uniform(65, 90) for d in devices}
        base_voltage = {d.id: random.uniform(20, 31) for d in devices}
        base_wire = {d.id: random.uniform(6.0, 10.0) for d in devices}

        written = 0
        batch: list[DeviceTelemetry] = []
        while timezone.now() < end_at:
            now = timezone.now()
            for d in devices:
                base_current[d.id] += random.uniform(-2.8, 2.8)
                base_voltage[d.id] += random.uniform(-0.9, 0.9)
                base_wire[d.id] += random.uniform(-0.45, 0.45)

                current = max(40.0, min(130.0, base_current[d.id]))
                voltage = max(16.0, min(40.0, base_voltage[d.id]))
                wire = max(3.0, min(14.0, base_wire[d.id]))

                batch.append(
                    DeviceTelemetry(
                        course=course,
                        device=d,
                        current=round(current, 2),
                        voltage=round(voltage, 2),
                        wire_feed_speed=round(wire, 2),
                        recorded_at=now,
                    )
                )
            DeviceTelemetry.objects.bulk_create(batch, batch_size=1000)
            written += len(batch)
            batch.clear()
            self.stdout.write(f"[{now.strftime('%H:%M:%S')}] 已写入 {written} 条")
            time.sleep(interval_sec)

        self.stdout.write(self.style.SUCCESS(f"模拟完成，总写入 {written} 条遥测数据。"))
