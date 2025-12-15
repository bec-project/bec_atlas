

# Access Models

## Experiment
- Owner groups: admin
- Access groups: pgroup, sls_<>_bs

Experiments are managed through DUO and should not be modified manually, hence we assign the owner group to admin. 
The access group is assigned to the pgroup and the beamline scientist group. 

## Session
- Owner groups: admin, sls_<>_bs
- Access groups: pgroup (if applicable)

Sessions are created when a new account is set in BEC. 

## Scan
- Owner groups: admin
- Access groups: pgroup (if applicable), sls_<>_bs

Scan access groups are inherited from the session. Since scans are 'official' data products, we assign the owner group to admin.

## Deployment
- Owner groups: admin, sls_<>_bs
- Access groups: auth_user

Deployments are managed through auto-deployment but contain information that a beamline scientist may want to edit. It does not contain sensitive information, hence we assign the owner group to admin and the access group to auth_user, which means that all authenticated users can see it.

## Deployment Access
- Owner groups: admin, sls_<>_bs
- Access groups: None

Deployment access defines the ACL permissions for accessing BEC. Beamline scientists should be able to edit it but we don't need to make it public.

## Realm
- Owner groups: admin
- Access groups: auth_user
Realms are managed through auto-deployment and do not contain sensitive information, hence we assign the owner group to admin and the access group to auth_user, which means that all authenticated users can see it.