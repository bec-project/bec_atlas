from __future__ import annotations

from types import UnionType
from typing import TYPE_CHECKING, Type, Union, get_args, get_origin

from bson import ObjectId

if TYPE_CHECKING:
    from bec_atlas.model.model import MongoBaseModel, Relation, User
    from bec_atlas.router.base_router import CollectionQueryParams


def get_user_groups_with_personal(user: User) -> list[str]:
    """
    Get the complete list of groups for a user including personal username and auth_user.

    Args:
        user: The user object

    Returns:
        list[str]: List of groups including username and auth_user
    """
    groups = set(user.groups if user.groups else [])
    groups.add("auth_user")
    if user.username and user.username != "admin":
        groups.add(user.username)
    return list(groups)


def is_objectid_compatible(annotation: type) -> bool:
    """
    Check if a type annotation is compatible with ObjectId.
    This function checks if the annotation is directly an ObjectId or if it's a Union that includes ObjectId.
    Args:
        annotation (type): The type annotation to check.
    Returns:
        bool: True if the annotation is ObjectId or a Union that includes ObjectId, False otherwise.
    """
    if annotation is ObjectId:
        return True

    origin = get_origin(annotation)

    if origin is Union or origin is UnionType:
        return any(arg is ObjectId for arg in get_args(annotation))

    return False


def resolve_relation(
    field_name: str,
    relation: Relation,
    params: CollectionQueryParams | None = None,
    user: User | None = None,
) -> list[dict]:
    """
    Generate a MongoDB $lookup aggregation pipeline for resolving relations.

    Handles both outbound relations (where the local document holds a reference to a foreign document)
    and inbound relations (where foreign documents reference the local document).

    Args:
        field_name (str): The name of the field in the model that will hold the resolved data.
        relation (Relation): The relation definition from the model's __relations__ attribute.
        params (CollectionQueryParams | None): Optional query parameters including filter, fields, sort,
                                               limit, offset, and nested includes.
        user (User | None): The user making the request. If provided, adds access control filtering
                           to the lookup pipeline.

    Returns:
        list[dict]: A list of MongoDB aggregation stages including $lookup and optionally $unwind.

    Examples:
        Outbound: session.experiment_id -> experiments._id
        Inbound: session._id -> messaging_services.parent_id
        Nested: session.experiment -> experiment.some_relation
    """
    pipeline = []

    # Determine local field and setup based on relation direction
    if relation.direction == "outbound":
        # Local document holds the reference
        let_variable = f"{relation.local_field}_value"
        local_expression = f"${relation.local_field}"
        match_conditions = [
            {"$ne": [f"$${let_variable}", None]},  # Ensure reference exists
            {"$eq": [f"${relation.foreign_field}", f"$${let_variable}"]},
        ]
    else:  # inbound
        # Foreign documents hold reference to us
        let_variable = "local_id"
        local_expression = "$_id"
        match_conditions = [{"$eq": [f"${relation.foreign_field}", f"$${let_variable}"]}]

    # Add optional filter
    if params:
        parsed_filter = params.parsed_filter()
        if parsed_filter:
            match_conditions.append(parsed_filter)

    # Build the lookup pipeline
    lookup_pipeline = []

    # Add user access control as the first stage in lookup (if applicable)
    if user is not None and "admin" not in user.groups:
        user_groups = get_user_groups_with_personal(user)
        access_filter = {
            "$match": {
                "$or": [
                    {"owner_groups": {"$in": user_groups}},
                    {"access_groups": {"$in": user_groups}},
                ]
            }
        }
        lookup_pipeline.append(access_filter)

    # Add match conditions for the relation
    lookup_pipeline.append({"$match": {"$expr": {"$and": match_conditions}}})

    # Handle nested includes
    if params and params.include and relation.reference_model:
        # Resolve the reference model if it's a lambda
        ref_model = (
            relation.reference_model()
            if callable(relation.reference_model)
            else relation.reference_model
        )

        if hasattr(ref_model, "__relations__"):
            for nested_field, nested_params in params.include.items():
                if nested_field in ref_model.__relations__:
                    nested_relation = ref_model.__relations__[nested_field]
                    nested_pipeline = resolve_relation(
                        nested_field, nested_relation, params=nested_params, user=user
                    )
                    lookup_pipeline.extend(nested_pipeline)

    if params:
        parsed_sort = params.parsed_sort()
        if parsed_sort:
            lookup_pipeline.append({"$sort": parsed_sort})

    if params and params.offset:
        lookup_pipeline.append({"$skip": params.offset})
    if params and params.limit:
        lookup_pipeline.append({"$limit": params.limit})

    if params and params.fields:
        projection = {field: 1 for field in params.fields}
        lookup_pipeline.append({"$project": projection})

    # Create the $lookup stage
    lookup_stage = {
        "$lookup": {
            "from": relation.reference_collection,
            "let": {let_variable: local_expression},
            "pipeline": lookup_pipeline,
            "as": field_name,
        }
    }

    pipeline.append(lookup_stage)

    # Unwind for 1-1 relationships
    if relation.relationship == "1-1":
        pipeline.append({"$unwind": {"path": f"${field_name}", "preserveNullAndEmptyArrays": True}})

    return pipeline


