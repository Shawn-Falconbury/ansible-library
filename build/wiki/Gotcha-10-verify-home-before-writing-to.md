# 10. Verify `$HOME` before writing to `~/`

> **Category:** Secrets and environment · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A file written to `~/.config/something` appears in the git working
tree.

**Cause:** Service accounts frequently have a home directory set to somewhere
unexpected — including a repository root. Anything written to `~/` then lands
under version control, which for a credentials file is a serious problem.

**Fix:** Write to an explicit absolute path outside the repository, and set any
tool's config path explicitly rather than relying on `$HOME` resolution. Under
cron, `$HOME` may differ again from an interactive shell.

---

← [09. Hardcoded no_log: true makes credential failures undebuggable](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable) · [All gotchas](Gotchas) · [11. Scheduler re-runs may pin to the original commit](Gotcha-11-scheduler-re-runs-may-pin-to-the-original-commit) →
