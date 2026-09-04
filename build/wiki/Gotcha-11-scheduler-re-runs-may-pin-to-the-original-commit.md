# 11. Scheduler re-runs may pin to the original commit

> **Category:** Setup and CI ordering · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A fix is committed and pushed, the job is re-run, and the old
behaviour persists.

**Cause:** Some CI and scheduling front-ends re-run a historical job at the
commit that job originally used. Re-running from history replays the bug.

**Fix:** Launch a fresh run from the template or pipeline definition, not from
the run history.

---

← [10. Verify $HOME before writing to ~/](Gotcha-10-verify-home-before-writing-to) · [All gotchas](Gotchas) · [12. Unpinned collections re-resolve on every run](Gotcha-12-unpinned-collections-re-resolve-on-every-run) →
