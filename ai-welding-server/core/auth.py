import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

from apps.users.models import BlacklistedToken

User = get_user_model()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _jwt_secret():
    return settings.SECRET_KEY


def _jwt_algorithm():
    return getattr(settings, "JWT_ALGORITHM", "HS256")


def _access_expire_seconds():
    return int(getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_SECONDS", 3600))


def _refresh_expire_seconds():
    return int(getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_SECONDS", 604800))


def _build_payload(user_id, token_type, expire_seconds):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=expire_seconds)
    return {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }


def create_access_token(user_id):
    payload = _build_payload(user_id, ACCESS_TOKEN_TYPE, _access_expire_seconds())
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def create_refresh_token(user_id):
    payload = _build_payload(user_id, REFRESH_TOKEN_TYPE, _refresh_expire_seconds())
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_token(token):
    return jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])


def blacklist_token(payload):
    token_id = payload.get("jti")
    token_type = payload.get("type", "")
    exp = payload.get("exp")
    if not token_id or not exp:
        return

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    BlacklistedToken.objects.get_or_create(
        token_id=token_id,
        defaults={"token_type": token_type, "expires_at": expires_at},
    )


def is_token_blacklisted(payload):
    token_id = payload.get("jti")
    if not token_id:
        return True
    return BlacklistedToken.objects.filter(token_id=token_id).exists()


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            return None

        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        if is_token_blacklisted(payload):
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None
        return user
