from types import SimpleNamespace
from unittest.mock import patch

from bec_atlas.router.user_router import UserRouter
from bec_atlas.utils.ldap_auth import ATTRIBUTES, LDAPUserService, make_server, make_server_pool
from ldap3 import BASE, SUBTREE


def _make_entry(**attrs):
    return SimpleNamespace(entry_attributes_as_dict=attrs)


def test_authenticate_username_escapes_rdn_and_uses_base_scope():
    captured = {}

    class FakeConnection:
        def __init__(self, server, user, password):
            captured["server"] = server
            captured["user"] = user
            captured["password"] = password
            self.entries = [_make_entry(cn=["alice,ops"], mail=["alice@example.com"], memberOf=[])]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self):
            return True

        def search(self, search_base, search_filter, search_scope, attributes):
            captured["search_base"] = search_base
            captured["search_filter"] = search_filter
            captured["search_scope"] = search_scope
            captured["attributes"] = attributes
            return True

    service = LDAPUserService("ldaps://d.psi.ch", "OU=users,DC=example,DC=com")

    with patch("bec_atlas.utils.ldap_auth.Connection", FakeConnection):
        user = service.authenticate_and_get_info("alice,ops", "secret")

    assert captured["user"] == r"CN=alice\,ops,OU=users,DC=example,DC=com"
    assert captured["search_base"] == captured["user"]
    assert captured["search_filter"] == "(objectClass=*)"
    assert captured["search_scope"] == BASE
    assert captured["attributes"] == ATTRIBUTES
    assert user["username"] == "alice,ops"


def test_authenticate_upn_escapes_filter_but_not_bind_dn():
    captured = {}

    class FakeConnection:
        def __init__(self, server, user, password):
            captured["user"] = user
            self.entries = [
                _make_entry(
                    cn=["alice"],
                    mail=["alice@example.com"],
                    givenName=["Alice"],
                    sn=["Doe"],
                    memberOf=["CN=beamline,OU=Groups,DC=example,DC=com"],
                )
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self):
            return True

        def search(self, search_base, search_filter, search_scope, attributes):
            captured["search_base"] = search_base
            captured["search_filter"] = search_filter
            captured["search_scope"] = search_scope
            captured["attributes"] = attributes
            return True

    service = LDAPUserService("ldaps://d.psi.ch", "OU=users,DC=example,DC=com")
    principal = "alice*)(mail=*)@example.com"

    with patch("bec_atlas.utils.ldap_auth.Connection", FakeConnection):
        user = service.authenticate_and_get_info(principal, "secret")

    assert captured["user"] == principal
    assert captured["search_base"] == "OU=users,DC=example,DC=com"
    assert captured["search_filter"] == r"(userPrincipalName=alice\2a\29\28mail=\2a\29@example.com)"
    assert captured["search_scope"] == SUBTREE
    assert captured["attributes"] == ATTRIBUTES
    assert user["roles"] == ["beamline"]


def test_make_server_accepts_hostname_and_full_url():
    from_host = make_server("dc00.d.psi.ch")
    from_url = make_server("ldaps://d.psi.ch")

    assert from_host.host == "dc00.d.psi.ch"
    assert from_host.ssl is True
    assert from_url.host == "d.psi.ch"
    assert from_url.ssl is True


def test_make_server_pool_tries_hosts_once_per_auth_attempt():
    pool = make_server_pool(["dc00.d.psi.ch", "dc01.d.psi.ch", "dc02.d.psi.ch"])

    assert pool.active == 1
    assert pool.exhaust is False
    assert len(pool.servers) == 3


def test_user_router_configures_ldap_server_pool_hosts():
    datasources = SimpleNamespace(mongodb=object())

    with patch("bec_atlas.router.user_router.LDAPUserService") as ldap_service:
        UserRouter(datasources, use_ssl=False)

    ldap_service.assert_called_once_with(
        ldap_server=["dc00.d.psi.ch", "dc01.d.psi.ch", "dc02.d.psi.ch"],
        base_dn="OU=users,OU=psi,DC=d,DC=psi,DC=ch",
    )
