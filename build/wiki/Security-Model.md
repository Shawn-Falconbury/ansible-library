# Security model

## The rule

**No real environment data, ever — not in a file, not in a commit message, not
in an issue.**

This is enforced, not merely requested.

---

## Why "sanitise it later" does not work

Scrubbing a working tree does nothing about what earlier commits contain. Every
prior commit in a public repository is fetchable by anyone who clones it, and a
force-push does not remove an object that someone has already forked, mirrored,
or that a crawler has already read.

The only reliable version of this rule is one that is true from the first
commit, which is why `scripts/bootstrap_repo.sh` **refuses to run on top of an
existing history** and creates a fresh one instead.

---

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
| RFC 7042 MAC range | A MAC you must replace | `00:00:5e:00:53:af` |

### Never use a plausible-looking placeholder

A private address reads as real, survives review, and teaches readers that
private ranges are acceptable here. They are not — **a private address is still
someone's real network**. An RFC 1918 address in a public repository tells a
reader something true about an environment they should know nothing about, and
that remains true whether or not it was the address you meant to use.

(This page does not name one as an example, deliberately. `scripts/leak_check.py`
flags RFC 1918 literals, and earning a waiver to illustrate a rule about not
needing waivers would be the wrong lesson.)

### MACs are easier to get wrong

There is no familiar "private MAC" intuition to fall back on. RFC 7042 §2.1.2
reserves `00-00-5E-00-53-00` through `00-00-5E-00-53-FF` for documentation.
Anything else is a real IEEE-assigned OUI: `00:1a:2b` *looks* like a
placeholder and identifies an actual vendor. The leak checker allowlists the
documentation range and flags everything else.

---

## Tracked vs. gitignored

Only `.example` files are tracked. Their filled-in counterparts are gitignored.

The point is the direction of the failure: forgetting to copy a file produces a
**missing file**, which is loud. The alternative arrangement — tracking real
files and relying on `.gitignore` to catch them — produces a **committed
credential**, which is silent.

---

## `scripts/leak_check.py`

Scans the whole tree for:

- IPv4 and IPv6 addresses outside the RFC 5737 / RFC 3849 documentation ranges
- MAC addresses outside the RFC 7042 documentation range
- Non-`.example` domains
- Email addresses
- Credential-shaped assignments

Runs in CI on every push and on a weekly schedule, and can be wired into
`pre-commit`:

```bash
pip install pre-commit && pre-commit install
```

### The scanner is tested before it is trusted

```bash
bash tests/test_leak_check.sh      # this, not leak_check.py alone
```

`tests/test_leak_check.sh` asserts the **negative path first** — the scanner
must reject a file of deliberately planted leaks, category by category — and
only then accepts its clean verdict on the working tree.

A scanner that has silently stopped matching is worse than no scanner, because
it converts an active check into a false assurance. This is the same failure
shape as everything in the [gotchas catalogue](Gotchas): the run exits zero and
reports success while being wrong.

### Regex hazards, both directions

Getting these patterns right is harder than it looks, and it fails silently in
both directions:

- **Over-matching:** `\d+\.\d+\.\d+\.\d+` fires on `cat9k_iosxe.17.06.06.SPA.bin`
  and on version strings generally. Each octet has to be validated against
  0–255 and anchored on word boundaries that reject adjacent dots.
- **Under-matching:** a keyword regex anchored with `\b` will never match
  inside `snmp_community`, because `_` is a word character and supplies no
  boundary.

→ [Gotcha 07](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames)

Every allowlist entry is paired with a negative fixture proving the original
detection still fires. An allowlist without that pairing is a hole with
documentation attached.

---

## Secrets in playbook output

`no_log: true` is correct for tasks handling secrets and **wrong as a permanent
fixture**. When such a task fails, the output that would explain why is
suppressed along with the secret, and you are left debugging a credential
failure with no information.

The pattern used here:

```yaml
no_log: "{{ mask_sensitive_output }}"
ignore_errors: true
```

followed by an `assert` that names the failure. The assertion message surfaces
*what* failed without printing the value.

→ [Gotcha 09](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable)

### Vault shadowing

A leftover plaintext definition of a variable name takes precedence over the
vaulted one, with no warning about the shadowing. Credentials get rotated in
the vault and nothing changes.

```bash
ansible -m debug -a 'var=some_credential_var' <group>
```

→ [Gotcha 14](Gotcha-14-plaintext-vars-can-silently-shadow-a-vaulted-variable)

---

## Reports that contain addresses

**Dual-render.** A masked copy for distribution, and a full copy archived at
mode `0600`.

The masking filters must raise on input they cannot parse rather than passing
it through — a value that survives a masking filter unparsed ends up unmasked
in a report labelled *masked*, while the render succeeds. Most of
`tests/test_mask.py` exists to assert that failure path.

Note which way [Gotcha 18](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root)
fails: a missing masking filter raises and the render stops, so the report is
never built. That is the safe direction. If you are going to have a bug in a
masking pipeline, that is the one to have.

---

## Writing files

Verify `$HOME` before writing to `~/`. Service accounts frequently have a home
directory set somewhere unexpected — including a repository root — and anything
written to `~/` then lands under version control. For a credentials file that
is a serious problem. Under cron, `$HOME` may differ again from an interactive
shell.

→ [Gotcha 10](Gotcha-10-verify-home-before-writing-to)
