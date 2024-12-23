from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPBindError


class LDAPUserService:
    def __init__(self, ldap_server, base_dn):
        self.server = Server(ldap_server, get_info=ALL)
        self.base_dn = base_dn

    def authenticate_and_get_info(self, principal, password):
        """
        Authenticate the user against the LDAP server and extract user details.
        """
        # Determine DN based on input type
        if "@" in principal:
            # Email login
            bind_dn = principal
            search_base = self.base_dn
            search_filter = f"(userPrincipalName={principal})"
        else:
            # Standard username login
            bind_dn = f"CN={principal},{self.base_dn}"
            search_base = bind_dn
            search_filter = "(objectClass=*)"

        try:
            # Authenticate the user
            with Connection(self.server, user=bind_dn, password=password) as user_conn:
                if not user_conn.bind():
                    raise LDAPBindError("Invalid credentials")

                # Search for user information
                user_conn.search(
                    search_base,
                    search_filter,
                    search_scope=SUBTREE,
                    attributes=["cn", "mail", "givenName", "sn", "memberOf"],
                )
                entry = user_conn.entries[0]

                # Extract user details
                user_data = {
                    "username": entry.cn.value,
                    "email": entry.mail.value if "mail" in entry else None,
                    "first_name": entry.givenName.value if "givenName" in entry else None,
                    "last_name": entry.sn.value if "sn" in entry else None,
                    "roles": (
                        [group.split(",")[0][3:] for group in entry.memberOf]
                        if "memberOf" in entry
                        else []
                    ),
                }
                return user_data

        except LDAPBindError as e:
            print(f"LDAP authentication failed: {e}")
            return None


if __name__ == "__main__":
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
