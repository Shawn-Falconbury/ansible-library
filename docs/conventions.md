# Conventions

## The placeholder vocabulary

Placeholders are deliberately distinguishable so that "not yet configured" can
never be mistaken for a working value.

| Form | Means | Example |
|---|---|---|
| RFC 5737 range | An address you must replace | `192.0.2.10`, `198.51.100.25`, `203.0.113.7` |
| `.example` domain | A name you must replace | `sw-a-access-01.lab.example` |
| `CHANGEME_` prefix | Must be set before first run; no safe default exists | `CHANGEME_set_in_vault` |
| `{{ vault_* }}` | A secret, referenced never inlined | `{{ vault_ios_password }}` |
| `.example` suffix | Copy the file and fill it in | `vars/mail.yml.example` |

Never use a plausible-looking address as a placeholder. `10.0.0.1` reads as <!-- leak-check: allow -->
real, survives review, and teaches readers that private ranges are acceptable
in this repo. They are not — a private address is still someone's real network.

Only `.example` files are tracked. Their filled-in counterparts are gitignored,
so the failure mode is a missing file (loud) rather than a committed
credential (silent).

## Playbook header block

Every playbook opens with a comment block covering, in order:

1. **What it does** — one line.
2. **Why it exists** — especially if the obvious implementation is wrong.
3. **Required configuration** — inventory groups and variables, by name.
4. **Optional variables** — with defaults stated.
5. **Assumptions** — what must already be true.
6. **What fails if misconfigured** — each likely mistake and its symptom.
7. **Usage** — copy-pasteable invocations.

Section 6 is the one that earns its keep. State the *symptom*, not just the
cause, because the symptom is what the reader will actually be holding.

## Comment style

Comment the non-obvious and skip the rest. `# set the hostname` above a task
named "Set the hostname" is noise.

Worth a comment:

- Anything that looks like it could be simplified but cannot.
- Anywhere the obvious approach fails silently.
- Any ordering that matters.
- Any precedence interaction.

Where a gotcha applies, restate it briefly at the point of use and link to
`docs/gotchas.md`. Readers arrive at a playbook directly, not via the docs.

## Structural patterns

**`delegate_to: localhost`, not `connection: local`.** Play-level `connection:`
is outranked by `ansible_connection` in group_vars. See gotcha 4.

**`ignore_errors` / `ignore_unreachable` in reporting playbooks.** A failed
host must stay visible in the report. Letting the play abort turns a partial
outage into no report at all.

**`run_once: true` for render and send tasks.** Otherwise one report per host.

**Dual-render.** Where a report contains addresses: a masked copy for
distribution, and a full copy archived at mode `0600`.

**Assert on emptiness.** A play matching zero hosts is not a pass.

**`no_log` as a toggle, never hardcoded.** Pair with `ignore_errors: true` and
a following `assert` so failures surface without printing values.

## Testing

The rule is: **make it fail first.** A check that has only ever been observed
passing has not been observed at all.

For each check, verify in this order:

1. It **fails** under the wrong conditions — wrong value, missing variable,
   unreachable host, broken credential.
2. It **passes** under the right conditions.
3. It reports the failure in a way that names the cause.

`tests/test_leak_check.sh` follows this shape and is the reference example:
the scanner must reject a file of planted leaks, category by category, before
its clean verdict on the repository is accepted as meaningful.

## Pre-commit

```bash
pip install pre-commit && pre-commit install
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: leak-check
        name: leak check
        entry: python3 scripts/leak_check.py
        language: system
        pass_filenames: false
        always_run: true
```

## Commit messages

Explain **why**, not what — the diff already shows what. A commit that changes
a timeout should say what timed out and how the new value was arrived at.

Security-relevant changes state what was verified and how. Git is the
authoritative anchor for these values, so the reasoning has to live where the
change does.
