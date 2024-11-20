import os
from datetime import datetime, timedelta
from typing import Annotated

import jwt
from bec_atlas.datasources.scylladb import scylladb_schema as schema
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login/form")
password_hash = PasswordHash.recommended()


def get_secret_key():
    val = os.getenv("SECRET_KEY", "test_secret")
    return val


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
    to_encode.update({"exp": expire})
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


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> schema.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        groups = payload.get("groups")
        email = payload.get("email")
        if not groups or not email:
            raise credentials_exception
    except Exception as exc:
        raise credentials_exception from exc
    return schema.User(groups=groups, email=email)
