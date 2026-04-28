from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Device",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_code", models.CharField(max_length=32, unique=True, verbose_name="设备编号")),
                (
                    "status",
                    models.CharField(
                        choices=[("in_use", "使用中"), ("idle", "空闲"), ("maintaining", "维护中")],
                        max_length=16,
                        verbose_name="状态",
                    ),
                ),
                ("classroom", models.CharField(max_length=64, verbose_name="教室")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "设备",
                "verbose_name_plural": "设备",
                "db_table": "devices",
                "ordering": ["device_code"],
            },
        ),
    ]
