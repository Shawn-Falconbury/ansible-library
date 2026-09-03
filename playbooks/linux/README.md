# playbooks/linux

Linux host automation over SSH.

| Playbook | Status | Purpose |
|---|---|---|
| `fact_collection.yml` | planned | Gather and archive host facts as a machine-readable inventory source. |
| `package_updates.yml` | planned | Apply updates with a pre-flight gate and post-update verification. |
| `listener_sweep.yml` | planned | Enumerate listening sockets across the fleet and diff against an expected set. |

Unlike the network playbooks, `ansible.builtin.ping` is a valid connectivity
test here — the module is copied to the target and executed there. See
`docs/gotchas.md` entry 1 for why that distinction matters.
