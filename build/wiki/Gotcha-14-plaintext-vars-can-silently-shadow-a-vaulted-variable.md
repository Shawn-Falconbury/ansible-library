# 14. Plaintext vars can silently shadow a vaulted variable

> **Category:** Variable precedence · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** Credentials are rotated in the vault and nothing changes.

**Cause:** A leftover definition of the same variable name in a plaintext vars
file takes precedence, and there is no warning about the shadowing.

**Fix:** Audit both files whenever a credential variable misbehaves. Confirm
the effective value:

```bash
ansible -m debug -a 'var=some_credential_var' <group>
```

---

← [13. git-receive-pack does not inherit command-scope -c config](Gotcha-13-git-receive-pack-does-not-inherit-command-scope-c-config) · [All gotchas](Gotchas) · [15. delegate_to and run_once at play level parse but do not work](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work) →
