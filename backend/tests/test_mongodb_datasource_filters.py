from bec_atlas.model.model import User


def _extract_groups(user_filter: dict) -> set[str]:
    clauses = user_filter["$or"]
    groups = set()
    for clause in clauses:
        _, condition = next(iter(clause.items()))
        groups.update(condition["$in"])
    return groups


def test_add_user_filter_combines_query_and_user_filter_for_read(backend):
    _, app = backend
    mongo = app.datasources.mongodb
    user = User(
        email="operator@bec_atlas.ch",
        groups=["beamline_staff", "p12345"],
        owner_groups=["admin"],
        access_groups=["admin"],
        first_name="Operator",
        last_name="User",
        username="operator",
    )
    query_filter = {"scope": "global"}

    combined_filter = mongo.add_user_filter(user, query_filter, operation="r")

    assert "$and" in combined_filter
    assert combined_filter["$and"][0] == query_filter
    user_filter = combined_filter["$and"][1]
    assert "$or" in user_filter
    assert _extract_groups(user_filter) == {"beamline_staff", "p12345", "auth_user", "operator"}


def test_add_user_filter_combines_query_and_user_filter_for_write(backend):
    _, app = backend
    mongo = app.datasources.mongodb
    user = User(
        email="operator@bec_atlas.ch",
        groups=["beamline_staff", "p12345"],
        owner_groups=["admin"],
        access_groups=["admin"],
        first_name="Operator",
        last_name="User",
        username="operator",
    )
    query_filter = {"scope": "global"}

    combined_filter = mongo.add_user_filter(user, query_filter, operation="w")

    assert "$and" in combined_filter
    assert combined_filter["$and"][0] == query_filter
    user_filter = combined_filter["$and"][1]
    assert "$or" in user_filter
    assert len(user_filter["$or"]) == 1
    assert "owner_groups" in user_filter["$or"][0]
    assert set(user_filter["$or"][0]["owner_groups"]["$in"]) == {
        "beamline_staff",
        "p12345",
        "auth_user",
        "operator",
    }


def test_add_user_filter_does_not_combine_for_admin(backend):
    _, app = backend
    mongo = app.datasources.mongodb
    admin_user = User(
        email="admin@bec_atlas.ch",
        groups=["admin"],
        owner_groups=["admin"],
        access_groups=["admin"],
        first_name="Admin",
        last_name="User",
        username="admin",
    )
    query_filter = {"scope": "global"}

    combined_filter = mongo.add_user_filter(admin_user, query_filter, operation="r")

    assert combined_filter == query_filter


def test_add_user_filter_with_none_query_returns_user_filter(backend):
    _, app = backend
    mongo = app.datasources.mongodb
    user = User(
        email="operator@bec_atlas.ch",
        groups=["beamline_staff", "p12345"],
        owner_groups=["admin"],
        access_groups=["admin"],
        first_name="Operator",
        last_name="User",
        username="operator",
    )

    combined_filter = mongo.add_user_filter(user, None, operation="r")

    assert "$or" in combined_filter
    assert "$and" not in combined_filter
    assert _extract_groups(combined_filter) == {"beamline_staff", "p12345", "auth_user", "operator"}