def build_relation_pipeline(
    model: Type[MongoBaseModel],
    field_name: str,
    params: CollectionQueryParams | None = None,
    user: User | None = None,
) -> list[dict]:
    """
    Build an aggregation pipeline for a relation using the appropriate resolution function.

    Args:
        model (Type[MongoBaseModel]): The model class that contains the __relations__ attribute.
        field_name (str): The name of the field/relation to resolve (should match a key in __relations__).
        params (CollectionQueryParams | None): Optional query parameters including filter, fields, sort,
                                               limit, offset, and nested includes.
        user (User | None): The user making the request. If provided, adds access control filtering
                           to all lookup pipelines.

    Returns:
        list[dict]: A list of MongoDB aggregation stages.

    Raises:
        KeyError: If field_name is not found in the model's __relations__ attribute.

    Examples:
        # Simple relation
        build_relation_pipeline(Session, "experiment")

        # With query parameters
        build_relation_pipeline(Session, "experiment", CollectionQueryParams(limit=10))

        # Nested relation: resolve session.experiment and experiment.some_nested_field
        build_relation_pipeline(
            Session,
            "experiment",
            CollectionQueryParams(include={"some_nested_field": CollectionQueryParams()}),
            user=current_user
        )
    """
    if not hasattr(model, "__relations__") or field_name not in model.__relations__:
        raise KeyError(
            f"Field '{field_name}' not found in {model.__name__}.__relations__. "
            f"Available relations: {list(model.__relations__.keys()) if hasattr(model, '__relations__') else []}"
        )

    relation = model.__relations__[field_name]
    return resolve_relation(field_name, relation, params, user)


def build_aggregation_pipeline(
    model: Type[MongoBaseModel],
    params: CollectionQueryParams | None = None,
    user: User | None = None,
) -> list[dict]:
    """
    Build a complete MongoDB aggregation pipeline from CollectionQueryParams.

    Handles user access control, filtering, relation resolution (includes), sorting,
    pagination, and field projection in the correct order for optimal query execution.

    Args:
        model (Type[MongoBaseModel]): The model class that contains the __relations__ attribute.
        params (CollectionQueryParams | None): Query parameters including filter, fields, sort,
                                               limit, offset, and includes for relation resolution.
        user (User | None): The user making the request. If provided, adds access control filtering.

    Returns:
        list[dict]: A complete MongoDB aggregation pipeline.

    Examples:
        # Simple query with filter and pagination
        pipeline = build_aggregation_pipeline(
            Session,
            CollectionQueryParams(filter='{"status": "active"}', limit=10),
            user=current_user
        )

        # Query with relation includes
        pipeline = build_aggregation_pipeline(
            Session,
            CollectionQueryParams(
                include={
                    "experiment": CollectionQueryParams(),
                    "messaging_services": CollectionQueryParams(limit=5)
                }
            ),
            user=current_user
        )
    """
    pipeline = []

    # 0. Add user access control filter (must be first for security)
    if user is not None and "admin" not in user.groups:
        user_groups = get_user_groups_with_personal(user)
        access_filter = {
            "$or": [{"owner_groups": {"$in": user_groups}}, {"access_groups": {"$in": user_groups}}]
        }
        pipeline.append({"$match": access_filter})

    if not params:
        return pipeline

    # 1. Add match stage for root-level filtering (should be first for performance)
    parsed_filter = params.parsed_filter()
    if parsed_filter:
        # Convert string IDs to ObjectIds in the filter if the model's field types require it
        for field_name, val in parsed_filter.items():
            field_info = model.model_fields.get(field_name)
            if not field_info:
                for finfo in model.model_fields.values():
                    if finfo.alias == field_name:
                        field_info = finfo
                        break
            if (
                field_info
                and is_objectid_compatible(field_info.annotation)
                and isinstance(val, str)
            ):
                try:
                    parsed_filter[field_name] = ObjectId(val)
                except Exception as exc:
                    raise ValueError(f"Invalid ObjectId for field '{field_name}': {exc}") from exc
        pipeline.append({"$match": parsed_filter})

    # 2. Add relation lookups (includes)
    if params.include and hasattr(model, "__relations__"):
        for field_name, nested_params in params.include.items():
            if field_name in model.__relations__:
                pipeline.extend(build_relation_pipeline(model, field_name, nested_params, user))

    # 3. Add sorting
    parsed_sort = params.parsed_sort()
    if parsed_sort:
        pipeline.append({"$sort": parsed_sort})

    # 4. Add pagination
    if params.offset:
        pipeline.append({"$skip": params.offset})
    if params.limit:
        pipeline.append({"$limit": params.limit})

    # 5. Add field projection (should be last to reduce data transfer)
    if params.fields:
        projection = {field: 1 for field in params.fields}
        pipeline.append({"$project": projection})

    return pipeline
