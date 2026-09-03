# playbooks/network

Cisco IOS / IOS-XE automation over `network_cli` and SNMPv3.

| Playbook | Status | Purpose |
|---|---|---|
| `reachability_check.yml` | complete | Verify devices are genuinely reachable. Splits by host class because `ansible.builtin.ping` does not test a `network_cli` device. |
| `baseline_compliance.yml` | complete | Audit IOS version and configuration against `vars/baseline.yml`. Selectable SSH or SNMPv3 transport. Collection and evaluation are separate files so the logic is testable without hardware. |
| `device_inventory.yml` | planned | Device inventory over SSH, rendered to HTML. |
| `device_inventory_snmp.yml` | planned | SNMPv3 counterpart to the above. |
| `snmp_capability_probe.yml` | planned | Modular probe matrix establishing which OIDs a platform family actually answers, with per-family fallback where a probe is unsupported. |
| `host_key_trust.yml` | planned | Declarative management of the SSH known-hosts trust store, with git as the authoritative anchor. |

## Before running anything here

`inventory/group_vars/ios_devices.yml` must set `ansible_network_os` and
`ansible_connection`. Both are required; a missing `ansible_network_os`
produces a connection-plugin error that looks like a device timeout, which
reports as a false positive.

## Reading order

Start with `reachability_check.yml`. It is the shortest playbook here and its
header block covers the two precedence traps that affect every other playbook
in this directory.

## Transport coverage

`baseline_compliance.yml` runs over SSH or SNMPv3, and **the two are not
interchangeable**:

| check | ssh | snmp |
|---|---|---|
| `ios_version` | yes | yes |
| `config_saved` | SKIP | yes |
| `required_config` | yes | SKIP |
| `forbidden_config` | yes | SKIP |

IOS exposes no clean CLI equivalent of the config-saved timestamps, and SNMP
does not return the running configuration. Run both and diff the reports before
any transport cutover — a swap changes which checks are evaluated at all, and a
report where PASSes became SKIPs is easy to miss if you only watch the failure
count.

## Testing

```bash
ansible-playbook -i localhost, tests/test_baseline_logic.yml
```

Ten fixture cases, fifty assertions, no hardware. See `tests/README.md`.
