# 12. Unpinned collections re-resolve on every run

> **Category:** Setup and CI ordering · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** Identical playbook, identical inventory, different behaviour
between two runs with no commit in between.

**Cause:** A scheduler that installs collections from Galaxy at task time will
pick up new releases silently. A major version bump changes module behaviour
with nothing in git to point at.

**Fix:** Pin every collection in `requirements.yml` with an explicit `version:`.

---

← [11. Scheduler re-runs may pin to the original commit](Gotcha-11-scheduler-re-runs-may-pin-to-the-original-commit) · [All gotchas](Gotchas) · [13. git-receive-pack does not inherit command-scope -c config](Gotcha-13-git-receive-pack-does-not-inherit-command-scope-c-config) →
