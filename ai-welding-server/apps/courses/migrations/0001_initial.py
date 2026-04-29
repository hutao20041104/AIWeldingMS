from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0006_majorcatalog_classcatalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("course_code", models.CharField(max_length=32, unique=True, verbose_name="课程编号")),
                ("classroom", models.CharField(max_length=64, verbose_name="授课地点")),
                ("start_time", models.DateTimeField(verbose_name="授课开始时间")),
                ("end_time", models.DateTimeField(verbose_name="授课结束时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses",
                        to="users.teacher",
                        verbose_name="授课教师",
                    ),
                ),
            ],
            options={
                "verbose_name": "课程",
                "verbose_name_plural": "课程",
                "db_table": "courses",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CourseStudent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_students",
                        to="courses.course",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_courses",
                        to="users.student",
                    ),
                ),
            ],
            options={
                "verbose_name": "课程学生关联",
                "verbose_name_plural": "课程学生关联",
                "db_table": "course_students",
            },
        ),
        migrations.AddField(
            model_name="course",
            name="students",
            field=models.ManyToManyField(
                related_name="courses", through="courses.CourseStudent", to="users.student", verbose_name="上课学生"
            ),
        ),
        migrations.AddConstraint(
            model_name="coursestudent",
            constraint=models.UniqueConstraint(fields=("course", "student"), name="uniq_course_student"),
        ),
    ]
