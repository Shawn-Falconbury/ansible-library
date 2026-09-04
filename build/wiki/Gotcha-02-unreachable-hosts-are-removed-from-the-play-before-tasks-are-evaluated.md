# 02. Unreachable hosts are removed from the play before tasks are evaluated

> **Category:** Reachability and reporting · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A health report shows 100% healthy while devices are down. The
down devices are not listed as failed — they are simply absent.

**Cause:** Ansible drops unreachable hosts from the play. They do not fail
tasks; they stop being iterated over. Any report built by looping over the
surviving hosts cannot see them, and their absence reads as success.

**Fix:** Diff the host list the play *started* with against the one still
standing.

```yaml
_hosts_vanished: "{{ ansible_play_hosts_all | difference(ansible_play_hosts) }}"
```

Report the diff explicitly and assert on it.

---

← [01. ansible.builtin.ping is not a connectivity test for network devices](Gotcha-01-ansible-builtin-ping-is-not-a-connectivity-test-for-network-devices) · [All gotchas](Gotchas) · [03. Unreachable hosts have no facts — do not default them to zero](Gotcha-03-unreachable-hosts-have-no-facts-do-not-default-them-to-zero) →
