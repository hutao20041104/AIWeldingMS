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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="User ID")
    identity_code = models.CharField(max_length=18, verbose_name="User Identity Code", unique=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name="User Role")
    avatar = models.ImageField(upload_to='avatars/%Y/%m/%d/', null=True, blank=True, verbose_name="User Avatar")
    tel = models.CharField(max_length=11, null=True, blank=True, verbose_name="User Phone Number")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="User Creation Time")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="User Update Time")

    class Meta:
        db_table = 'users'
        verbose_name = "User"
        verbose_name_plural = "Users"
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
    major = models.CharField(max_length=16, verbose_name="Student Major")

    class Meta:
        db_table = 'students'


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
