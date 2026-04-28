from django.contrib.auth.backends import BaseBackend

from .models import User


class IdentityCodeBackend(BaseBackend):
    """自定义认证后端,通过idetity-code+password认证用户"""

    def authenticate(self, request, identity_code=None, password=None, **kwargs):

        if not identity_code or not password:
            return None

        try:
            user = User.objects.get(identity_code=identity_code)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None
