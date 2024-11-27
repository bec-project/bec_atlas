from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from bec_atlas.authentication import create_access_token, get_current_user, verify_password
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model import UserInfo
from bec_atlas.router.base_router import BaseRouter


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/user/me", self.user_me, methods=["GET"])
        self.router.add_api_route("/user/login", self.user_login, methods=["POST"], dependencies=[])
        self.router.add_api_route(
            "/user/login/form", self.form_login, methods=["POST"], dependencies=[]
        )

    async def user_me(self, user: UserInfo = Depends(get_current_user)):
        data = self.db.get_user_by_email(user.email)
        if data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return data

    async def form_login(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
        user_login = UserLoginRequest(username=form_data.username, password=form_data.password)
        out = await self.user_login(user_login)
        return {"access_token": out, "token_type": "bearer"}

    async def user_login(self, user_login: UserLoginRequest):
        user = self.db.get_user_by_email(user_login.username)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        credentials = self.db.get_user_credentials(user.id)
        if credentials is None:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(user_login.password, credentials.password):
            raise HTTPException(status_code=401, detail="Invalid password")

        return create_access_token(data={"groups": list(user.groups), "email": user.email})
