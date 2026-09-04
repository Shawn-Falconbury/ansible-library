# 17. `ansible-galaxy` reads `collections_path`, but only if `ansible.cfg` exists yet

> **Category:** Setup and CI ordering · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:**

```
ERROR! couldn't resolve module/action 'cisco.ios.ios_facts'.
This often indicates a misspelling, missing collection, or incorrect
module path.
```

The collection is installed. `ansible-galaxy collection list` shows it.

**Cause:** An ordering dependency between two setup steps. `ansible.cfg` sets
`collections_path = ./collections`, and `ansible-galaxy` honours that setting --
but only if `ansible.cfg` is already on disk when the install runs. In a repo
that ships `ansible.cfg.example` and expects you to copy it, installing before
copying puts the collections in `~/.ansible/collections` while the playbooks
look in `./collections`.

What makes this expensive is the error text. It names three plausible causes --
misspelling, missing collection, incorrect module path -- and the real one is
none of them. The collection is present, spelled correctly, at a valid path;
just not the path this project is configured to search.

**Fix:** Stage the configuration first, then install.

```bash
cp ansible.cfg.example ansible.cfg
ansible-galaxy collection install -r requirements.yml
```

Confirm where they actually landed rather than trusting the success message:

```bash
ansible-galaxy collection list | head -3   # prints the search path in use
```

The same ordering applies in CI. A workflow that installs collections in one
step and materialises config in a later step will fail the syntax check while
every individual step reports success.

---

← [16. SKIP rolled up into PASS](Gotcha-16-skip-rolled-up-into-pass) · [All gotchas](Gotchas) · [18. filter_plugins/ is discovered next to the playbook, not the project root](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root) →
