# Conventions

House style. Read this before contributing.

Canonical source: [`docs/conventions.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/conventions.md)

---

## The playbook header block

Every playbook opens with a comment block covering, in order:

1. **What it does** — one line.
2. **Why it exists** — especially if the obvious implementation is wrong.
3. **Required configuration** — inventory groups and variables, by name.
4. **Optional variables** — with defaults stated.
5. **Assumptions** — what must already be true.
6. **What fails if misconfigured** — each likely mistake and its symptom.
7. **Usage** — copy-pasteable invocations.

**Section 6 is the one that earns its keep.** State the *symptom*, not just the
cause, because the symptom is what the reader will actually be holding when
they come looking. Nobody searches for "connection plugin precedence"; they
search for "playbook says every device is up".

---

## Comment style

Comment the non-obvious and skip the rest. `# set the hostname` above a task
named "Set the hostname" is noise that trains readers to skip comments.

Worth a comment:

- Anything that looks like it could be simplified but cannot.
- Anywhere the obvious approach fails silently.
- Any ordering that matters.
- Any precedence interaction.

Where a gotcha applies, **restate it briefly at the point of use** and link to
`docs/gotchas.md`. Readers arrive at a playbook directly, not via the docs.
A cross-reference that requires leaving the file will not be followed.

---

## Structural patterns

| Pattern | Why |
|---|---|
| `delegate_to: localhost`, not `connection: local` | Play-level `connection:` is outranked by `ansible_connection` in group_vars — [Gotcha 04](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection) |
| `delegate_to` / `run_once` on **tasks**, never plays | Play-level parses and then fails at run time — [Gotcha 15](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work) |
| `ignore_errors` / `ignore_unreachable` in reporting playbooks | A failed host must stay visible. Aborting turns a partial outage into no report at all |
| `run_once: true` for render and send tasks | Otherwise one report per host |
| Dual-render for reports containing addresses | Masked copy for distribution, full copy archived at `0600` |
| Assert on emptiness | A play matching zero hosts is not a pass — [Gotcha 08](Gotcha-08-an-empty-play-is-not-a-passing-play) |
| `no_log` as a toggle, never hardcoded | Pair with `ignore_errors: true` and a following `assert` — [Gotcha 09](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable) |
| SKIP as a first-class status | Never rolled into PASS — [Gotcha 16](Gotcha-16-skip-rolled-up-into-pass) |
| Templates in `templates/` beside the playbook | Ansible searches there automatically; a root-level one forces `../../` paths that break on relocation |
| `filter_plugins` declared in `ansible.cfg` | Auto-discovery is relative to the playbook, not the project root — [Gotcha 18](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root) |
| Every collection pinned in `requirements.yml` | Unpinned collections re-resolve silently — [Gotcha 12](Gotcha-12-unpinned-collections-re-resolve-on-every-run) |

---

## Testing

**Make it fail first.** A check that has only ever been observed passing has
not been observed at all.

For each check, verify in this order:

1. It **fails** under the wrong conditions.
2. It **passes** under the right conditions.
3. It reports the failure in a way that **names the cause**.

`tests/test_leak_check.sh` follows this shape and is the reference example.
Full detail: [Testing philosophy](Testing-Philosophy).

---

## Commit messages

Explain **why**, not what — the diff already shows what. A commit that changes
a timeout should say what timed out and how the new value was arrived at.

Security-relevant changes state what was verified and how. Git is the
authoritative anchor for these values, so the reasoning has to live where the
change does.

And: no real environment data in commit messages either. The rule covers
history, not just the working tree.

---

## Adding a gotcha

Anything learned the hard way gets written down rather than left for the next
person to rediscover.

1. Append a `## N. Title` section to `docs/gotchas.md`, following the existing
   shape: **Symptom → Cause → Fix**, with the symptom first.
2. Assign the number to a category in the `GROUPS` list in
   `scripts/build_wiki.py`.
3. Rebuild the wiki: `python3 scripts/build_wiki.py`

The build **refuses to complete** if a gotcha is ungrouped, so a new entry
cannot quietly fail to appear in the index. CI runs
`python3 scripts/build_wiki.py --check` and fails on a stale build.

The bar for inclusion is not "this was annoying". It is **the code ran, exited
zero, and reported success while being wrong.** Ordinary errors announce
themselves and do not belong in the catalogue.
