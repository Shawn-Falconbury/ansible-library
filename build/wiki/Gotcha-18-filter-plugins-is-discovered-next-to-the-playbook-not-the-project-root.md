# 18. `filter_plugins/` is discovered next to the playbook, not the project root

> **Category:** Structure and plugin discovery · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:**

```
TemplateAssertionError: No filter named 'mask_ip'
```

The plugin file exists, the function is in `FilterModule.filters()`, and the
spelling is right.

**Cause:** Ansible auto-discovers `filter_plugins/` adjacent to the *playbook*.
A project that keeps playbooks in subdirectories -- `playbooks/network/`,
`playbooks/linux/` -- puts the repository-root `filter_plugins/` outside that
search path entirely, so it is never loaded.

**Fix:** Declare it in `ansible.cfg`.

```ini
[defaults]
filter_plugins = ./filter_plugins
```

The error text points at the template, which is the wrong place to look. Nothing
about "no filter named X" suggests a search path.

Note which way this one fails. A missing masking filter raises and the render
stops, which is the *safe* direction -- the report never gets built. Compare
[gotcha 6](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes), where the failure produced a passing check. If you are going to have
a bug in a masking pipeline, this is the one to have.

---

← [17. ansible-galaxy reads collections_path, but only if ansible.cfg exists yet](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet) · [All gotchas](Gotchas)
