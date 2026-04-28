import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class User(AbstractUser):

    # remove useless fields
    first_name = None
    last_name = None
    date_joined = None

    # User Roles
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    identity_code = models.CharField(max_length=18, verbose_name="工号", unique=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name="角色")
    is_approved = models.BooleanField(default=True, verbose_name="审核状态")
    avatar = models.ImageField(upload_to='avatars/%Y/%m/%d/', null=True, blank=True, verbose_name="头像")
    tel = models.CharField(max_length=11, null=True, blank=True, verbose_name="手机号")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'users'
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username} - {self.role}'


class Teacher(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")

    class Meta:
        db_table = 'teachers'


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    major = models.CharField(max_length=64, blank=True, default="", verbose_name="专业")
    major_code = models.CharField(max_length=32, blank=True, default="", verbose_name="专业代码")
    class_code = models.CharField(max_length=32, blank=True, default="", verbose_name="班级代码")
    class_name = models.CharField(max_length=64, blank=True, default="", verbose_name="班级")

    class Meta:
        db_table = 'students'


class MajorCatalog(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name="专业")
    code = models.CharField(max_length=32, unique=True, verbose_name="专业代码")

    class Meta:
        db_table = "major_catalogs"
        verbose_name = "专业字典"
        verbose_name_plural = "专业字典"

    def __str__(self):
        return f"{self.name}({self.code})"


class ClassCatalog(models.Model):
    name = models.CharField(max_length=64, verbose_name="班级")
    code = models.CharField(max_length=32, unique=True, verbose_name="班级代码")
    major = models.ForeignKey(
        MajorCatalog,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="classes",
        verbose_name="所属专业",
    )

    class Meta:
        db_table = "class_catalogs"
        verbose_name = "班级字典"
        verbose_name_plural = "班级字典"

    def __str__(self):
        return f"{self.name}({self.code})"


class MajorClassManagement(MajorCatalog):
    class Meta:
        proxy = True
        verbose_name = "专业班级管理"
        verbose_name_plural = "专业班级管理"


class BlacklistedToken(models.Model):
    token_id = models.UUIDField(unique=True, verbose_name="JWT Token ID")
    token_type = models.CharField(max_length=16, verbose_name="Token Type")
    expires_at = models.DateTimeField(verbose_name="Expiration Time")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        db_table = "blacklisted_tokens"
        verbose_name = "Blacklisted Token"
        verbose_name_plural = "Blacklisted Tokens"

    def __str__(self):
        return f"{self.token_type}:{self.token_id}"
