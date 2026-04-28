from typing import Optional

import jwt
from django.contrib.auth import authenticate
from ninja import Router, Schema

from core.auth import (
    JWTAuth,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = Router(tags=["auth"])


class LoginIn(Schema):
    identity_code: str
    password: str


class RefreshIn(Schema):
    refresh_token: str


class LogoutIn(Schema):
    refresh_token: Optional[str] = None


class UserOut(Schema):
    id: str
    identity_code: str
    username: str
    role: str
    avatar: Optional[str] = None
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
        "role": user.role,
        "avatar": avatar_url,
        "tel": user.tel,
    }


@router.post("/login", response={200: LoginOut, 401: dict, 400: dict})
def login_api(request, payload: LoginIn):
    user = authenticate(
        request,
        identity_code=payload.identity_code,
        password=payload.password,
    )
    if user is None:
        return 401, {"message": "identity_code 或 password 错误"}

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return {
        "user": _user_payload(user),
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        },
    }


@router.post("/refresh", response={200: TokenPairOut, 401: dict, 400: dict})
def refresh(request, payload: RefreshIn):
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        return 401, {"message": "refresh_token 无效"}

    if decoded.get("type") != "refresh":
        return 400, {"message": "token 类型错误"}

    # 延迟导入避免循环依赖
    from core.auth import is_token_blacklisted

    if is_token_blacklisted(decoded):
        return 401, {"message": "refresh_token 已失效"}

    user_id = decoded.get("sub")
    if not user_id:
        return 401, {"message": "refresh_token 无效"}

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    blacklist_token(decoded)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@router.post("/logout", auth=JWTAuth(), response={200: dict, 401: dict})
def logout(request, payload: LogoutIn):
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

    return {"message": "退出登录成功"}


@router.get("/whoami", auth=JWTAuth(), response=UserOut)
def whoami(request):
    return _user_payload(request.auth)
