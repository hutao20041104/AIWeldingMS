from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="start_time",
            field=models.DateTimeField(blank=True, null=True, verbose_name="开始时间"),
        ),
        migrations.AddField(
            model_name="device",
            name="end_time",
            field=models.DateTimeField(blank=True, null=True, verbose_name="结束时间"),
        ),
    ]
