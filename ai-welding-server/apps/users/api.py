import logging
from typing import Optional

import jwt
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from ninja import File, Router, Schema, UploadedFile

from apps.users.models import Teacher
from core.auth import (
    JWTAuth,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = Router(tags=["auth"])
User = get_user_model()
logger = logging.getLogger(__name__)


class LoginIn(Schema):
    identity_code: str
    password: str


class RefreshIn(Schema):
    refresh_token: str


class LogoutIn(Schema):
    refresh_token: Optional[str] = None


class TeacherRegisterIn(Schema):
    identity_code: str
    username: str
    password: str
    tel: Optional[str] = None


class UserOut(Schema):
    id: str
    identity_code: str
    username: str
    email: Optional[str] = None
    role: str
    is_approved: bool
    avatar: Optional[str] = None
    tel: Optional[str] = None


class ProfileUpdateIn(Schema):
    username: str
    email: Optional[str] = None
    tel: Optional[str] = None


class TokenPairOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class LoginOut(Schema):
    user: UserOut
    tokens: TokenPairOut


def _user_payload(user):
    avatar_url = user.avatar.url if user.avatar else None
    return {
        "id": str(user.id),
        "identity_code": user.identity_code,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_approved": user.is_approved,
        "avatar": avatar_url,
        "tel": user.tel,
    }


@router.post("/login", response={200: LoginOut, 401: dict, 403: dict, 400: dict})
def login_api(request, payload: LoginIn):
    logger.info("Login attempt identity_code=%s", payload.identity_code)
    user = authenticate(
        request,
        identity_code=payload.identity_code,
        password=payload.password,
    )
    if user is None:
        logger.warning("Login failed identity_code=%s reason=invalid_credentials", payload.identity_code)
        return 401, {"message": "identity_code 或 password 错误"}
    if user.role == "teacher" and not user.is_approved:
        logger.warning("Login blocked identity_code=%s reason=teacher_not_approved", payload.identity_code)
        return 403, {"message": "账号异常，请联系管理员"}

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    logger.info("Login success identity_code=%s user_id=%s role=%s", payload.identity_code, user.id, user.role)
    return {
        "user": _user_payload(user),
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        },
    }


@router.post("/register/teacher", response={201: dict, 400: dict})
def register_teacher(request, payload: TeacherRegisterIn):
    logger.info("Teacher register attempt identity_code=%s username=%s", payload.identity_code, payload.username)
    if User.objects.filter(identity_code=payload.identity_code).exists():
        logger.warning("Teacher register failed identity_code=%s reason=identity_code_exists", payload.identity_code)
        return 400, {"message": "identity_code 已存在"}
    if User.objects.filter(username=payload.username).exists():
        logger.warning("Teacher register failed username=%s reason=username_exists", payload.username)
        return 400, {"message": "username 已存在"}

    teacher_user = User.objects.create_user(
        username=payload.username,
        identity_code=payload.identity_code,
        password=payload.password,
        role="teacher",
        tel=payload.tel,
        is_approved=False,
    )
    Teacher.objects.create(user=teacher_user)
    logger.info("Teacher register success identity_code=%s user_id=%s", payload.identity_code, teacher_user.id)
    return 201, {"message": "教师注册成功，请等待管理员审核"}


@router.post("/refresh", response={200: TokenPairOut, 401: dict, 400: dict})
def refresh(request, payload: RefreshIn):
    logger.info("Refresh token attempt")
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        logger.warning("Refresh token failed reason=invalid_token")
        return 401, {"message": "refresh_token 无效"}

    if decoded.get("type") != "refresh":
        logger.warning("Refresh token failed reason=wrong_token_type type=%s", decoded.get("type"))
        return 400, {"message": "token 类型错误"}

    # 延迟导入避免循环依赖
    from core.auth import is_token_blacklisted

    if is_token_blacklisted(decoded):
        logger.warning("Refresh token failed reason=blacklisted jti=%s", decoded.get("jti"))
        return 401, {"message": "refresh_token 已失效"}

    user_id = decoded.get("sub")
    if not user_id:
        logger.warning("Refresh token failed reason=missing_sub")
        return 401, {"message": "refresh_token 无效"}

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    blacklist_token(decoded)
    logger.info("Refresh token success user_id=%s", user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@router.post("/logout", auth=JWTAuth(), response={200: dict, 401: dict})
def logout(request, payload: LogoutIn):
    user_id = getattr(request.auth, "id", None)
    logger.info("Logout attempt user_id=%s", user_id)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header.replace("Bearer ", "", 1).strip()
        try:
            decoded_access = decode_token(access_token)
            blacklist_token(decoded_access)
        except jwt.PyJWTError:
            pass

    if payload.refresh_token:
        try:
            decoded_refresh = decode_token(payload.refresh_token)
            blacklist_token(decoded_refresh)
        except jwt.PyJWTError:
            pass

    logger.info("Logout success user_id=%s", user_id)
    return {"message": "退出登录成功"}


@router.get("/whoami", auth=JWTAuth(), response=UserOut)
def whoami(request):
    logger.debug("Whoami requested user_id=%s", getattr(request.auth, "id", None))
    return _user_payload(request.auth)


@router.put("/profile", auth=JWTAuth(), response={200: UserOut, 400: dict})
def update_profile(request, payload: ProfileUpdateIn):
    user = request.auth
    username = (payload.username or "").strip()
    email = (payload.email or "").strip()
    if not username:
        return 400, {"message": "用户名不能为空"}

    if User.objects.exclude(id=user.id).filter(username=username).exists():
        return 400, {"message": "用户名已被占用"}
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return 400, {"message": "邮箱格式不正确"}
        if User.objects.exclude(id=user.id).filter(email=email).exists():
            return 400, {"message": "邮箱已被占用"}

    user.username = username
    user.email = email
    user.tel = (payload.tel or "").strip() or None
    user.save(update_fields=["username", "email", "tel", "updated_at"])
    logger.info("Profile updated user_id=%s", user.id)
    return _user_payload(user)


@router.post("/profile/avatar", auth=JWTAuth(), response={200: UserOut, 400: dict})
def update_profile_avatar(request, avatar: UploadedFile = File(...)):
    user = request.auth
    filename = (avatar.name or "").lower()
    if not filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return 400, {"message": "头像仅支持 jpg/jpeg/png/webp"}

    user.avatar = avatar
    user.save(update_fields=["avatar", "updated_at"])
    logger.info("Profile avatar updated user_id=%s filename=%s", user.id, avatar.name)
    return _user_payload(user)
