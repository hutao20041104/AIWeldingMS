import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone

from core.models import SoftDeleteModel


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class User(AbstractUser, SoftDeleteModel):

    # remove useless fields
    first_name = None
    last_name = None
    date_joined = None

    # User Roles
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="User ID")
    identity_code = models.CharField(max_length=18, verbose_name="User Identity Code")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name="User Role")
    avatar = models.ImageField(upload_to='avatars/%Y/%m/%d/', null=True, blank=True, verbose_name="User Avatar")
    tel = models.CharField(max_length=11, null=True, blank=True, verbose_name="User Phone Number")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="User Creation Time")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="User Update Time")

    objects = ActiveUserManager()
    all_objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['identity_code'],
                condition=(
                    models.Q(deleted_at__isnull=True)
                    & ~models.Q(identity_code__exact='')
                ),
                name='users_identity_number_unique_when_active',
            )
        ]

    def __str__(self):
        return f'{self.username} - {self.role}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()


class Teacher(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")

    class Meta:
        db_table = 'teachers'


class Student(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    major = models.CharField(max_length=16, verbose_name="Student Major")

    class Meta:
        db_table = 'students'
