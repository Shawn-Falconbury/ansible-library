# tests

## Principle

Make it fail first. A check observed only in its passing state has not been
observed.

Each test asserts, in order:

1. The check **fails** under wrong conditions.
2. The check **passes** under right conditions.
3. The failure message names the cause.

## Running them

```bash
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/run_tests.sh
```

Or activate a virtualenv first and drop the variable. There is deliberately no
search of likely venv locations: guessing which of several installed
ansible-core versions you meant is what makes "it passed locally" untrustworthy.
Every run prints the interpreter and version it used.

CI tests ansible-core 2.16 and 2.17. Running against a much newer core can pass
here and fail there.

## What runs where

| Script | In `run_tests.sh` | Needs Ansible | Purpose |
|---|---|---|---|
| `test_mask.py` | yes | no | Masking filter functions |
| `test_leak_check.sh` | yes | no | The leak scanner, and the tree |
| `test_filter_path.sh` | yes | yes | Filters reachable from a playbook |
| `test_baseline_logic.yml` | yes | yes | Baseline evaluation, fixture-driven |
| `test_masking.sh` | yes | yes | Dual-render masking, fixture-driven |
| `simulate_ci.sh` | **no** | yes | Reproduces the CI jobs |
| `test_bare_lint.sh` | **no** | yes | Reproduces CI's lint job |

The last two are excluded from `run_tests.sh` because `simulate_ci.sh` wipes
`collections/` and all generated config — too destructive for the default
invocation. Run both before pushing:

```bash
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/simulate_ci.sh
ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_bare_lint.sh
```

## `test_mask.py`

Runs under plain `python3 -m unittest`, with no Ansible present — the filter
module degrades `AnsibleFilterError` to a plain `Exception` subclass when
`ansible.errors` is unavailable. The highest-risk logic in the repository should
be testable on any machine with python3 and nothing else.

Most of the 34 tests assert on **failure**. The filters must raise on input
they cannot parse, never return it unchanged: a value that passes through a
masking filter unparsed ends up unmasked in a report labelled masked, while the
render succeeds and every test still passes.

## `test_leak_check.sh`

Verifies `scripts/leak_check.py` before trusting its verdict on the repository.
Asserts category by category — IPv4, IPv6, MAC, domain, email, literal secret —
that each planted leak in `negative/` is detected, so a single pattern that
stops matching fails that specific category rather than going quietly green.

Then asserts no false positives against `fixtures/`, which includes the cases a
naive implementation gets wrong: IOS image filenames (`cat9k_iosxe.17.06.06.SPA.bin`),
bare version strings, `bypass:` keys that trip a greedy credential pattern,
prose containing `pass-through`, dotted names whose interior label looks like a
TLD, and RFC 7042 documentation MACs.

Every allowlist entry is paired with a negative fixture proving the original
detection survives. `negative/` contains `00:00:5e:00:54:af` — one octet outside <!-- leak-check: allow -->
the documentation range — which must still be caught.

Fixtures carry a `.txt` suffix and their directories are excluded from the
repository scan, so the deliberately poisoned file is not itself a finding.

## `test_filter_path.sh`

`test_mask.py` proves the functions work. This proves a playbook can reach
them — a different question, because Ansible autodiscovers `filter_plugins/`
next to the *playbook*, and every playbook here lives in a subdirectory. It
works only because `ansible.cfg` declares the path.

Asserts both directions. The negative half matters most: a configuration line
that turns out to be unnecessary is a line nobody dares delete, and a suite that
would stay green after deleting it teaches nothing.

## `test_baseline_logic.yml`

Drives `playbooks/network/tasks/evaluate_baseline.yml` against recorded fixtures
on localhost — no device, no credentials. Ten cases, fifty assertions.

This is what catches gotcha 6: a fixture containing formatted TimeTicks
(`9:0:07:42.73`) proves `| int` yields `0` and that the guard forces SKIP rather
than PASS.

## `test_masking.sh`

Renders `playbooks/network/templates/device_inventory.html.j2` both ways
from `fixtures/inventory_rows.yml` and asserts that no value the fixture
supplied appears in the masked copy.

This covers a gap `test_mask.py` cannot. Those tests prove the masking
*functions* work; they say nothing about whether the template calls them. A
field that prints `row.mgmt_ip` directly instead of going through the
`addr()` macro leaves all 34 unit tests green while leaking every
management address into the distributed report. Verified by mutation: that
exact change makes this test fail and the unit tests pass.

It asserts the *full* render contains every fixture value first. Without
that control, an empty or broken render would satisfy the masking
assertion trivially -- a file containing nothing leaks nothing.

`scripts/leak_check.py` is deliberately **not** used as the assertion here.
The fixture must use publishable values (RFC 5737, RFC 7042) because it is
committed to a public repository, and those are precisely the values the
checker allowlists -- so it returns clean on the unmasked render. The two
answer different questions: the checker asks whether anything unsafe to
publish is in the repository, this asks whether the template routes every
field through a masking macro.

The wrapper exists because the test needs `ansible.cfg` staged to resolve
the masking filters, and `ansible.cfg` is gitignored. It stages one, runs
the playbook, and restores whatever was there before.

## `simulate_ci.sh`

**Every command in this file must be copied verbatim from `.github/workflows/ci.yml`.**

This has been violated twice. The first version added `-not -path '*/tasks/*'`
to the syntax-check `find`, because feeding task files to `--syntax-check` is
obviously wrong — the simulation passed, CI failed, and the exclusion that made
it pass was the bug it existed to catch. The second time, a `unit` job was added
to `ci.yml` and not here, one commit after that warning was written.

A simulation that diverges from what it simulates is worse than none: it turns
an unknown into a false assurance. **When `ci.yml` changes, change this file in
the same commit.**

One known divergence, documented in the script: CI's `unit` job runs with no
Ansible installed, which cannot be reproduced on a development box that has it.
A pass here is necessary but not sufficient for that property.

## `test_bare_lint.sh`

CI runs lint and syntax as separate jobs on separate runners. The lint job gets
a fresh checkout with no `ansible.cfg`, no staged inventory, and no collections;
`simulate_ci.sh` runs `ansible-lint` after staging all three. Those are
different tests, and a repo can pass one and fail the other.

This reconstructs what `actions/checkout` would receive — committed content plus
uncommitted changes plus untracked files, honouring `.gitignore` — so build
artefacts cannot mask a problem the runner would hit.

## Verifying a push

`scripts/verify_published.py` asks GitHub what it actually received, rather than
asking your clone what it believes it sent. Checks visibility, the head commit's
author identity and account linkage, that no generated config or collections
were published, that scripts carry the executable bit, and the latest CI
conclusion per job.

```bash
python3 scripts/verify_published.py
```

The repository slug comes from the `origin` remote, so it works in a fork.
