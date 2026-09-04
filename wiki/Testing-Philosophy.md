# Testing philosophy

## Make it fail first

**A check observed only in its passing state has not been observed.**

Every test here asserts, in order:

1. The check **fails** under wrong conditions — wrong value, missing variable,
   unreachable host, broken credential.
2. The check **passes** under right conditions.
3. The failure message **names the cause**.

Step 1 is the one that gets skipped, and skipping it is how a check that stopped
working keeps reporting green. This is the same structural error as
[Gotcha 16](Gotcha-16-skip-rolled-up-into-pass), applied to the test suite
itself: a check that cannot fail has not passed, it has merely not run.

---

## What runs where

| Script | In `run_tests.sh` | Needs Ansible | Purpose |
|---|:---:|:---:|---|
| `test_mask.py` | ✅ | no | Masking filter functions |
| `test_leak_check.sh` | ✅ | no | The leak scanner, and the tree |
| `test_filter_path.sh` | ✅ | yes | Filters reachable from a playbook |
| `test_baseline_logic.yml` | ✅ | yes | Baseline evaluation, fixture-driven |
| `test_masking.sh` | ✅ | yes | Dual-render masking, fixture-driven |
| `simulate_ci.sh` | ❌ | yes | Reproduces the CI jobs |
| `test_bare_lint.sh` | ❌ | yes | Reproduces CI's lint job |

The last two are excluded from the default invocation because `simulate_ci.sh`
wipes `collections/` and all generated config — too destructive to run by
accident. Run both before pushing.

```bash
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/run_tests.sh
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/simulate_ci.sh
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_bare_lint.sh
```

`ANSIBLE_VENV` is required rather than discovered. Guessing which of several
installed ansible-core versions you meant is precisely what makes "it passed
locally" untrustworthy. Every run prints the interpreter and version it used.

---

## `test_mask.py` — 34 tests, most of them about failure

Runs under plain `python3 -m unittest`, with no Ansible present. The filter
module degrades `AnsibleFilterError` to a plain `Exception` subclass when
`ansible.errors` is unavailable, on the principle that **the highest-risk logic
in the repository should be testable on any machine with python3 and nothing
else**.

Most of the assertions are about the filters *raising*, not returning. A
masking filter must reject input it cannot parse, never pass it through
unchanged — because a value that survives a masking filter unparsed ends up
unmasked in a report labelled *masked*, while the render succeeds and every
test still passes.

This is the highest-consequence silent failure in the repository, which is why
it carries the most tests.

---

## `test_leak_check.sh` — verify the scanner, then trust it

Asserts category by category — IPv4, IPv6, MAC, domain, email, literal secret —
that each planted leak in `tests/negative/` is detected. Category-by-category
matters: a single pattern that stops matching fails *that specific category*
rather than the suite going quietly green on the strength of the others.

Then asserts no false positives against `tests/fixtures/`, which deliberately
includes the cases a naive implementation gets wrong:

- IOS image filenames — `cat9k_iosxe.17.06.06.SPA.bin`
  → [Gotcha 07](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames)
- Bare version strings
- `bypass:` keys, which trip a greedy credential pattern
- Prose containing `pass-through`
- Dotted names whose interior label looks like a TLD
- RFC 7042 documentation MACs

**Every allowlist entry is paired with a negative fixture proving the original
detection survives.** `negative/` contains a MAC one octet outside the
documentation range, which must still be caught. Without that pairing, an
allowlist is indistinguishable from a hole.

Fixtures carry a `.txt` suffix and their directories are excluded from the
repository scan, so the deliberately poisoned file is not itself a finding.

---

## `test_baseline_logic.yml` — logic without hardware

Ten fixture cases, fifty assertions, no devices required:

```bash
ansible-playbook -i localhost, tests/test_baseline_logic.yml
```

This is why collection and evaluation are separate task files in
`playbooks/network/tasks/`. Evaluation that is entangled with device I/O can
only be tested against devices, which in practice means it is tested against
whichever devices happen to be up.

---

## CI

Four jobs, on every push to every branch, on pull requests, and weekly:

| Job | What it does |
|---|---|
| **leak check** | Verifies the checker against planted leaks, *then* scans the tree |
| **unit tests** | Filter plugin tests under bare python3 |
| **lint** | `yamllint` and `ansible-lint` |
| **syntax check** | Stages config, runs fixture-driven logic and masking tests, installs pinned collections, syntax-checks every playbook |

The ordering inside the syntax job is not cosmetic. Staging configuration
before installing collections is required, and a workflow that reverses the two
fails the syntax check while every individual step reports success.
→ [Gotcha 17](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet)

`ansible-playbook --syntax-check` also catches play-level `delegate_to` and
`run_once`, which are structurally valid YAML and pass review.
→ [Gotcha 15](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work)

CI tests ansible-core **2.16 and 2.17**. Running against a much newer core can
pass locally and fail there.
