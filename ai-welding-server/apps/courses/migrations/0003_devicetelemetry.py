from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0002_course_assistant_and_grouping"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceTelemetry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current", models.FloatField(verbose_name="电流(A)")),
                ("voltage", models.FloatField(verbose_name="电压(V)")),
                ("wire_feed_speed", models.FloatField(verbose_name="送丝速度")),
                ("recorded_at", models.DateTimeField(db_index=True, verbose_name="记录时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telemetry_records",
                        to="courses.course",
                        verbose_name="课程",
                    ),
                ),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telemetry_records",
                        to="devices.device",
                        verbose_name="设备",
                    ),
                ),
            ],
            options={
                "verbose_name": "设备遥测记录",
                "verbose_name_plural": "设备遥测记录",
                "db_table": "device_telemetry_records",
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.AddIndex(
            model_name="devicetelemetry",
            index=models.Index(fields=["course", "device", "-recorded_at"], name="idx_telemetry_course_dev_time"),
        ),
        migrations.AddIndex(
            model_name="devicetelemetry",
            index=models.Index(fields=["course", "-recorded_at"], name="idx_telemetry_course_time"),
        ),
    ]
