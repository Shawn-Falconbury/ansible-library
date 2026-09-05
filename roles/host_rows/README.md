# roles/host_rows

Builds the row list every report in this repository renders from.

## Contract

Set `host_rows_targeted` to `ansible_play_hosts_all` and call the role. It
reads `check_results`, `check_verdict`, `collection_failed` and
`collection_error` from each host's vars.

```yaml
- name: Build the report rows
  # apply:, not bare run_once/delegate_to -- those are not valid attributes
  # of an include and are rejected at syntax-check.
  ansible.builtin.include_role:
    name: host_rows
    apply:
      run_once: true
      delegate_to: localhost
  vars:
    host_rows_targeted: "{{ ansible_play_hosts_all }}"
  run_once: true
```

Produces:

| Variable | Contents |
|---|---|
| `host_rows_list` | one dict per targeted host: `name`, `reachable`, `verdict`, `checks`, and `reason` when unreachable |
| `host_rows_counts` | `{PASS, FAIL, SKIP}` across every check in the fleet |
| `host_rows_skipped` | `"host :: check"` per SKIP, for assert messages |
| `host_rows_failed` | `"host :: check"` per FAIL, for assert messages |

## The two things it exists to prevent

**A host that vanished must still appear.** Unreachable hosts are removed from
`ansible_play_hosts` before the reporting tasks run. A row list built from the
survivors is internally consistent, correctly formatted, and missing exactly
the hosts somebody needed to know about — and their absence reads as a smaller
fleet rather than an outage. This role iterates `host_rows_targeted` and
asserts it produced one row per entry.

**An uncollected host must not be given zeros.** `0 failed` for a machine
nobody reached renders as a measurement and reads as the healthiest thing in
the fleet. Uncollected rows carry an empty check list and contribute a SKIP to
the totals.

## Do not render the summary lists

`host_rows_skipped` and `host_rows_failed` are flat strings with the host name
already baked in. They are for `assert` messages on the operator's own
terminal.

Rendering them in a template bypasses the masking macros entirely, because
there is no field left to mask — the name is already inside the string. That
leak happened once here, in `service_health.txt.j2`, and it looked correct
because the per-host rows above it masked properly. Templates derive their
summary sections from `host_rows_list`.

## Requires a staged ansible.cfg

`include_role` resolves by name through `roles_path`, which
`ansible.cfg.example` declares as `./roles`. On a bare checkout with no staged
config the role does not resolve, and the error names the role rather than the
search path — the same shape as `docs/gotchas.md` entry 18.
