# playbooks/linux

Linux host automation over SSH.

| Playbook | Status | Purpose |
|---|---|---|
| `fact_collection.yml` | complete | Gather and archive host facts, with a manifest that names every host whose archive was NOT rewritten. A leftover file parses and reads as current; the manifest is what stops it being believed. |
| `package_updates.yml` | complete | Apply updates with a free-space gate and a post-run re-read of the upgradable list. `apt-get upgrade` exits 0 while holding packages back, so the return code proves nothing. |
| `listener_sweep.yml` | complete | Enumerate listening sockets and diff against a baseline on proto/**address**/port. A port-only diff cannot see a service moving from loopback to every interface. Dual-rendered, leak-scanned. |

Unlike the network playbooks, `ansible.builtin.ping` is a valid connectivity
test here — the module is copied to the target and executed there. See
`docs/gotchas.md` entry 1 for why that distinction matters.
