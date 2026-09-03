# Gotchas

Failure modes that produce a **passing result**. Every entry here was found the
hard way — the code ran, exited zero, and reported success while being wrong.

Ordinary errors are not interesting; they announce themselves. These do not.

---

## 1. `ansible.builtin.ping` is not a connectivity test for network devices

**Symptom:** A reachability playbook reports every switch healthy. One of them
has been powered off for months.

**Cause:** `ansible.builtin.ping` is resolved by an action plugin that executes
on the *control node*. Against a host using the `network_cli` connection
plugin, it never opens a session to the device. It returns `pong` regardless of
whether the device exists.

For an SSH-connected Linux host the module is copied to the target and run
there, so it *is* a real test. The behaviour differs entirely by connection
plugin, which is why the same task can be correct in one play and meaningless
in the next.

**Fix:** Use a task that must transact with the device.

```yaml
# Wrong for network_cli hosts
- ansible.builtin.ping:

# Right
- cisco.ios.ios_facts:
    gather_subset: [min]
```

See `playbooks/network/reachability_check.yml`.

---

## 2. Unreachable hosts are removed from the play before tasks are evaluated

**Symptom:** A health report shows 100% healthy while devices are down. The
down devices are not listed as failed — they are simply absent.

**Cause:** Ansible drops unreachable hosts from the play. They do not fail
tasks; they stop being iterated over. Any report built by looping over the
surviving hosts cannot see them, and their absence reads as success.

**Fix:** Diff the host list the play *started* with against the one still
standing.

```yaml
_hosts_vanished: "{{ ansible_play_hosts_all | difference(ansible_play_hosts) }}"
```

Report the diff explicitly and assert on it.

---

## 3. Unreachable hosts have no facts — do not default them to zero

**Symptom:** A dead host appears in the report with `0 errors, 0 warnings,
uptime 0` and reads as the healthiest device in the fleet.

**Cause:** Applying `| default(0)` to a metric for a host that never responded
produces a number. A number renders as a measurement. There is nothing in the
output to distinguish "measured zero" from "never measured".

**Fix:** In the template, branch on reachability *before* touching metric
fields, and omit the columns entirely rather than defaulting them. See
`templates/reachability_report.txt.j2`.

---

## 4. `ansible_connection` in group_vars outranks a play-level `connection:`

**Symptom:** A play sets `connection: local` and the tasks still run against
the device — or fail with a connection-plugin error that makes no sense for a
local task.

**Cause:** `ansible_connection` set in `group_vars` has higher precedence than
the play-level `connection:` keyword. The play keyword loses silently.

**Fix:** Use `delegate_to: localhost` for tasks that must run on the control
node. Do not rely on `connection:` to override inventory.

Verify empirically rather than assuming:

```bash
ansible -m debug -a 'var=ansible_connection' ios_devices
```

---

## 5. `ansible_become: false` in group_vars silently drops privilege

Same precedence family as above, with a nastier outcome: tasks run
unprivileged, many of them partially succeed, and the failure surfaces much
later as inconsistent state. Play-level `become: true` does not rescue it.

---

## 6. `| int` on a formatted string returns 0 and causes false PASSes

**Symptom:** A threshold check passes on every device, including ones that
should fail.

**Cause:** SNMP TimeTicks and similar values often arrive pre-formatted:

```
9:0:07:42.73
```

`{{ value | int }}` on that returns `0` — no error, no warning. A check of the
form `value | int > threshold` then evaluates against zero and behaves
consistently, wrongly.

**Fix:** Request raw integers where the tool allows it (`snmpget -Ovqt`), and
guard the comparison so a non-numeric value forces a SKIP rather than falling
through to a PASS:

```yaml
_le_numeric: "{{ raw_value is match('^[0-9]+$') }}"
```

Treat `not _le_numeric` as SKIP, never as PASS. A check that cannot evaluate
its input has not passed.

---

## 7. A naive dotted-quad regex fires on IOS image filenames

**Symptom:** A leak scan or address parser flags `cat9k_iosxe.17.06.06.SPA.bin`.

**Cause:** `\d+\.\d+\.\d+\.\d+` matches `17.06.06` in context, and version
strings generally.

**Fix:** Validate each octet against 0–255 and anchor on word boundaries that
reject adjacent dots and word characters. See the `RE_IPV4` pattern in
`scripts/leak_check.py`.

The inverse mistake is worth noting too: a keyword regex anchored with `\b`
will never match inside `snmp_community`, because `_` is a word character and
supplies no boundary. Both directions of this failure are silent.

---

## 8. An empty play is not a passing play

**Symptom:** A run completes with no failures and an empty report.

**Cause:** A typo in a group name, or a `--limit` that matches nothing. Ansible
does not consider this an error.

**Fix:** Assert that the play matched a non-zero number of hosts before doing
anything else.

---

## 9. Hardcoded `no_log: true` makes credential failures undebuggable

`no_log` is correct for tasks handling secrets and wrong as a permanent
fixture. When such a task fails, the output that would explain why is
suppressed along with the secret.

Make it a variable (`mask_sensitive_output`), pair it with `ignore_errors:
true`, and follow with an `assert` that names the failure. The assertion
message surfaces *what* failed without printing the value.

