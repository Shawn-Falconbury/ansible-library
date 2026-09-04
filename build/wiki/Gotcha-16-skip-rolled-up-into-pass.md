# 16. `SKIP` rolled up into `PASS`

> **Category:** Evaluation logic · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A compliance report shows every device compliant. Several were
never actually evaluated.

**Cause:** Treating "could not evaluate" as "no problem found". A check that
was unable to run has not passed, but if the summary only counts FAILs, an
unevaluated device is indistinguishable from a clean one.

**Fix:** Make SKIP a first-class status, count it separately, and have the
device-level verdict degrade to SKIP if any individual check skipped. Fail the
run on SKIP by default — unknown is not acceptable.

This is the same error as [gotcha 6](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes) one level up the stack: there, a blind
comparison reported PASS; here, a blind *device* is rolled into the compliant
count.

---

← [15. delegate_to and run_once at play level parse but do not work](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work) · [All gotchas](Gotchas) · [17. ansible-galaxy reads collections_path, but only if ansible.cfg exists yet](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet) →
