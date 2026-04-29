from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
        ("devices", "0002_device_start_time_end_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="assistant_student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assistant_courses",
                to="users.student",
                verbose_name="课程助教",
            ),
        ),
        migrations.CreateModel(
            name="CourseGroupAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_assignments",
                        to="courses.course",
                    ),
                ),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_assignments",
                        to="devices.device",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_assignments",
                        to="users.student",
                    ),
                ),
            ],
            options={
                "verbose_name": "课程分组",
                "verbose_name_plural": "课程分组",
                "db_table": "course_group_assignments",
            },
        ),
        migrations.AddConstraint(
            model_name="coursegroupassignment",
            constraint=models.UniqueConstraint(fields=("course", "student"), name="uniq_course_group_student"),
        ),
    ]
