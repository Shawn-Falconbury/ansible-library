# 15. `delegate_to` and `run_once` at play level parse but do not work

> **Category:** Structure and plugin discovery · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A play that looks correct fails at execution with
`'delegate_to' is not a valid attribute for a Play`.

**Cause:** Both are *task* keywords. Placed on a play they are structurally
valid YAML, so linting and review pass them. The failure only appears when the
play runs.

This bites hardest in exactly the situation that motivates using them: a
reporting play against network devices, where `connection: local` does not work
([gotcha 4](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection)) and `delegate_to: localhost` is the correct substitute. Putting it
where `connection:` would have gone is the natural mistake.

**Fix:** Apply per task.

```yaml
# Wrong -- parses, then fails at run time
- name: Render the report
  hosts: ios_devices
  run_once: true
  delegate_to: localhost
  tasks:
    - ansible.builtin.template: ...

# Right
- name: Render the report
  hosts: ios_devices
  tasks:
    - ansible.builtin.template: ...
      run_once: true
      delegate_to: localhost
```

`ansible-playbook --syntax-check` catches this. Run it in CI.

---

← [14. Plaintext vars can silently shadow a vaulted variable](Gotcha-14-plaintext-vars-can-silently-shadow-a-vaulted-variable) · [All gotchas](Gotchas) · [16. SKIP rolled up into PASS](Gotcha-16-skip-rolled-up-into-pass) →
