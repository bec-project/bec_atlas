import os
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from bec_atlas.model import UserInfo

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login/form")
password_hash = PasswordHash.recommended()


class OptionalOAuth2PasswordBearer(OAuth2PasswordBearer):
    """
    OAuth2PasswordBearer that returns None instead of raising HTTPException
    when no Authorization header is present.
    """

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            return None

        return param


optional_oauth2_scheme = OptionalOAuth2PasswordBearer(tokenUrl="/api/v1/user/login/form")


def convert_to_user(func):
    """
    Decorator to convert the current_user parameter to a User object.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if "current_user" in kwargs:
            current_user = kwargs["current_user"]
            if current_user:
                router = args[0]
                user = router.get_user_from_db(current_user.token, current_user.email)
                kwargs["current_user"] = user
        return await func(*args, **kwargs)

    return wrapper


@lru_cache()
def get_secret_key():
    """
    Load the JWT secret from disk or use a default value.
    """
    deployment_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deployment")
    secret_file = os.path.join(deployment_dir, ".jwt_secret")
    if not os.path.exists(secret_file):
        return "test_secret"
    with open(secret_file, "r", encoding="utf-8") as token_file:
        return token_file.read().strip()


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError as exc:
        raise credentials_exception from exc


async def get_current_user(
    request: Request, token: Optional[str] = Depends(optional_oauth2_scheme)
) -> UserInfo:
    """
    Unified authentication method that supports both token and cookie-based authentication.
    Tries to extract token from Authorization header first, then falls back to cookies.
    """
    auth_token = None

    # First try to get token from OAuth2 scheme (Authorization header)
    if token:
        auth_token = token

    # If no token from Authorization header, try cookies
    if not auth_token:
        auth_token = request.cookies.get("access_token")

    if not auth_token:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials - no token found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return get_current_user_sync(auth_token)


def get_current_user_sync(token: str) -> UserInfo:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email = payload.get("email")
        if not email:
            raise credentials_exception
    except Exception as exc:
        raise credentials_exception from exc
    return UserInfo(email=email, token=token)
