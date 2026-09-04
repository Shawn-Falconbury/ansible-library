# Playbook catalogue

Playbooks are grouped by function rather than by the environment they came
from. Each directory has its own README describing the group.

Status is stated honestly: **complete** means it has fixture-driven tests and
passes CI. **Planned** means the pattern is documented but the playbook is not
in the tree yet.

---

## `playbooks/network/` — Cisco IOS / IOS-XE

Over `network_cli` and SNMPv3.

| Playbook | Status | Purpose |
|---|---|---|
| `reachability_check.yml` | ✅ complete | Verify devices are *genuinely* reachable. Splits by host class because `ansible.builtin.ping` does not test a `network_cli` device. |
| `baseline_compliance.yml` | ✅ complete | Audit IOS version and configuration against `vars/baseline.yml`. Selectable SSH or SNMPv3 transport. Collection and evaluation are separate task files so the logic is testable without hardware. |
| `device_inventory.yml` | 🔜 planned | Device inventory over SSH, rendered to HTML. |
| `device_inventory_snmp.yml` | 🔜 planned | SNMPv3 counterpart to the above. |
| `snmp_capability_probe.yml` | 🔜 planned | Modular probe matrix establishing which OIDs a platform family actually answers, with per-family fallback where a probe is unsupported. |
| `host_key_trust.yml` | 🔜 planned | Declarative management of the SSH known-hosts trust store, with git as the authoritative anchor. |

**Reading order:** start with `reachability_check.yml`.

### Transport coverage is not symmetric

`baseline_compliance.yml` runs over SSH or SNMPv3, and **the two are not
interchangeable**:

| Check | SSH | SNMPv3 |
|---|:---:|:---:|
| `ios_version` | ✅ | ✅ |
| `config_saved` | ⚠️ SKIP | ✅ |
| `required_config` | ✅ | ⚠️ SKIP |
| `forbidden_config` | ✅ | ⚠️ SKIP |

IOS exposes no clean CLI equivalent of the config-saved timestamps, and SNMP
does not return the running configuration.

Run both and diff the reports before any transport cutover. A swap changes
*which checks are evaluated at all*, and a report where PASSes became SKIPs is
easy to miss if you only watch the failure count — which is
[Gotcha 16](Gotcha-16-skip-rolled-up-into-pass) waiting to happen at the
organisational level rather than the code level.

---

## `playbooks/linux/` — Linux hosts over SSH

| Playbook | Status | Purpose |
|---|---|---|
| `fact_collection.yml` | 🔜 planned | Gather and archive host facts as a machine-readable inventory source. |
| `package_updates.yml` | 🔜 planned | Apply updates with a pre-flight gate and post-update verification. |
| `listener_sweep.yml` | 🔜 planned | Enumerate listening sockets across the fleet and diff against an expected set. |

Unlike the network playbooks, `ansible.builtin.ping` **is** a valid
connectivity test here — the module is copied to the target and executed there.
→ [Gotcha 01](Gotcha-01-ansible-builtin-ping-is-not-a-connectivity-test-for-network-devices)

---

## `playbooks/tls/` — Certificate distribution

| Playbook | Status | Purpose |
|---|---|---|
| `cert_distribute.yml` | 🔜 planned | Distribute a single wildcard certificate to many hosts from one issuing point, with per-host ownership and mode. |

**Pattern:** one issuance point holding the account credentials obtains a
wildcard via a DNS-01 challenge, then fans the result out. This removes the
need for an inbound port forward to every host, which is the main reason
per-host issuance becomes a security liability at scale.

Ownership and mode are per-host variables, not constants. A service running as
a non-root user needs group read on the key, and the group differs by host. A
single hardcoded mode either breaks the service or over-shares the key.

---

## `playbooks/reporting/` — Health reporting and notification

| Playbook | Status | Purpose |
|---|---|---|
| `service_health.yml` | 🔜 planned | Service and certificate-expiry monitoring with unreachable-host detection. |

**Reporting playbooks are where silent failures concentrate**, because their
output is a document that looks the same whether or not it is correct. Three
rules apply to everything in this directory:

- `ignore_errors` / `ignore_unreachable` so failed hosts stay visible. Letting
  the play abort turns a partial outage into no report at all.
- Unreachable hosts detected via the `ansible_play_hosts_all` diff, never by
  absence from a loop.
  → [Gotcha 02](Gotcha-02-unreachable-hosts-are-removed-from-the-play-before-tasks-are-evaluated)
- Metric fields **omitted** for unreachable hosts, never defaulted to zero. A
  zero renders as a measurement and reads as the healthiest device in the
  fleet.
  → [Gotcha 03](Gotcha-03-unreachable-hosts-have-no-facts-do-not-default-them-to-zero)

---

## Supporting components

| Path | What it is |
|---|---|
| `filter_plugins/network_mask.py` | Address-masking filters for dual-render reports. Must be declared in `ansible.cfg` — → [Gotcha 18](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root) |
| `playbooks/network/tasks/` | Collection and evaluation task files, included rather than run, so evaluation is testable against fixtures |
| `playbooks/network/templates/` | Jinja2 report templates, kept beside the playbooks that use them |
| `scripts/leak_check.py` | The no-real-data enforcer — → [Security model](Security-Model) |
| `scripts/bootstrap_repo.sh` | Publishes with a fresh history; refuses to run on top of an existing one |
| `scripts/verify_published.py` | Post-publish verification of what actually landed |

### Why templates live beside their playbooks

Ansible's template lookup searches a `templates/` directory adjacent to the
playbook automatically, so playbooks reference a bare filename and stay correct
if the directory moves. A root-level `templates/` forces
`src: ../../templates/x.j2`, which breaks on any relocation.

Note that `filter_plugins/` does **not** work the same way, and that asymmetry
is exactly what makes [Gotcha 18](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root)
expensive to diagnose.
