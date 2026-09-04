# 01. `ansible.builtin.ping` is not a connectivity test for network devices

> **Category:** Reachability and reporting · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A reachability playbook reports every switch healthy. One of them
has been powered off for months.

**Cause:** `ansible.builtin.ping` is resolved by an action plugin that executes
on the *control node*. Against a host using the `network_cli` connection
plugin, it never opens a session to the device. It returns `pong` regardless of
whether the device exists.

For an SSH-connected Linux host the module is copied to the target and run
there, so it *is* a real test. The behaviour differs entirely by connection
plugin, which is why the same task can be correct in one play and meaningless
in the next.

**Fix:** Use a task that must transact with the device.

```yaml
# Wrong for network_cli hosts
- ansible.builtin.ping:

# Right
- cisco.ios.ios_facts:
    gather_subset: [min]
```

See `playbooks/network/reachability_check.yml`.

---

[All gotchas](Gotchas) · [02. Unreachable hosts are removed from the play before tasks are evaluated](Gotcha-02-unreachable-hosts-are-removed-from-the-play-before-tasks-are-evaluated) →
