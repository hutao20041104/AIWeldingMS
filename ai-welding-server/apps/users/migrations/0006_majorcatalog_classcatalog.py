from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_student_profile_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="MajorCatalog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True, verbose_name="专业")),
                ("code", models.CharField(max_length=32, unique=True, verbose_name="专业代码")),
            ],
            options={
                "verbose_name": "专业字典",
                "verbose_name_plural": "专业字典",
                "db_table": "major_catalogs",
            },
        ),
        migrations.CreateModel(
            name="ClassCatalog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, verbose_name="班级")),
                ("code", models.CharField(max_length=32, unique=True, verbose_name="班级代码")),
                (
                    "major",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="classes",
                        to="users.majorcatalog",
                        verbose_name="所属专业",
                    ),
                ),
            ],
            options={
                "verbose_name": "班级字典",
                "verbose_name_plural": "班级字典",
                "db_table": "class_catalogs",
            },
        ),
    ]
