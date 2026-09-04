# 09. Hardcoded `no_log: true` makes credential failures undebuggable

> **Category:** Secrets and environment · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

`no_log` is correct for tasks handling secrets and wrong as a permanent
fixture. When such a task fails, the output that would explain why is
suppressed along with the secret.

Make it a variable (`mask_sensitive_output`), pair it with `ignore_errors:
true`, and follow with an `assert` that names the failure. The assertion
message surfaces *what* failed without printing the value.

---

← [08. An empty play is not a passing play](Gotcha-08-an-empty-play-is-not-a-passing-play) · [All gotchas](Gotchas) · [10. Verify $HOME before writing to ~/](Gotcha-10-verify-home-before-writing-to) →
