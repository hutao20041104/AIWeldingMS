from django.db import models


class Device(models.Model):
    STATUS_IN_USE = "in_use"
    STATUS_IDLE = "idle"
    STATUS_MAINTAINING = "maintaining"

    STATUS_CHOICES = [
        (STATUS_IN_USE, "使用中"),
        (STATUS_IDLE, "空闲"),
        (STATUS_MAINTAINING, "维护中"),
    ]

    device_code = models.CharField(max_length=32, unique=True, verbose_name="设备编号")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, verbose_name="状态")
    classroom = models.CharField(max_length=64, verbose_name="教室")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "devices"
        verbose_name = "设备"
        verbose_name_plural = "设备"
        ordering = ["device_code"]

    def __str__(self):
        return self.device_code
