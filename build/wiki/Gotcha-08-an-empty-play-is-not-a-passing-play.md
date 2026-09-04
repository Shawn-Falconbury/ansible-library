# 08. An empty play is not a passing play

> **Category:** Evaluation logic · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A run completes with no failures and an empty report.

**Cause:** A typo in a group name, or a `--limit` that matches nothing. Ansible
does not consider this an error.

**Fix:** Assert that the play matched a non-zero number of hosts before doing
anything else.

---

← [07. A naive dotted-quad regex fires on IOS image filenames](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames) · [All gotchas](Gotchas) · [09. Hardcoded no_log: true makes credential failures undebuggable](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable) →
