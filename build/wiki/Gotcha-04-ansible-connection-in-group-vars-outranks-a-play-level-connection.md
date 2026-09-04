# 04. `ansible_connection` in group_vars outranks a play-level `connection:`

> **Category:** Variable precedence · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A play sets `connection: local` and the tasks still run against
the device — or fail with a connection-plugin error that makes no sense for a
local task.

**Cause:** `ansible_connection` set in `group_vars` has higher precedence than
the play-level `connection:` keyword. The play keyword loses silently.

**Fix:** Use `delegate_to: localhost` for tasks that must run on the control
node. Do not rely on `connection:` to override inventory.

Verify empirically rather than assuming:

```bash
ansible -m debug -a 'var=ansible_connection' ios_devices
```

---

← [03. Unreachable hosts have no facts — do not default them to zero](Gotcha-03-unreachable-hosts-have-no-facts-do-not-default-them-to-zero) · [All gotchas](Gotchas) · [05. ansible_become: false in group_vars silently drops privilege](Gotcha-05-ansible-become-false-in-group-vars-silently-drops-privilege) →
