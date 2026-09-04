# 13. `git-receive-pack` does not inherit command-scope `-c` config

> **Category:** Secrets and environment · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** `git -c safe.directory=... push` still fails with an ownership
error on a hook-driven push.

**Cause:** `git-receive-pack` is spawned as a child process and does not
inherit command-scope configuration passed with `-c`.

**Fix:** Set the configuration at system scope on the receiving host.

---

← [12. Unpinned collections re-resolve on every run](Gotcha-12-unpinned-collections-re-resolve-on-every-run) · [All gotchas](Gotchas) · [14. Plaintext vars can silently shadow a vaulted variable](Gotcha-14-plaintext-vars-can-silently-shadow-a-vaulted-variable) →
