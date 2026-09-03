# playbooks/tls

Certificate distribution.

| Playbook | Status | Purpose |
|---|---|---|
| `cert_distribute.yml` | planned | Distribute a single wildcard certificate to many hosts from one issuing point, with per-host ownership and mode. |

## Pattern

One issuance point holding the account credentials, obtaining a wildcard via a
DNS-01 challenge, then fanning the result out. This removes the need for an
inbound port forward to every host, which is the main reason per-host issuance
becomes a security liability at scale.

Ownership and mode are per-host variables, not constants. A service running as
a non-root user needs group read on the key, and the group differs by host. A
single hardcoded mode either breaks the service or over-shares the key.
