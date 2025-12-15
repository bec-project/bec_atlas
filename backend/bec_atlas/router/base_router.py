from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, TypeVar

from bson import ObjectId
from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from bec_atlas.datasources.mongodb.aggregation_pipelines import (
    build_aggregation_pipeline,
    is_objectid_compatible,
)
from bec_atlas.model.model import User

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.datasource_manager import DatasourceManager


R = TypeVar("R", bound=BaseModel)


class CollectionQueryParams(BaseModel):
    filter: str | None = Query(
        default=None, description='Filter for the query, e.g. {"name": "test"}'
    )
    fields: list[str] | None = Query(
        default=None, description="List of fields to include in the response."
    )
    offset: int = Query(default=0, ge=0, description="Number of items to skip.")
    limit: int = Query(default=100, ge=1, description="Maximum number of items to return.")
    sort: str | None = Query(default=None, description="Sort order, e.g. '{\"name\": 1}'")

    def parsed_fields(self) -> dict | None:
        if self.fields is None:
            return None

        return {field: 1 for field in self.fields}

    def parsed_filter(self) -> dict | None:
        if not self.filter:
            return None
        if isinstance(self.filter, dict):
            return self.filter
        try:
            return json.loads(self.filter)
        except json.JSONDecodeError as exception:
            # pylint: disable=raise-missing-from
            raise HTTPException(400, f"Invalid JSON in filter: {exception}")

    def parsed_sort(self) -> dict | None:
        if not self.sort:
            return None
        try:
            return json.loads(self.sort)
        except json.JSONDecodeError as exception:
            # pylint: disable=raise-missing-from
            raise HTTPException(400, f"Invalid JSON in sort: {exception}")


class CollectionQueryParamsWithInclude(CollectionQueryParams):
    include: dict[str, CollectionQueryParamsWithInclude] | None = Query(
        default=None,
        description=(
            "Include related documents. The key is the name of the relation, and the value is "
            "a nested CollectionQueryParams object for the related collection."
        ),
    )

    @field_validator("include", mode="before")
    @classmethod
    def validate_include(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                include_dict = json.loads(v)
                return {
                    key: CollectionQueryParamsWithInclude(**value)
                    for key, value in include_dict.items()
                }
            except json.JSONDecodeError as exception:
                # pylint: disable=raise-missing-from
                raise HTTPException(400, f"Invalid JSON in include parameter: {exception}")
        if isinstance(v, dict):
            return {key: CollectionQueryParamsWithInclude(**value) for key, value in v.items()}
        raise HTTPException(400, "Invalid format for include parameter")


class BaseRouter:
    def __init__(self, datasources: DatasourceManager, prefix: str = "/api/v1") -> None:
        self.datasources = datasources
        self.prefix = prefix

    @lru_cache(maxsize=128)
    def get_user_from_db(self, _token: str, email: str) -> User | None:
        """
        Get the user from the database. This is a helper function to be used by the
        convert_to_user decorator. The function is cached to avoid repeated database
        queries. To scope the cache to the current request, the token and email are
        used as the cache key.

        Args:
            _token (str): The token
            email (str): The email
        """
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")
        return self.datasources.mongodb.get_user_by_email(email)

    def find_with_query(
        self,
        collection: str,
        query: CollectionQueryParams | CollectionQueryParamsWithInclude,
        dtype: type,
        dtype_partial: type[R],
        user: User | None = None,
    ) -> list[R] | JSONResponse:
        """
        Find documents in the database using the query parameters.

        Args:
            collection (str): The name of the collection to query
            query (CollectionQueryParams | CollectionQueryParamsWithInclude): The query parameters
            dtype (type[R]): The type of the documents to return
            dtype_partial (type[R]): The type of the partial documents to return
            user (User): The user making the request
        Returns:
            list[R] | JSONResponse: The documents returned by the query
        """
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")
        if not self.datasources.mongodb:
            raise RuntimeError("MongoDB datasource not loaded")
        fields = query.parsed_fields()

        query_filter = query.parsed_filter()
        if not hasattr(query, "include") or not query.include:
            if query_filter is not None:
                # convert strings to ObjectIds in the filter if the model's field types require it
                for field_name, val in query_filter.items():
                    field_info = dtype.model_fields.get(field_name)
                    if not field_info:
                        for finfo in dtype.model_fields.values():
                            if finfo.alias == field_name:
                                field_info = finfo
                                break
                    if not field_info:
                        continue
                    if not is_objectid_compatible(field_info.annotation):
                        continue
                    try:
                        query_filter[field_name] = ObjectId(val)
                    except Exception as exc:
                        raise HTTPException(
                            400, f"Invalid ObjectId for field '{field_name}': {exc}"
                        ) from exc

            out = self.datasources.mongodb.find(
                collection=collection,
                query_filter=query_filter,
                dtype=dtype_partial,
                fields=fields,
                offset=query.offset,
                limit=query.limit,
                sort=query.parsed_sort(),
            )
        else:
            pipeline = build_aggregation_pipeline(dtype, query, user=user)
            out = self.datasources.mongodb.aggregate(collection, pipeline, dtype_partial, user=user)
        if fields:
            return JSONResponse(
                content=[
                    model.model_dump(exclude_none=True, exclude_defaults=True, mode="json")
                    for model in out
                ]
            )
        return out
