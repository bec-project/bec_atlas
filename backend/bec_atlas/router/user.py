from typing import Annotated

from bec_atlas.authentication import create_access_token, get_current_user, verify_password
from bec_atlas.datasources.scylladb import scylladb_schema as schema
from bec_atlas.router.base_router import BaseRouter
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.scylla = self.datasources.datasources.get("scylla")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/user/me", self.user_me, methods=["GET"])
        self.router.add_api_route("/user/login", self.user_login, methods=["POST"], dependencies=[])
        self.router.add_api_route(
            "/user/login/form", self.form_login, methods=["POST"], dependencies=[]
        )

    async def user_me(self, user: schema.User = Depends(get_current_user)):
        data = schema.User.objects.filter(email=user.email)
        if data.count() == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return data.first()

    async def form_login(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
        user_login = UserLoginRequest(username=form_data.username, password=form_data.password)
        out = await self.user_login(user_login)
        return {"access_token": out, "token_type": "bearer"}

    async def user_login(self, user_login: UserLoginRequest):
        result = schema.User.objects.filter(email=user_login.username)
        if result.count() == 0:
            raise HTTPException(status_code=404, detail="User not found")
        user: schema.User = result.first()
        credentials = schema.UserCredentials.objects.filter(user_id=user.user_id)
        if credentials.count() == 0:
            raise HTTPException(status_code=404, detail="User not found")
        user_credentials = credentials.first()
        if not verify_password(user_login.password, user_credentials.password):
            raise HTTPException(status_code=401, detail="Invalid password")

        return create_access_token(data={"groups": list(user.groups), "email": user.email})
