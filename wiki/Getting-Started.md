# Getting started

## Order matters

Do these in this order. The reason is
[Gotcha 17](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet):
`ansible-galaxy` honours `collections_path` from `ansible.cfg`, but only if
that file is already on disk when the install runs. Installing first puts the
collections in `~/.ansible/collections` while the playbooks look in
`./collections`, and the resulting error names three plausible causes, none of
which is the real one.

```bash
git clone https://github.com/Shawn-Falconbury/ansible-library.git
cd ansible-library

# 1. Stage configuration FIRST
cp ansible.cfg.example ansible.cfg
cp inventory/hosts.yml.example inventory/hosts.yml
for f in inventory/group_vars/*.example vars/*.example; do
  cp "$f" "${f%.example}"
done

# 2. Then install collections
ansible-galaxy collection install -r requirements.yml

# 3. Confirm where they actually landed — do not trust the success message
ansible-galaxy collection list | head -3
```

---

## Fill in the placeholders

Every value in an `.example` file is a placeholder that must be replaced. The
forms are deliberately distinguishable so that "not yet configured" can never
be mistaken for a working value:

| Form | Means |
|---|---|
| RFC 5737 address (`192.0.2.10`, `198.51.100.25`, `203.0.113.7`) | An address you must replace |
| `.example` domain (`sw-a-access-01.lab.example`) | A name you must replace |
| `CHANGEME_` prefix | Must be set before first run; no safe default exists |
| `{{ vault_* }}` | A secret, referenced never inlined |
| RFC 7042 MAC (`00:00:5e:00:53:af`) | A MAC you must replace |

Filled-in copies are gitignored. Only `.example` files are tracked, so a real
inventory cannot be committed by forgetting to add it to `.gitignore`.

Full detail: [Conventions](Conventions) and [Security model](Security-Model).

---

## Required inventory variables

Before anything in `playbooks/network/` will work,
`inventory/group_vars/ios_devices.yml` must set both:

```yaml
ansible_network_os: ios
ansible_connection: ansible.netcommon.network_cli
```

Both are required. A missing `ansible_network_os` produces a connection-plugin
error that looks like a device timeout — which reports as a false positive on
a device that is actually fine.

Be aware that `ansible_connection` set here **outranks a play-level
`connection:` keyword**, silently. So does `ansible_become: false`.
→ [Gotcha 04](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection),
[Gotcha 05](Gotcha-05-ansible-become-false-in-group-vars-silently-drops-privilege)

Verify empirically rather than assuming:

```bash
ansible -m debug -a 'var=ansible_connection' ios_devices
```

---

## First run

Start with `reachability_check.yml`. It is the shortest playbook in the
repository, and its header block covers the two precedence traps that affect
every other playbook there.

```bash
ansible-playbook playbooks/network/reachability_check.yml
```

Then the compliance audit:

```bash
ansible-playbook playbooks/network/baseline_compliance.yml
```

---

## Run the tests before you trust anything

```bash
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/run_tests.sh
```

There is deliberately no search of likely venv locations. Guessing which of
several installed ansible-core versions you meant is exactly what makes "it
passed locally" untrustworthy. Every run prints the interpreter and version it
used.

Two scripts are excluded from `run_tests.sh` because `simulate_ci.sh` wipes
`collections/` and all generated config. Run both before pushing:

```bash
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/simulate_ci.sh
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_bare_lint.sh
```

The baseline logic tests need no hardware at all — ten fixture cases, fifty
assertions:

```bash
ansible-playbook -i localhost, tests/test_baseline_logic.yml
```

More: [Testing philosophy](Testing-Philosophy).

---

## Wire up the leak check locally

```bash
pip install pre-commit && pre-commit install
```

Or run it directly before pushing:

```bash
bash tests/test_leak_check.sh
```

This verifies the scanner against planted leaks *first*, then accepts its clean
verdict on the tree. Running `scripts/leak_check.py` alone tells you less than
you think it does.

---

## Version support

Verified against **ansible-core 2.16 and 2.17**, which is what CI tests.
Running against a much newer core can pass locally and fail there.
