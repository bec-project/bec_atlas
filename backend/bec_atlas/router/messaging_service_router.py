from __future__ import annotations

from typing import TYPE_CHECKING

import pymongo
from bec_lib import messages
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from scilog.models import Logbook

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.endpoints import RedisAtlasEndpoints
from bec_atlas.model.model import (
    AvailableMessagingServiceInfo,
    AvailableMessagingServiceInfoPartial,
    Deployments,
    MergedMessagingServiceInfo,
    Session,
    User,
)
from bec_atlas.router.base_router import BaseRouter, CollectionQueryParams

if TYPE_CHECKING:
    from bec_atlas.datasources.datasource_manager import DatasourceManager


class MessagingServiceRouter(BaseRouter):
    def __init__(self, datasources: DatasourceManager, prefix="/api/v1"):
        super().__init__(datasources=datasources, prefix=prefix)
        self.db = self.datasources.mongodb
        self.redis = self.datasources.redis
        self.scilog = self.datasources.scilog
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/messagingServices",
            self.messaging_services,
            methods=["GET"],
            description="Get all messaging services either a deployment or a session or both",
            response_model=list[AvailableMessagingServiceInfoPartial],
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/messagingServices",
            self.messaging_services_create,
            methods=["POST"],
            description="Create a new messaging service for a deployment or a session",
            response_model=AvailableMessagingServiceInfo,
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/messagingServices/{messaging_service_id}",
            self.messaging_services_update,
            methods=["PATCH"],
            description="Update a messaging service",
            response_model=AvailableMessagingServiceInfo,
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/messagingServices/{messaging_service_id}",
            self.messaging_services_delete,
            methods=["DELETE"],
            description="Delete a messaging service",
            response_model=None,
        )
        self.router.add_api_route(
            "/messagingServices/requestLink",
            self.request_signal_link,
            methods=["POST"],
            description="Request to start a signal link exchange for a session or deployment",
            response_model=None,
        )
        self.router.add_api_route(
            "/messagingServices/availableLogbooks",
            self.available_logbooks,
            methods=["GET"],
            description="Get all available logbooks for the specified experiment",
            response_model=list[Logbook],
            response_model_exclude_none=True,
        )

    @convert_to_user
    async def messaging_services(
        self,
        query: CollectionQueryParams = Query(
            default_factory=CollectionQueryParams,
            description="Query parameters for filtering, sorting, and paginating messaging services.",
        ),
        current_user: User = Depends(get_current_user),
    ) -> list[AvailableMessagingServiceInfoPartial] | JSONResponse:
        """
        Get all messaging services.
        """
        return self.find_with_query(
            collection="messaging_services",
            dtype=MergedMessagingServiceInfo,
            dtype_partial=MergedMessagingServiceInfo,
            query=query,
            user=current_user,
        )

    @convert_to_user
    async def messaging_services_create(
        self,
        messaging_service: MergedMessagingServiceInfo,
        current_user: User = Depends(get_current_user),
    ) -> AvailableMessagingServiceInfo:
        """
        Create a new messaging service for a deployment or a session.
        """

        # The user must have access to the deployment or session for which the messaging service is being created.
        # We check this by trying to fetch the deployment or session with the provided id and checking if it returns a result.
        # If it does not return a result, it means that either the deployment or session does not exist or the user
        # does not have access to it, and we raise a 404 error.

        if not messaging_service.parent_id:
            raise HTTPException(status_code=400, detail="Parent ID must be provided")

        if not ObjectId.is_valid(messaging_service.parent_id):
            raise HTTPException(status_code=400, detail="Invalid parent ID format")

        if not messaging_service.service_type or messaging_service.service_type not in [
            "signal",
            "scilog",
            "teams",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Service type must be provided and must be one of 'signal', 'scilog' or 'teams'",
            )

        # Check if it is a session
        is_session = True
        parent = self.db.find_one(
            collection="sessions",
            query_filter={"_id": messaging_service.parent_id},
            dtype=Session,
            user=current_user,
        )
        if not parent:
            is_session = False
            # Check if it is a deployment
            parent = self.db.find_one(
                collection="deployments",
                query_filter={"_id": messaging_service.parent_id},
                dtype=Deployments,
                user=current_user,
            )
            if not parent:
                raise HTTPException(
                    status_code=404,
                    detail="Neither session nor deployment found with the provided parent ID or user does not have access",
                )

        messaging_service.owner_groups = parent.owner_groups
        messaging_service.access_groups = parent.access_groups

        messaging_service.id = None

        try:
            out = self.db.post(
                collection="messaging_services",
                data=messaging_service.model_dump(exclude_none=True),
                dtype=None,
            )
        except pymongo.errors.DuplicateKeyError:
            parent_type = "session" if is_session else "deployment"
            # pylint: disable=raise-missing-from
            raise HTTPException(
                status_code=400,
                detail=f"Messaging service with the same name already exists for {parent_type} {messaging_service.parent_id}",
            )

        # After updating the database, we trigger the deployment info update which requires the Deployments object,
        # so we fetch the deployment object and pass it to the update_deployment_info method.
        deployment_id = parent.deployment_id if is_session else parent.id
        self._update_deployment_info(deployment_id)
        return out

    @convert_to_user
    async def messaging_services_update(
        self,
        messaging_service_id: str,
        messaging_service: AvailableMessagingServiceInfoPartial,
        current_user: User = Depends(get_current_user),
    ) -> AvailableMessagingServiceInfo:
        """
        Update a messaging service.

        Args:
            messaging_service_id (str): The messaging service id
            messaging_service (AvailableMessagingServiceInfoPartial): The messaging service data to update
            current_user (User): The current user

        Returns:
            AvailableMessagingServiceInfo: The updated messaging service
        """
        if not ObjectId.is_valid(messaging_service_id):
            raise HTTPException(status_code=400, detail="Invalid messaging service id")

        # First, check if the messaging service exists and the user has access to it
        existing_service = self.db.find_one(
            collection="messaging_services",
            query_filter={"_id": ObjectId(messaging_service_id)},
            dtype=None,
            user=current_user,
        )

        if not existing_service:
            raise HTTPException(
                status_code=404, detail="Messaging service not found or user does not have access"
            )

        # Prepare the update data, excluding None values and fields that shouldn't be updated
        update_data = messaging_service.model_dump(exclude_none=True, exclude_unset=True)
        # Remove fields that should not be updated
        update_data.pop("_id", None)
        update_data.pop("id", None)
        update_data.pop("parent_id", None)  # parent_id should not be changed
        update_data.pop("owner_groups", None)  # owner_groups should not be changed
        update_data.pop("access_groups", None)  # access_groups should not be changed

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Perform the update
        updated_service = self.db.patch(
            collection="messaging_services",
            id=ObjectId(messaging_service_id),
            update=update_data,
            dtype=None,
            user=current_user,
            return_document=True,
        )

        if not updated_service:
            raise HTTPException(
                status_code=404, detail="Messaging service not found or user does not have access"
            )

        session = self.db.find_one(
            collection="sessions",
            query_filter={"_id": ObjectId(updated_service["parent_id"])},
            dtype=Session,
            user=current_user,
        )
        if session:
            deployment_id = session.deployment_id
        else:
            deployment_id = updated_service["parent_id"]

        self._update_deployment_info(deployment_id)
        return updated_service

    @convert_to_user
    async def messaging_services_delete(
        self, messaging_service_id: str, current_user: User = Depends(get_current_user)
    ) -> None:
        """
        Delete a messaging service.

        Args:
            messaging_service_id (str): The messaging service id
            current_user (User): The current user

        Returns:
            None
        """
        if not ObjectId.is_valid(messaging_service_id):
            raise HTTPException(status_code=400, detail="Invalid messaging service id")

        # Check if the messaging service exists and the user has access to it
        existing_service = self.db.find_one(
            collection="messaging_services",
            query_filter={"_id": ObjectId(messaging_service_id)},
            dtype=None,
            user=current_user,
        )

        if not existing_service:
            raise HTTPException(
                status_code=404, detail="Messaging service not found or user does not have access"
            )

        parent_id = existing_service["parent_id"]

        # Delete the messaging service
        deleted = self.db.delete_one(
            collection="messaging_services",
            filter={"_id": ObjectId(messaging_service_id)},
            user=current_user,
        )

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete messaging service")

        session = self.db.find_one(
            collection="sessions",
            query_filter={"_id": ObjectId(parent_id)},
            dtype=Session,
            user=current_user,
        )
        if session:
            deployment_id = session.deployment_id
        else:
            deployment_id = parent_id
        self._update_deployment_info(deployment_id)

        if existing_service.get("service_type") == "signal":
            # If the deleted messaging service is of type "signal",
            # we also leave the signal group associated with it to avoid orphaned groups.
            signal_group_id = existing_service.get("group_id")
            if signal_group_id:
                msg = messages.VariableMessage(
                    value={"action": "leave", "group_id": signal_group_id}
                )
                self.redis.connector.send(RedisAtlasEndpoints.signal_group_updates(), msg)

    @convert_to_user
    async def request_signal_link(
        self, number: str, messaging_service_id: str, current_user: User = Depends(get_current_user)
    ) -> None:
        """
        Request to start a signal link exchange for a messaging service.

        Args:
            messaging_service_id (str): The messaging service id
            number (str): The phone number to receive the link request

        Returns:
            None
        """

        output_storage = {"number": number}
        if not messaging_service_id:
            raise HTTPException(status_code=400, detail="Messaging service id must be provided")

        if not ObjectId.is_valid(messaging_service_id):
            raise HTTPException(status_code=400, detail="Invalid messaging service id format")
        out = self.db.find_one(
            "messaging_services", {"_id": ObjectId(messaging_service_id)}, None, user=current_user
        )

        if not out:
            raise HTTPException(
                status_code=404, detail="Messaging service not found or user does not have access"
            )

        if out.get("service_type") != "signal":
            raise HTTPException(status_code=400, detail="Messaging service is not of type signal")

        output_storage["messaging_service_id"] = messaging_service_id

        parent_id = out.get("parent_id")
        session = self.db.find_one(
            collection="sessions",
            query_filter={"_id": ObjectId(parent_id)},
            dtype=None,
            user=current_user,
        )
        if session:
            output_storage["session_id"] = str(session["_id"])
            output_storage["session"] = session
            output_storage["session"]["_id"] = str(output_storage["session"]["_id"])
        else:
            deployment = self.db.find_one(
                collection="deployments",
                query_filter={"_id": ObjectId(parent_id)},
                dtype=None,
                user=current_user,
            )
            if not deployment:
                raise HTTPException(
                    status_code=404,
                    detail="Neither session nor deployment found for the messaging service or user does not have access",
                )
            output_storage["deployment_id"] = str(deployment["_id"])
            output_storage["deployment"] = deployment
            output_storage["deployment"]["_id"] = str(output_storage["deployment"]["_id"])

        if not out:
            raise HTTPException(status_code=404, detail="Target messaging service not found")

        # We post a new VariableMessage to the Redis instance on Atlas, which will
        # trigger the signal link exchange process for the messaging service.
        message = messages.VariableMessage(value=output_storage)
        self.redis.connector.send(RedisAtlasEndpoints.signal_link_requests(), message)

    @convert_to_user
    async def available_logbooks(
        self, experiment_id: str, current_user: User = Depends(get_current_user)
    ) -> list[Logbook]:
        """
        Get all available logbooks for the specified experiment.

        Args:
            experiment_id (str): The experiment id
            current_user (User): The current user
        Returns:
            list[Logbook]: A list of available logbooks for the specified experiment
        """

        # We fetch the experiment to check if it exists and the user has access to it. If not, we raise a 404 error.
        experiment = self.db.find_one(
            collection="experiments",
            query_filter={"_id": experiment_id},
            dtype=None,
            user=current_user,
        )
        if not experiment:
            raise HTTPException(
                status_code=404, detail="Experiment not found or user does not have access"
            )

        out = self.scilog.fetch_logbooks_for_pgroup(pgroup=experiment_id)

        return out

    def _update_deployment_info(self, deployment_id: str | ObjectId):
        if isinstance(deployment_id, ObjectId):
            deployment_id = str(deployment_id)
        deployments = self.db.get_full_deployment(filter={"_id": deployment_id})
        deployment_info = next(iter(deployments), None)
        if deployment_info:
            self.redis.update_deployment_info(deployment_info)
