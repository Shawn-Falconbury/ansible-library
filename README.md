# Ansible Network & Systems Reference

Reference implementations of network and systems automation patterns, written
to be read as much as run.

Every playbook here is a clean-room implementation. Nothing in this repository
is a sanitised copy of a working environment — no real address, hostname,
credential, or organisation name has ever been committed, and CI enforces that
on every push. What is preserved is the *technique* and, more usefully, the
reasoning behind it.

Most of these playbooks exist because the obvious implementation was wrong in a
way that produced a passing result. Those cases are documented inline, at the
point where the mistake would otherwise be made.

## Start here

If you are looking for the single most useful file, it is
**[docs/gotchas.md](docs/gotchas.md)** — the collected failure modes, each one
of which cost real debugging time to find.

## What do you want to do?

| Goal | Playbook |
|---|---|
| Confirm every device is genuinely reachable | [`playbooks/network/reachability_check.yml`](playbooks/network/reachability_check.yml) |
| Audit devices against a config and version baseline | `playbooks/network/baseline_compliance.yml` |
| Build a device inventory over SSH | `playbooks/network/device_inventory.yml` |
| Build a device inventory over SNMPv3 | `playbooks/network/device_inventory_snmp.yml` |
| Discover which SNMP OIDs a platform actually answers | `playbooks/network/snmp_capability_probe.yml` |
| Manage the SSH known-hosts trust store declaratively | `playbooks/network/host_key_trust.yml` |
| Collect and archive Linux host facts | `playbooks/linux/fact_collection.yml` |
| Apply package updates with a verification gate | `playbooks/linux/package_updates.yml` |
| Enumerate listening services across a fleet | `playbooks/linux/listener_sweep.yml` |
| Distribute a wildcard certificate to many hosts | `playbooks/tls/cert_distribute.yml` |
| Monitor service health and certificate expiry | `playbooks/reporting/service_health.yml` |

Playbooks are grouped by function rather than by the environment they came
from. Each directory has its own README describing the group.

## Layout

```
docs/            Conventions, and the gotchas catalogue
inventory/       Example inventory and group_vars (.example only)
vars/            Example variable files (.example only)
playbooks/
  network/       Cisco IOS / IOS-XE
    tasks/       Task files: collection and evaluation, included not run
    templates/   Jinja2 report templates for these playbooks
  linux/         Linux hosts over SSH
  tls/           Certificate distribution
  reporting/     Health reporting and notification
roles/           Reusable roles
scripts/         Helper scripts, including the leak checker
tests/           Test harness, fixtures, and negative cases
```

## Running any of this

```bash
git clone <this-repo> && cd ansible-reference

cp ansible.cfg.example ansible.cfg
cp inventory/hosts.yml.example inventory/hosts.yml
for f in inventory/group_vars/*.example vars/*.example; do cp "$f" "${f%.example}"; done

ansible-galaxy collection install -r requirements.yml
```

Then edit the copied files. Every value in an `.example` file is a placeholder
that must be replaced — see [docs/conventions.md](docs/conventions.md) for what
the placeholder forms mean.

Filled-in copies are gitignored. Only `.example` files are tracked, so a real
inventory cannot be committed by forgetting to add it to `.gitignore`.

Verified against ansible-core 2.16 and 2.17.

Templates live in a `templates/` directory beside the playbooks that use
them, not in one at the repository root. Ansible's template lookup searches
there automatically, so playbooks reference a bare filename and stay
correct if the directory moves. A root-level `templates/` forces
`src: ../../templates/x.j2`, which breaks on any relocation.

## The rule this repository runs on

**No real environment data, ever — not in a file, not in a commit message, not
in an issue.**

This is enforced, not merely requested. `scripts/leak_check.py` scans the whole
tree for addresses outside the RFC 5737 documentation ranges, MAC addresses,
non-`.example` domains, and credential-shaped assignments. It runs in CI on
every push and on a weekly schedule.

The checker is itself tested before it is trusted. `tests/test_leak_check.sh`
asserts the negative path first — the scanner must reject a file of
deliberately planted leaks, category by category — and only then accepts its
clean verdict on the working tree. A scanner that has silently stopped matching
is worse than no scanner, because it converts an active check into a false
assurance.

Run it locally before pushing:

```bash
bash tests/test_leak_check.sh
```

To wire it into `pre-commit`, see [docs/conventions.md](docs/conventions.md).

## Publishing this repository

```bash
bash scripts/bootstrap_repo.sh --remote git@github.com:USER/REPO.git
```

The script creates a fresh history, refuses to commit if the test suite fails,
lists exactly what is staged, and stops short of pushing. It also refuses to
run on top of an existing history — scrubbing a working tree does nothing about
what earlier commits contain, and every prior commit in a public repository is
fetchable by anyone who clones it.

Create the GitHub repository **empty**: no README, no `.gitignore`, no licence.
Those exist here, and an auto-generated file forces a merge on the first push.

## Contributing

Read [docs/conventions.md](docs/conventions.md) first. In short: every
configurable value is a documented variable, every playbook opens with a header
block stating what it needs and what breaks if that is wrong, and anything that
was learned the hard way gets written down in `docs/gotchas.md` rather than
being left for the next person to rediscover.

## Licence

MIT. See [LICENSE](LICENSE).
