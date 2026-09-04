# 03. Unreachable hosts have no facts — do not default them to zero

> **Category:** Reachability and reporting · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A dead host appears in the report with `0 errors, 0 warnings,
uptime 0` and reads as the healthiest device in the fleet.

**Cause:** Applying `| default(0)` to a metric for a host that never responded
produces a number. A number renders as a measurement. There is nothing in the
output to distinguish "measured zero" from "never measured".

**Fix:** In the template, branch on reachability *before* touching metric
fields, and omit the columns entirely rather than defaulting them. See
`templates/reachability_report.txt.j2`.

---

← [02. Unreachable hosts are removed from the play before tasks are evaluated](Gotcha-02-unreachable-hosts-are-removed-from-the-play-before-tasks-are-evaluated) · [All gotchas](Gotchas) · [04. ansible_connection in group_vars outranks a play-level connection:](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection) →
