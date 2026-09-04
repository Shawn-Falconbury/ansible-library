# 05. `ansible_become: false` in group_vars silently drops privilege

> **Category:** Variable precedence · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

Same precedence family as above, with a nastier outcome: tasks run
unprivileged, many of them partially succeed, and the failure surfaces much
later as inconsistent state. Play-level `become: true` does not rescue it.

---

← [04. ansible_connection in group_vars outranks a play-level connection:](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection) · [All gotchas](Gotchas) · [06. | int on a formatted string returns 0 and causes false PASSes](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes) →
