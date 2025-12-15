from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, cast

from bec_lib import messages
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.endpoints import RedisAtlasEndpoints
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import (
    DeploymentCredential,
    Deployments,
    DeploymentsPartial,
    Experiment,
    Session,
    User,
)
from bec_atlas.router.base_router import BaseRouter, CollectionQueryParamsWithInclude

if TYPE_CHECKING:  # pragma: no cover

    from bec_atlas.datasources.datasource_manager import DatasourceManager
    from bec_atlas.datasources.redis_datasource import RedisDatasource

logger = logging.getLogger(__name__)


class DeploymentsRouter(BaseRouter):
    def __init__(self, datasources: DatasourceManager, prefix="/api/v1"):
        super().__init__(datasources, prefix)
        self.db: MongoDBDatasource = self.datasources.mongodb
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/deployments",
            self.deployments,
            methods=["GET"],
            description="Get all deployments for the realm",
            response_model=list[DeploymentsPartial],
        )
        self.router.add_api_route(
            "/deployments/realm",
            self.deployments_for_realm,
            methods=["GET"],
            description="Get all deployments for the realm",
            response_model=list[Deployments],
        )
        self.router.add_api_route(
            "/deployments/id",
            self.deployment_with_id,
            methods=["GET"],
            description="Get a single deployment by id for a realm",
            response_model=Deployments | None,
        )
        self.router.add_api_route(
            "/deployments/experiment",
            self.deployments_set_experiment,
            methods=["POST"],
            description="Set the experiment for a deployment",
            response_model=Deployments,
        )

        self.update_available_deployments()

    @convert_to_user
    async def deployments(
        self,
        query: CollectionQueryParamsWithInclude = Query(
            default_factory=CollectionQueryParamsWithInclude,
            description=(
                "Query parameters for filtering, sorting, paginating, and including relations."
            ),
            title="Deployment Query Parameters",
        ),
        current_user: User = Depends(get_current_user),
    ) -> list[DeploymentsPartial] | JSONResponse:
        """
        Get all deployments matching the query.

        Args:
            query (CollectionQueryParamsWithInclude): The query parameters for filtering, sorting, and paginating deployments.
            current_user (User): The current user

        Returns:
            list[DeploymentsPartial]: List of deployments for the realm
        """
        return self.find_with_query(
            collection="deployments",
            dtype=Deployments,
            dtype_partial=DeploymentsPartial,
            query=query,
            user=current_user,
        )

    @convert_to_user
    async def deployments_for_realm(
        self,
        realm: str,
        include_session: bool = False,
        include_experiment: bool = False,
        include_message_services: bool = False,
        current_user: User = Depends(get_current_user),
    ) -> list[Deployments] | JSONResponse:
        """
        Get all deployments for a realm.

        Args:
            realm (str): The realm id
            include_session (bool): Include active session in the response
            include_experiment (bool): Include experiment in the session response
            include_message_services (bool): Include message services in the session response
            current_user (User): The current user

        Returns:
            list[Deployments] | JSONResponse: List of deployments for the realm
        """
        return self._get_deployment_with_includes(
            filter={"realm_id": realm},
            include_session=include_session,
            include_experiment=include_experiment,
            include_message_services=include_message_services,
            user=current_user,
        )

    @convert_to_user
    async def deployment_with_id(
        self,
        deployment_id: str,
        include_session: bool = False,
        include_experiment: bool = False,
        include_message_services: bool = False,
        current_user: User = Depends(get_current_user),
    ) -> Deployments | None:
        """
        Get deployment with id from realm

        Args:
            deployment_id (str): The deployment id
            include_session (bool): Include active session in the response
            include_experiment (bool): Include experiment in the session response
            include_message_services (bool): Include message services in the session response
            current_user (User): The current user

        Returns:
            Deployments | None: The deployment with the given id
        """
        if not ObjectId.is_valid(deployment_id):
            raise HTTPException(status_code=400, detail="Invalid deployment id")

        out = self._get_deployment_with_includes(
            filter={"_id": deployment_id},
            include_session=include_session,
            include_experiment=include_experiment,
            include_message_services=include_message_services,
            user=current_user,
        )
        if isinstance(out, JSONResponse):
            raise HTTPException(
                status_code=400, detail="Unexpected error occurred while fetching deployment"
            )
        return out[0] if out else None

    def _get_deployment_with_includes(
        self,
        filter: dict,
        include_session: bool = False,
        include_experiment: bool = False,
        include_message_services: bool = False,
        user: User | None = None,
    ) -> list[Deployments] | JSONResponse:
        include = {}
        if include_session:
            session_include = {}
            if include_experiment:
                session_include["experiment"] = {}
            if include_message_services:
                session_include["messaging_services"] = {}

            if session_include:
                include["active_session"] = {"include": session_include}
            else:
                include["active_session"] = {}
        if include_message_services:
            include["messaging_services"] = {}
        query = CollectionQueryParamsWithInclude(
            filter=json.dumps(filter), include=include if include else None
        )
        return self.find_with_query(
            collection="deployments",
            dtype=Deployments,
            dtype_partial=DeploymentsPartial,
            query=query,
            user=user,
        )

    @convert_to_user
    async def deployments_set_experiment(
        self, experiment_id: str, deployment_id: str, current_user: User = Depends(get_current_user)
    ) -> Deployments:
        """
        Set the experiment for a deployment.
        If the experiment_id exists, it will perform the following steps:
        - check if a session already exists for the deployment and experiment
        - if the session does not exist, a new session will be created
        - set the active_session_id of the deployment to the session id

        Args:
            experiment_id (str): The experiment id
            deployment_id (str): The deployment id
            current_user (User): The current user
        Returns:
            Deployments: The updated deployment
        """
        # Validate deployment_id
        if not ObjectId.is_valid(deployment_id):
            raise HTTPException(status_code=400, detail="Invalid deployment id")

        # Get deployment
        deployments = self._get_deployment_with_includes(
            filter={"_id": deployment_id},
            include_session=True,
            include_experiment=False,
            include_message_services=True,
            user=current_user,
        )
        if not deployments:
            raise HTTPException(status_code=404, detail="Deployment not found")
        deployment = deployments[0]

        if deployment.active_session and deployment.active_session.experiment_id == experiment_id:
            # The deployment already has the experiment set, we can return early
            return deployment

        # Get experiment
        experiment = self.db.find_one(
            "experiments", {"_id": experiment_id}, Experiment, user=current_user
        )
        if experiment is None:
            raise HTTPException(status_code=404, detail="Experiment not found")

        # Find or create session for this experiment and deployment
        session = self.db.find_one(
            "sessions",
            {"experiment_id": experiment_id, "deployment_id": ObjectId(deployment_id)},
            Session,
            user=current_user,
        )

        if session is None:
            logger.info(
                f"No session found for experiment {experiment_id} and deployment {deployment_id}, creating a new one."
            )

            new_session = Session(
                name=str(experiment.id) if experiment.id else experiment_id,
                experiment_id=experiment_id,
                deployment_id=ObjectId(deployment_id),
                owner_groups=deployment.owner_groups or [],
                access_groups=[experiment_id],
            )
            session_result = self.db.db["sessions"].insert_one(
                new_session.model_dump(exclude_none=True)
            )
            session_id = str(session_result.inserted_id)
        else:
            session_id = str(session.id)

        # Update deployment's active_session_id
        self.db.patch(
            "deployments",
            ObjectId(deployment_id),
            {"active_session_id": ObjectId(session_id)},
            dtype=None,
            user=current_user,
        )

        # Get updated deployment including the active session and experiment
        updated_deployment = self._get_deployment_with_includes(
            filter={"_id": deployment_id},
            include_session=True,
            include_experiment=True,
            include_message_services=True,
            user=current_user,
        )

        if not updated_deployment:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated deployment")

        output_deployment = updated_deployment[0]

        self.update_messaging_services_for_session(
            old_session=deployment.active_session, new_session=output_deployment.active_session
        )

        # Update Redis with the new deployment info
        redis: RedisDatasource = self.datasources.redis
        redis.update_deployment_info(deployment=output_deployment)

        return output_deployment

    def update_available_deployments(self):
        """
        Update the available deployments.
        """
        self.available_deployments = self._get_deployment_with_includes(
            filter={}, include_session=True, include_experiment=True, include_message_services=True
        )

        # purely for type checking; it is guaranteed to be a list after the above call
        assert isinstance(self.available_deployments, list)

        credentials = self.db.find("deployment_credentials", {}, DeploymentCredential)

        data = {
            deployment.id: {"realm_id": deployment.realm_id}
            for deployment in self.available_deployments
        }

        # add the credentials to the data
        for cred in credentials:
            if cred.id in data:
                data[cred.id]["deployment_credential"] = cred

        redis: RedisDatasource = self.datasources.redis
        msg = json.dumps([msg.model_dump(mode="json") for msg in self.available_deployments])
        redis.connector.set_and_publish("deployments", msg)
        for info in data.values():
            redis.add_deployment_acl(info["deployment_credential"], info["realm_id"])

        for deployment in self.available_deployments:
            redis.update_deployment_info(deployment)

        try:
            redis.connector._redis_conn.acl_save()
        except Exception:
            logger.error("Failed to save ACLs to disk")

    def update_messaging_services_for_session(
        self, old_session: Session | None, new_session: Session | None
    ):
        """
        Update the messaging services for a session when the active session of a deployment is changed.

        Args:
            old_session (Session | None): The old active session of the deployment
            new_session (Session | None): The new active session of the deployment
        """
        if not old_session and not new_session:
            # No active session before or after, nothing to update
            return
        if old_session:
            for msg in old_session.messaging_services or []:
                self.unlink_messaging_service(msg)
        if new_session:
            for msg in new_session.messaging_services or []:
                self.link_messaging_service(msg)

    def unlink_messaging_service(self, msg: messages.AvailableMessagingServices):
        """
        Unlink the messaging service. Depending on the messaging service type,
        this could involve different actions such as joining groups.

        Args:
            msg: The messaging service to remove
        """
        redis: RedisDatasource = self.datasources.redis
        match msg.service_type:
            case "signal":
                msg = cast(messages.SignalServiceInfo, msg)
                if not msg.group_id:
                    return
                update_message = messages.VariableMessage(
                    value={"action": "leave", "group_id": msg.group_id}
                )
                redis.connector.send(RedisAtlasEndpoints.signal_group_updates(), update_message)

    def link_messaging_service(self, msg: messages.AvailableMessagingServices):
        """
        Link the messaging service. Depending on the messaging service type,
        this could involve different actions such as joining groups.

        Args:
            msg: The messaging service to link
        """
        redis: RedisDatasource = self.datasources.redis
        match msg.service_type:
            case "signal":
                msg = cast(messages.SignalServiceInfo, msg)
                if not msg.group_link:
                    return
                if not msg.group_link.startswith("https://signal.group/"):
                    return
                update_message = messages.VariableMessage(
                    value={"action": "join", "group_link": msg.group_link}
                )
                redis.connector.send(RedisAtlasEndpoints.signal_group_updates(), update_message)
