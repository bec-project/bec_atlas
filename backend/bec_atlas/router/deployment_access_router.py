import secrets
import time
from typing import TYPE_CHECKING, Any

from bec_lib.endpoints import EndpointInfo, MessageOp
from bec_lib.serialization import MsgpackSerialization
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import BECAccessProfile, DeploymentAccess, User
from bec_atlas.router.base_router import BaseRouter
from bec_atlas.router.redis_router import RedisAtlasEndpoints

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.redis_datasource import RedisDatasource


class DeploymentAccessRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/deployment_access",
            self.get_deployment_access,
            methods=["GET"],
            description="Get the access lists for a specific deployment.",
            response_model=DeploymentAccess,
        )
        self.router.add_api_route(
            "/deployment_access",
            self.patch_deployment_access,
            methods=["PATCH"],
            description="Update the access lists for a specific deployment.",
            response_model=DeploymentAccess,
        )

    @convert_to_user
    async def get_deployment_access(
        self, deployment_id: str, current_user: User = Depends(get_current_user)
    ) -> DeploymentAccess:
        """
        Get the access lists for a specific deployment.

        Args:
            deployment_id (str): The deployment id
            current_user (UserInfo): The current user

        Returns:
            DeploymentAccess: The access lists for the deployment
        """
        if not ObjectId.is_valid(deployment_id):
            raise HTTPException(status_code=400, detail="Invalid deployment ID")
        return self.db.find_one(
            "deployments", {"_id": ObjectId(deployment_id)}, DeploymentAccess, user=current_user
        )

    @convert_to_user
    async def patch_deployment_access(
        self,
        deployment_id: str,
        deployment_access: dict,
        current_user: User = Depends(get_current_user),
    ) -> DeploymentAccess:
        """
        Update the access lists for a specific deployment.

        Args:
            deployment_id (str): The deployment id
            deployment_access (DeploymentAccess): The deployment access object
            current_user (UserInfo): The current user

        Returns:
            DeploymentAccess: The updated access lists for the deployment
        """
        deployment_access.pop("_id", None)
        deployment_access.pop("id", None)
        deployment_access.pop("owner_groups", None)
        deployment_access.pop("access_groups", None)
        original = self.db.find_one(
            "deployment_access",
            {"_id": ObjectId(deployment_id)},
            DeploymentAccess,
            user=current_user,
        )
        out = self.db.patch(
            collection="deployment_access",
            id=ObjectId(deployment_id),
            update=deployment_access,
            dtype=DeploymentAccess,
            user=current_user,
        )
        self._update_bec_access_profiles(original=original, updated=out)
        self._refresh_redis_bec_access(deployment_id)
        return out

    def _update_bec_access_profiles(self, original: DeploymentAccess, updated: DeploymentAccess):
        """
        Update the BEC access profiles in the database. This will not update the redis access.
        Call _refresh_redis_bec_access to update the redis access.

        Args:
            deployment_access (DeploymentAccess): The deployment access object
        """
        db: MongoDBDatasource = self.datasources.datasources.get("mongodb")

        new_profiles = set(
            updated.user_read_access
            + updated.user_write_access
            + updated.su_read_access
            + updated.su_write_access
        )
        old_profiles = set(
            original.user_read_access
            + original.user_write_access
            + original.su_read_access
            + original.su_write_access
        )
        removed_profiles = old_profiles - new_profiles
        for profile in removed_profiles:
            db.delete_one("bec_access_profiles", {"username": profile, "deployment_id": updated.id})
        for profile in new_profiles:
            if profile in updated.su_write_access:
                access = self._get_redis_access_profile("su_write", profile, str(updated.id))
            elif profile in updated.su_read_access:
                access = self._get_redis_access_profile("su_read", profile, str(updated.id))
            elif profile in updated.user_write_access:
                access = self._get_redis_access_profile("user_write", profile, str(updated.id))
            else:
                access = self._get_redis_access_profile("user_read", profile, str(updated.id))

            existing_profile = db.find_one(
                "bec_access_profiles",
                {"username": profile, "deployment_id": str(updated.id)},
                BECAccessProfile,
            )
            if existing_profile:
                # access.passwords = existing_profile.passwords
                db.patch(
                    "bec_access_profiles",
                    existing_profile.id,
                    access.model_dump(exclude_none=True, exclude_defaults=True),
                    BECAccessProfile,
                )
            else:
                access.passwords = {str(time.time()): secrets.token_urlsafe(32)}
                db.post(
                    "bec_access_profiles", access.model_dump(exclude_none=True), BECAccessProfile
                )

    def _refresh_redis_bec_access(self, deployment_id: str):
        """
        Refresh the redis BEC access.
        """
        redis: RedisDatasource = self.datasources.datasources.get("redis")
        db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        profiles = db.find(
            collection="bec_access_profiles",
            query_filter={"deployment_id": deployment_id},
            dtype=BECAccessProfile,
        )
        profiles = [profile.model_dump(exclude_none=True) for profile in profiles]
        for profile in profiles:
            profile.pop("owner_groups", None)
            profile.pop("access_groups", None)
            profile.pop("deployment_id", None)
            profile.pop("_id", None)

        endpoint_info = EndpointInfo(
            RedisAtlasEndpoints.redis_bec_acl_user(deployment_id), Any, MessageOp.SET_PUBLISH
        )

        redis.connector.set_and_publish(endpoint_info, MsgpackSerialization.dumps(profiles))

    def _get_redis_access_profile(self, access_profile: str, username: str, deployment_id: str):
        """
        Get the redis access profile.

        Args:
            access_profile (str): The access profile
            username (str): The username
            deployment_id (str): The deployment id

        """
        if access_profile == "su_write":
            return BECAccessProfile(
                owner_groups=["admin"],
                access_groups=[username],
                deployment_id=deployment_id,
                username=username,
                categories=["+@all"],
                keys=["*"],
                channels=["*"],
                commands=["+all"],
                profile="su_write",
            )
        if access_profile == "su_read":
            return BECAccessProfile(
                owner_groups=["admin"],
                access_groups=[username],
                deployment_id=deployment_id,
                username=username,
                categories=["+@all", "-@dangerous"],
                keys=["*"],
                channels=["*"],
                commands=["+read"],
                profile="su_read",
            )
        if access_profile == "user_write":
            return BECAccessProfile(
                owner_groups=["admin"],
                access_groups=[username],
                deployment_id=deployment_id,
                username=username,
                categories=["+@all", "-@dangerous"],
                keys=["*"],
                channels=["*"],
                commands=["+write"],
                profile="user_write",
            )
        return BECAccessProfile(
            owner_groups=["admin"],
            access_groups=[username],
            deployment_id=deployment_id,
            username=username,
            categories=["+@all", "-@dangerous"],
            keys=["*"],
            channels=["*"],
            commands=["+read"],
            profile="user_read",
        )
