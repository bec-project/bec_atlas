from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from bec_atlas.authentication import (
    convert_to_user,
    create_access_token,
    get_current_user,
    get_current_user_token,
    verify_password,
)
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model import UserInfo
from bec_atlas.model.model import User
from bec_atlas.router.base_router import BaseRouter
from bec_atlas.utils.ldap_auth import LDAPUserService


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None, use_ssl=True):
        super().__init__(prefix, datasources)
        self.use_ssl = use_ssl
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.ldap = LDAPUserService(
            ldap_server="ldaps://d.psi.ch", base_dn="OU=users,OU=psi,DC=d,DC=psi,DC=ch"
        )
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/user/me", self.user_me, methods=["GET"])
        self.router.add_api_route("/user/login", self.user_login, methods=["POST"], dependencies=[])
        self.router.add_api_route(
            "/user/login/form", self.form_login, methods=["POST"], dependencies=[]
        )
        self.router.add_api_route("/user/logout", self.user_logout, methods=["POST"])
        self.router.add_api_route("/user/test_login", self.test_login, methods=["POST"])
        self.router.add_api_route("/user/test_login", self.test_login, methods=["POST"])

    @convert_to_user
    async def user_me(self, user: User = Depends(get_current_user)):
        return user

    async def test_login(self, user: UserInfo = Depends(get_current_user_token)):
        return user

    async def form_login(
        self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response
    ):
        user_login = UserLoginRequest(username=form_data.username, password=form_data.password)
        out = await self.user_login(user_login, response)
        return {"access_token": out, "token_type": "bearer"}

    async def user_login(self, user_login: UserLoginRequest, response: Response):
        user = self._get_user(user_login)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found or password is incorrect")
        token = create_access_token(data={"email": user.email})
        response.set_cookie(key="access_token", value=token, httponly=True, secure=self.use_ssl)
        return token

    async def user_logout(self, response: Response):
        response.delete_cookie("access_token")
        return {"message": "Logged out"}

    def _get_user(self, user_login: UserLoginRequest) -> UserInfo | None:
        user = self._get_functional_account(user_login)
        if user is None:
            user = self._get_ad_account(user_login)
        return user

    def _get_functional_account(self, user_login: UserLoginRequest) -> UserInfo | None:
        user = self.db.get_user_by_email(user_login.username)
        if user is None:
            return None
        credentials = self.db.get_user_credentials(user.id)
        if credentials is None:
            return None
        if not verify_password(user_login.password, credentials.password):
            return None
        return user

    def _get_ad_account(self, user_login: UserLoginRequest) -> User | None:
        user = self.ldap.authenticate_and_get_info(user_login.username, user_login.password)
        if user is None:
            return None
        user_info = User(
            owner_groups=["admin"],
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            username=user["username"],
            groups=user["roles"],
        )
        # update the user info in the database
        user = self.db.get_user_by_email(user_info.email)
        if user is None:
            self.db.post(
                collection="users", data=user_info.model_dump(exclude_none=True), dtype=None
            )
        else:
            self.db.patch(
                collection="users", id=user.id, update={"groups": user_info.groups}, dtype=None
            )
        return user_info
