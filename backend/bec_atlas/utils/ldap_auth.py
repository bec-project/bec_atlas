import logging

from ldap3 import BASE, NONE, ROUND_ROBIN, SUBTREE, Connection, Server, ServerPool
from ldap3.core.exceptions import LDAPBindError
from ldap3.utils.dn import escape_rdn

logger = logging.getLogger(__name__)


ATTRIBUTE_MAP = {"cn": "username", "mail": "email", "givenName": "first_name", "sn": "last_name"}
ATTRIBUTES = [*ATTRIBUTE_MAP, "memberOf"]


class LDAPUserService:
    def __init__(self, ldap_server, base_dn):
        server_factory = make_server if isinstance(ldap_server, str) else make_server_pool
        self.server = server_factory(ldap_server)
        self.base_dn = base_dn

    def authenticate_and_get_info(self, principal, password):
        """
        Authenticate the user against the LDAP server and extract user details.
        """
        principal = escape_rdn(principal)  # escape characters to prevent injection
        # Determine DN based on input type
        if "@" in principal:
            # Email login
            bind_dn = principal
            search_base = self.base_dn
            search_filter = f"(userPrincipalName={principal})"
            search_scope = SUBTREE
        else:
            # Standard username login
            bind_dn = f"CN={principal},{self.base_dn}"
            search_base = bind_dn
            search_filter = "(objectClass=*)"
            search_scope = BASE

        try:
            # Authenticate the user
            with Connection(self.server, user=bind_dn, password=password) as user_conn:
                if not user_conn.bind():
                    raise LDAPBindError("Invalid credentials")

                # Search for user information
                user_conn.search(
                    search_base, search_filter, search_scope=search_scope, attributes=ATTRIBUTES
                )
                entry = user_conn.entries[0]

                # Extract user details
                attrs = entry.entry_attributes_as_dict
                user_data = {new: attrs.get(old, [None])[0] for old, new in ATTRIBUTE_MAP.items()}
                user_data["roles"] = [
                    g[3:].split(",", 1)[0] for g in attrs.get("memberOf", []) if g.startswith("CN=")
                ]
                return user_data

        except Exception as e:
            logger.error(f"LDAP authentication failed: {e}")
            return None


def make_server_pool(hosts):
    servers = [make_server(host) for host in hosts]
    return ServerPool(servers, ROUND_ROBIN, active=True, exhaust=True)


def make_server(host):
    return Server(f"ldaps://{host}", get_info=NONE, connect_timeout=5)


if __name__ == "__main__":  # pragma: no cover
    ldap_service = LDAPUserService(
        ldap_server="ldaps://d.psi.ch", base_dn="OU=users,OU=psi,DC=d,DC=psi,DC=ch"
    )

    principal = "username"  # Replace with the username or email
    password = "user_password"  # Replace with the user password

    user_info = ldap_service.authenticate_and_get_info(principal, password)
    if user_info:
        print("User authenticated and details extracted:", user_info)
    else:
        print("Authentication failed or user not found.")
