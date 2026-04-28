from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_is_approved"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="major",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="专业"),
        ),
        migrations.AddField(
            model_name="student",
            name="major_code",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="专业代码"),
        ),
        migrations.AddField(
            model_name="student",
            name="class_code",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="班级代码"),
        ),
        migrations.AddField(
            model_name="student",
            name="class_name",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="班级"),
        ),
    ]