---

## 10. Verify `$HOME` before writing to `~/`

**Symptom:** A file written to `~/.config/something` appears in the git working
tree.

**Cause:** Service accounts frequently have a home directory set to somewhere
unexpected — including a repository root. Anything written to `~/` then lands
under version control, which for a credentials file is a serious problem.

**Fix:** Write to an explicit absolute path outside the repository, and set any
tool's config path explicitly rather than relying on `$HOME` resolution. Under
cron, `$HOME` may differ again from an interactive shell.

---

## 11. Scheduler re-runs may pin to the original commit

**Symptom:** A fix is committed and pushed, the job is re-run, and the old
behaviour persists.

**Cause:** Some CI and scheduling front-ends re-run a historical job at the
commit that job originally used. Re-running from history replays the bug.

**Fix:** Launch a fresh run from the template or pipeline definition, not from
the run history.

---

## 12. Unpinned collections re-resolve on every run

**Symptom:** Identical playbook, identical inventory, different behaviour
between two runs with no commit in between.

**Cause:** A scheduler that installs collections from Galaxy at task time will
pick up new releases silently. A major version bump changes module behaviour
with nothing in git to point at.

**Fix:** Pin every collection in `requirements.yml` with an explicit `version:`.

---

## 13. `git-receive-pack` does not inherit command-scope `-c` config

**Symptom:** `git -c safe.directory=... push` still fails with an ownership
error on a hook-driven push.

**Cause:** `git-receive-pack` is spawned as a child process and does not
inherit command-scope configuration passed with `-c`.

**Fix:** Set the configuration at system scope on the receiving host.

---

## 14. Plaintext vars can silently shadow a vaulted variable

**Symptom:** Credentials are rotated in the vault and nothing changes.

**Cause:** A leftover definition of the same variable name in a plaintext vars
file takes precedence, and there is no warning about the shadowing.

**Fix:** Audit both files whenever a credential variable misbehaves. Confirm
the effective value:

```bash
ansible -m debug -a 'var=some_credential_var' <group>
```

---

## 15. `delegate_to` and `run_once` at play level parse but do not work

**Symptom:** A play that looks correct fails at execution with
`'delegate_to' is not a valid attribute for a Play`.

**Cause:** Both are *task* keywords. Placed on a play they are structurally
valid YAML, so linting and review pass them. The failure only appears when the
play runs.

This bites hardest in exactly the situation that motivates using them: a
reporting play against network devices, where `connection: local` does not work
(gotcha 4) and `delegate_to: localhost` is the correct substitute. Putting it
where `connection:` would have gone is the natural mistake.

**Fix:** Apply per task.

```yaml
# Wrong -- parses, then fails at run time
- name: Render the report
  hosts: ios_devices
  run_once: true
  delegate_to: localhost
  tasks:
    - ansible.builtin.template: ...

# Right
- name: Render the report
  hosts: ios_devices
  tasks:
    - ansible.builtin.template: ...
      run_once: true
      delegate_to: localhost
```

`ansible-playbook --syntax-check` catches this. Run it in CI.

---

## 16. `SKIP` rolled up into `PASS`

**Symptom:** A compliance report shows every device compliant. Several were
never actually evaluated.

**Cause:** Treating "could not evaluate" as "no problem found". A check that
was unable to run has not passed, but if the summary only counts FAILs, an
unevaluated device is indistinguishable from a clean one.

**Fix:** Make SKIP a first-class status, count it separately, and have the
device-level verdict degrade to SKIP if any individual check skipped. Fail the
run on SKIP by default — unknown is not acceptable.

This is the same error as gotcha 6 one level up the stack: there, a blind
comparison reported PASS; here, a blind *device* is rolled into the compliant
count.

---

## 17. `ansible-galaxy` reads `collections_path`, but only if `ansible.cfg` exists yet

**Symptom:**

```
ERROR! couldn't resolve module/action 'cisco.ios.ios_facts'.
This often indicates a misspelling, missing collection, or incorrect
module path.
```

The collection is installed. `ansible-galaxy collection list` shows it.

**Cause:** An ordering dependency between two setup steps. `ansible.cfg` sets
`collections_path = ./collections`, and `ansible-galaxy` honours that setting --
but only if `ansible.cfg` is already on disk when the install runs. In a repo
that ships `ansible.cfg.example` and expects you to copy it, installing before
copying puts the collections in `~/.ansible/collections` while the playbooks
look in `./collections`.

What makes this expensive is the error text. It names three plausible causes --
misspelling, missing collection, incorrect module path -- and the real one is
none of them. The collection is present, spelled correctly, at a valid path;
just not the path this project is configured to search.

**Fix:** Stage the configuration first, then install.

```bash
cp ansible.cfg.example ansible.cfg
ansible-galaxy collection install -r requirements.yml
```

Confirm where they actually landed rather than trusting the success message:

```bash
ansible-galaxy collection list | head -3   # prints the search path in use
```

The same ordering applies in CI. A workflow that installs collections in one
step and materialises config in a later step will fail the syntax check while
every individual step reports success.
