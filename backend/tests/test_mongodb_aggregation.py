from bec_atlas.datasources.mongodb.aggregation_pipelines import resolve_relation
from bec_atlas.model.model import ExperimentPartial, MessagingServicePartial, Relation


def test_deployment_resolution():

    relation = Relation(
        reference_collection="experiments",
        reference_model=ExperimentPartial,
        local_field="experiment_id",
        foreign_field="_id",
        relationship="1-1",
        direction="outbound",
    )

    expected_lookup = [
        {
            "$lookup": {
                "from": "experiments",
                "let": {"experiment_id_value": "$experiment_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$ne": ["$$experiment_id_value", None]},
                                    {"$eq": ["$_id", "$$experiment_id_value"]},
                                ]
                            }
                        }
                    }
                ],
                "as": "experiment",
            }
        },
        {"$unwind": {"path": "$experiment", "preserveNullAndEmptyArrays": True}},
    ]

    assert resolve_relation("experiment", relation) == expected_lookup


def test_deployment_messaging_resolution():

    expected_lookup = [
        {
            "$lookup": {
                "from": "messaging_services",
                "let": {"local_id": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$and": [{"$eq": ["$parent_id", "$$local_id"]}]}}}
                ],
                "as": "messaging_services",
            }
        }
    ]

    relation = Relation(
        reference_collection="messaging_services",
        reference_model=MessagingServicePartial,
        local_field="_id",
        foreign_field="parent_id",
        relationship="1-N",
        direction="inbound",
    )

    assert resolve_relation("messaging_services", relation) == expected_lookup
